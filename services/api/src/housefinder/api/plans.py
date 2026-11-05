"""Plan completo de una oferta (F6.7, ADR-0025): sus secciones y la explicación del asesor."""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Iterator, Mapping
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from housefinder.advisor.tools import ExplainedPlan, PlanExplanation, explain_plan
from housefinder.agent.loop import Progress
from housefinder.agent.references import FigureSegment, OfferSegment, Segment, segments
from housefinder.api.deps import (
    ClientDep,
    DbDep,
    KeysDep,
    LLMDep,
    OrgDep,
    ParamBookDep,
    RuleBookDep,
    SessionDep,
    check_full_plan,
    is_particular,
)
from housefinder.api.figures import FigureOut, SeriesOut, figure_out, series_out
from housefinder.api.search import RentalAdviceOut, advice_out
from housefinder.branding import service as branding
from housefinder.core.figures import Figure
from housefinder.crypto.envelope import KeyProvider
from housefinder.db.connection import Connection
from housefinder.db.profiles import latest_profile_id
from housefinder.db.tiers import record_plan_use
from housefinder.params.book import ParamBook
from housefinder.plans.bids import Charge, bid_simulation
from housefinder.plans.service import FullPlan, PlanUnavailable, full_plan
from housefinder.profiles import store
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook
from housefinder.reports.pdf import plan_html, plan_pdf, plan_sources
from housefinder.search.service import ContentCache, SearchUnavailable

router = APIRouter(prefix="/plans", tags=["plan"])
log = logging.getLogger(__name__)
# Para que ni Caddy ni el proxy de Next acumulen ni compriman las etapas (ADR-0052)
STREAM_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


class SectionOut(BaseModel):
    id: str
    title: str
    figures: list[FigureOut]


class ArgumentOut(BaseModel):
    code: str
    text: str
    figure_keys: list[str]


class StepOut(BaseModel):
    id: str
    stage: str
    title: str
    detail: str
    source_url: str
    verified: bool


class ChangeOut(BaseModel):
    key: str
    base: FigureOut
    scenario: FigureOut
    delta: FigureOut


class PlanOut(BaseModel):
    offer_id: UUID
    kind: str
    title: str | None
    url: str | None
    auction: bool
    passes: bool
    reasons: list[str]
    sections: list[SectionOut]
    advice: RentalAdviceOut | None
    arguments: list[ArgumentOut]
    roadmap: list[StepOut]
    pending_changes: list[ChangeOut]  # cifras que cambian con las reglas pendientes
    cheapest_mortgage: str | None
    safest_mortgage: str | None
    notes: list[str]
    # Para las gráficas (ADR-0050): año a año y el primer año por partes, en €/año
    series: list[SeriesOut] = []
    breakdown: list[FigureOut] = []


class SegmentOut(BaseModel):
    kind: Literal["text", "figure", "offer"]
    text: str | None = None
    figure: FigureOut | None = None
    part: str | None = None  # value, low, high o range
    offer: str | None = None
    label: str | None = None


class CardOut(BaseModel):
    title: str
    text: list[SegmentOut]
    figure: FigureOut | None  # la cifra que resume la ficha


class ExplanationOut(BaseModel):
    """Las fichas del asesor (ADR-0052). `summary` None: el texto no pasó la comprobación."""

    summary: list[SegmentOut] | None
    cards: list[CardOut]
    risks: list[list[SegmentOut]]
    next_step: list[SegmentOut] | None
    failure: str | None
    notes: list[str]
    extra_arguments: list[str]  # del asesor: no salen de las cifras


@router.get("/offers/{offer_id}", response_model=PlanOut)
def offer_plan(offer_id: UUID, db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
               book: ParamBookDep, rules: RuleBookDep, current: SessionDep) -> PlanOut:
    plan = _plan(db, keys, org, client, book, rules, offer_id, is_particular(current))[1]
    return PlanOut(
        offer_id=plan.offer_id, kind=plan.kind, title=plan.title, url=plan.url,
        auction=plan.auction, passes=plan.verdict.passes, reasons=list(plan.verdict.reasons),
        sections=[SectionOut(id=s.id, title=s.title, figures=[figure_out(f) for f in s.figures])
                  for s in plan.sections],
        advice=advice_out(plan.advice) if plan.advice else None,
        arguments=[ArgumentOut(code=a.code, text=a.text, figure_keys=[f.key for f in a.figures])
                   for a in plan.arguments],
        roadmap=[StepOut(id=s.id, stage=s.stage, title=s.title, detail=s.detail,
                         source_url=s.source_url, verified=s.verified) for s in plan.roadmap],
        pending_changes=[ChangeOut(key=c.key, base=figure_out(c.base),
                                   scenario=figure_out(c.scenario), delta=figure_out(c.delta))
                         for c in (plan.pending.changed if plan.pending else ())],
        cheapest_mortgage=plan.cheapest_mortgage, safest_mortgage=plan.safest_mortgage,
        notes=list(plan.notes), series=[series_out(x) for x in plan.series],
        breakdown=[figure_out(f) for f in plan.breakdown])


class ChargeIn(BaseModel):
    concept: str = Field(default="", max_length=200)  # como aparece en la página
    amount: Decimal = Field(ge=0)


class BidsIn(BaseModel):
    """Simulador de puja (ADR-0047). Importes en euros."""

    auction_value: Decimal | None = Field(default=None, gt=0)  # si no lo trae la oferta
    charges: list[ChargeIn] = Field(default_factory=list, max_length=30)  # las que subsisten
    possession: Decimal = Field(default=Decimal(0), ge=0)  # coste de recuperar la posesión
    cash: bool = False  # al contado, sin hipoteca
    judicial: bool = False  # subasta judicial: depósito y fases de la LEC


class BidLevelOut(BaseModel):
    share: Decimal
    price: FigureOut
    cashflow: FigureOut
    stressed: FigureOut | None
    irr: FigureOut | None
    passes: bool
    reasons: list[str]
    stage: str | None


class BidsOut(BaseModel):
    offer_id: UUID
    title: str | None
    url: str | None
    auction_value: FigureOut
    deposit: FigureOut | None
    charges: FigureOut | None
    max_bid: FigureOut | None
    levels: list[BidLevelOut]
    notes: list[str]


@router.post("/offers/{offer_id}/bids", response_model=BidsOut)
def offer_bids(offer_id: UUID, body: BidsIn, db: DbDep, keys: KeysDep, org: OrgDep,
               client: ClientDep, book: ParamBookDep, rules: RuleBookDep,
               current: SessionDep) -> BidsOut:
    """La puja máxima y el plan a cada puja de una subasta. Cuenta como un plan completo."""
    profile_id = latest_profile_id(db, org, client)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Confirma primero tu perfil en /perfil")
    profile = store.load(db, keys, profile_id, org)
    record = check_full_plan(db, org, offer_id, is_particular(current))  # nivel gratuito
    try:
        sim = bid_simulation(db, book, rules, profile, org, offer_id, body.auction_value,
                             tuple(Charge(" ".join(c.concept.split()), c.amount)
                                   for c in body.charges if c.amount > 0),
                             body.possession, body.cash, body.judicial)
    except SearchUnavailable as exc:
        raise HTTPException(status_code=422, detail=exc.reasons) from exc
    except PlanUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if record:
        record_plan_use(db, org, offer_id)
        db.commit()
    return BidsOut(
        offer_id=sim.offer_id, title=sim.title, url=sim.url,
        auction_value=figure_out(sim.auction_value),
        deposit=figure_out(sim.deposit) if sim.deposit else None,
        charges=figure_out(sim.charges) if sim.charges else None,
        max_bid=figure_out(sim.max_bid) if sim.max_bid else None,
        levels=[BidLevelOut(
            share=lv.share, price=figure_out(lv.price), cashflow=figure_out(lv.cashflow),
            stressed=figure_out(lv.stressed) if lv.stressed else None,
            irr=figure_out(lv.irr) if lv.irr else None, passes=lv.verdict.passes,
            reasons=list(lv.verdict.reasons), stage=lv.stage) for lv in sim.levels],
        notes=list(sim.notes))


@router.get("/offers/{offer_id}/pdf", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def offer_plan_pdf(offer_id: UUID, db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
                   book: ParamBookDep, rules: RuleBookDep, current: SessionDep) -> Response:
    """El plan en PDF con su anexo de fuentes (ADR-0026). No se guarda: lleva datos personales."""
    plan = _plan(db, keys, org, client, book, rules, offer_id, is_particular(current))[1]
    html = plan_html(plan, plan_sources(db, plan, rules, book), date.today(),
                     branding.load(db, org))
    try:
        pdf = plan_pdf(html)
    except OSError as exc:  # faltan pango o cairo
        raise HTTPException(status_code=503, detail="No se puede generar el PDF: faltan las "
                            "bibliotecas de WeasyPrint (brew install pango; ver ADR-0026)"
                            ) from exc
    return Response(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="plan-{offer_id.hex[:8]}.pdf"',
        "Cache-Control": "no-store"})


@router.post("/offers/{offer_id}/explanation", response_class=StreamingResponse,
             responses={200: {"model": ExplanationOut, "description": (
                 "text/event-stream: eventos «etapa» ({etapa, herramienta}) mientras el asesor "
                 "trabaja y uno «resultado» con el ExplanationOut, o «error» (ADR-0052)")}})
def explanation(offer_id: UUID, db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
                book: ParamBookDep, rules: RuleBookDep, llm: LLMDep,
                current: SessionDep) -> StreamingResponse:
    # Lo que puede fallar con un código HTTP (sin perfil, nivel gratuito) va antes de empezar
    profile, plan = _plan(db, keys, org, client, book, rules, offer_id, is_particular(current))
    events: queue.Queue[str | None] = queue.Queue()

    def tell(step: Progress) -> None:
        events.put(_event("etapa", {"etapa": step.stage, "herramienta": step.tool}))

    def work() -> None:
        try:
            explained = explain_plan(db, book, llm, org, plan, profile, rules, progress=tell)
            events.put(_event("resultado", explanation_out(explained).model_dump(mode="json")))
        except Exception as exc:  # el usuario ve una línea; el registro, solo el tipo
            log.error("La explicación del plan falló: %s", type(exc).__name__)
            events.put(_event("error", {"detail": "El asesor no ha podido terminar"}))
        finally:
            events.put(None)

    def stream() -> Iterator[str]:
        threading.Thread(target=work, daemon=True).start()
        while (item := events.get()) is not None:
            yield item

    return StreamingResponse(stream(), media_type="text/event-stream", headers=STREAM_HEADERS)


def explanation_out(explained: ExplainedPlan) -> ExplanationOut:
    answer = explained.answer
    cards = answer.output if isinstance(answer.output, PlanExplanation) else None
    if cards is None:
        return ExplanationOut(summary=None, cards=[], risks=[], next_step=None,
                              failure=answer.failure, notes=answer.notes,
                              extra_arguments=explained.extra_arguments)

    def parts(text: str) -> list[SegmentOut]:  # ya comprobado en el bucle
        return [_segment(s) for s in segments(text, answer.figures, answer.offers)]

    return ExplanationOut(
        summary=parts(cards.resumen),
        cards=[CardOut(title=c.titulo, text=parts(c.texto),
                       figure=_card_figure(c.cifra, answer.figures)) for c in cards.claves],
        risks=[parts(r) for r in cards.riesgos], next_step=parts(cards.siguiente_paso),
        failure=None, notes=answer.notes, extra_arguments=explained.extra_arguments)


def _card_figure(marker: str | None, figures: Mapping[str, Figure]) -> FigureOut | None:
    found = segments(marker, figures) if marker else []
    return figure_out(found[0].figure) if found and isinstance(found[0], FigureSegment) else None


def _event(name: str, data: object) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# Los planes completos ya calculados (ver ContentCache): volver al plan de una oferta, su PDF y
# el asesor no lo calculan de nuevo mientras no cambie nada de lo que lo decide
PLANS: ContentCache[FullPlan] = ContentCache(size=500)


def _plan(db: Connection, keys: KeyProvider, org: UUID, client: UUID, book: ParamBook,
          rules: RuleBook, offer_id: UUID,
          particular: bool = False) -> tuple[UserProfile, FullPlan]:
    profile_id = latest_profile_id(db, org, client)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Confirma primero tu perfil en /perfil")
    profile = store.load(db, keys, profile_id, org)
    record = check_full_plan(db, org, offer_id, particular)  # nivel gratuito (ADR-0041)
    try:
        plan = full_plan(db, book, rules, profile, org, offer_id, cache=PLANS)
    except SearchUnavailable as exc:
        raise HTTPException(status_code=422, detail=exc.reasons) from exc
    except PlanUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if record:
        record_plan_use(db, org, offer_id)
        db.commit()
    return profile, plan


def _segment(segment: Segment) -> SegmentOut:
    if isinstance(segment, FigureSegment):
        return SegmentOut(kind="figure", figure=figure_out(segment.figure), part=segment.part)
    if isinstance(segment, OfferSegment):
        return SegmentOut(kind="offer", offer=segment.offer, label=segment.label)
    return SegmentOut(kind="text", text=segment.text)
