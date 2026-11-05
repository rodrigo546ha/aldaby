"""Plan completo de una oferta (F6.7, ADR-0025): sus secciones y la explicación del asesor."""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable, Iterator, Mapping
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from housefinder.advisor import conversations
from housefinder.advisor.tools import (
    ExplainedPlan,
    PlanExplanation,
    PlanGate,
    ask_about_offer,
    ask_in_plan,
    explain_plan,
)
from housefinder.agent.llm import Message
from housefinder.agent.loop import AgentAnswer, Progress
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
    advisor_left,
    check_full_plan,
    is_particular,
    plan_gate,
    take_advisor,
)
from housefinder.api.figures import FigureOut, SeriesOut, figure_out, series_out
from housefinder.api.search import RentalAdviceOut, advice_out
from housefinder.branding import service as branding
from housefinder.core.figures import Figure
from housefinder.core.retention import conversation_days
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
    take_advisor(db, org, is_particular(current))  # consultas al asesor de hoy (ADR-0065)
    gate = plan_gate(db, org, is_particular(current))  # el plan de otra oferta gasta cupo
    events: queue.Queue[str | None] = queue.Queue()

    def tell(step: Progress) -> None:
        events.put(_event("etapa", {"etapa": step.stage, "herramienta": step.tool}))

    def work() -> None:
        try:
            explained = explain_plan(db, book, llm, org, plan, profile, rules, progress=tell,
                                     plan_gate=gate)
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


class QuestionIn(BaseModel):
    """La pregunta sola: el historial sale de la conversación guardada (ADR-0064)."""

    question: str = Field(min_length=2, max_length=500)


class AdvisorAnswerOut(BaseModel):
    """La respuesta del asesor, ya comprobada. `answer` None: el texto no pasó la comprobación.
    `text` es el mismo texto con sus marcadores, el que ve el modelo en el historial."""

    answer: list[SegmentOut] | None
    text: str | None
    failure: str | None
    notes: list[str]


QUESTION_STREAM = {200: {"model": AdvisorAnswerOut, "description": (
    "text/event-stream: eventos «etapa» mientras el asesor trabaja y uno «resultado» con el "
    "AdvisorAnswerOut, o «error» (ADR-0063)")}}
Answer = Callable[[list[Message], Callable[[Progress], None], PlanGate | None], AgentAnswer]


@router.post("/offers/{offer_id}/questions", response_class=StreamingResponse,
             responses=QUESTION_STREAM)
def question(offer_id: UUID, body: QuestionIn, db: DbDep, keys: KeysDep, org: OrgDep,
             client: ClientDep, book: ParamBookDep, rules: RuleBookDep, llm: LLMDep,
             current: SessionDep) -> StreamingResponse:
    """Una pregunta sobre el plan de la oferta. Se guarda cifrada en su conversación (ADR-0064)."""
    profile, _ = _plan(db, keys, org, client, book, rules, offer_id, is_particular(current))
    return _answer(db, keys, org, client, offer_id, body.question, is_particular(current),
                   lambda history, tell, gate: ask_about_offer(
                       db, book, llm, org, offer_id, body.question, history, profile, rules,
                       progress=tell, plan_gate=gate))


@router.post("/questions", response_class=StreamingResponse, responses=QUESTION_STREAM)
def general_question(body: QuestionIn, db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
                     book: ParamBookDep, rules: RuleBookDep, llm: LLMDep,
                     current: SessionDep) -> StreamingResponse:
    """Una pregunta en «Mi plan», sin oferta fija (ADR-0066): las mismas herramientas que en la
    terminal, con su conversación cifrada."""
    profile = _profile(db, keys, org, client)
    return _answer(db, keys, org, client, None, body.question, is_particular(current),
                   lambda history, tell, gate: ask_in_plan(
                       db, book, llm, org, body.question, history, profile, rules,
                       progress=tell, plan_gate=gate))


def _answer(db: Connection, keys: KeyProvider, org: UUID, client: UUID, offer_id: UUID | None,
            question: str, particular: bool, answer: Answer) -> StreamingResponse:
    """Lo común de una pregunta al asesor: historial guardado, consulta del día, cupo de planes,
    etapas en `text/event-stream` y la vuelta guardada cifrada (ADR-0063, ADR-0064, ADR-0065)."""
    history = conversations.history(conversations.load(db, keys, org, client, offer_id))
    take_advisor(db, org, particular)  # consultas al asesor de hoy (ADR-0065)
    gate = plan_gate(db, org, particular)  # el plan de otra oferta gasta cupo
    events: queue.Queue[str | None] = queue.Queue()

    def tell(step: Progress) -> None:
        events.put(_event("etapa", {"etapa": step.stage, "herramienta": step.tool}))

    def work() -> None:
        try:
            shown = answer_out(answer(history, tell, gate))
            conversations.append(db, keys, org, client, offer_id, question,
                                 shown.model_dump(mode="json"), shown.text)
            db.commit()
            events.put(_event("resultado", shown.model_dump(mode="json")))
        except Exception as exc:  # ni la pregunta ni la respuesta van al registro
            log.error("La pregunta al asesor falló: %s", type(exc).__name__)
            events.put(_event("error", {"detail": "El asesor no ha podido terminar"}))
        finally:
            events.put(None)

    def stream() -> Iterator[str]:
        threading.Thread(target=work, daemon=True).start()
        while (item := events.get()) is not None:
            yield item

    return StreamingResponse(stream(), media_type="text/event-stream", headers=STREAM_HEADERS)


class TurnOut(BaseModel):
    question: str
    answer: AdvisorAnswerOut
    at: str  # ISO 8601


class ConversationOut(BaseModel):
    """La conversación guardada (ADR-0064): se borra a los `retention_days` días de la última
    pregunta. `advisor_left`: consultas al asesor que le quedan hoy a la organización (ADR-0065)."""

    turns: list[TurnOut]
    retention_days: int
    advisor_left: int


@router.get("/offers/{offer_id}/conversation", response_model=ConversationOut)
def conversation(offer_id: UUID, db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
                 current: SessionDep) -> ConversationOut:
    return _conversation(db, keys, org, client, offer_id, is_particular(current))


@router.delete("/offers/{offer_id}/conversation", status_code=204)
def forget_conversation(offer_id: UUID, db: DbDep, org: OrgDep, client: ClientDep) -> None:
    conversations.forget(db, org, client, offer_id)
    db.commit()


@router.get("/conversation", response_model=ConversationOut)
def general_conversation(db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
                         current: SessionDep) -> ConversationOut:
    """La conversación de «Mi plan» (ADR-0066). 404 sin perfil confirmado: la web no enseña el
    asesor, que sin perfil no puede ordenar ofertas."""
    if latest_profile_id(db, org, client) is None:
        raise HTTPException(status_code=404, detail="Confirma primero tu perfil en /perfil")
    return _conversation(db, keys, org, client, None, is_particular(current))


@router.delete("/conversation", status_code=204)
def forget_general_conversation(db: DbDep, org: OrgDep, client: ClientDep) -> None:
    conversations.forget(db, org, client, None)
    db.commit()


def _conversation(db: Connection, keys: KeyProvider, org: UUID, client: UUID,
                  offer_id: UUID | None, particular: bool) -> ConversationOut:
    turns = conversations.load(db, keys, org, client, offer_id)
    return ConversationOut(
        turns=[TurnOut(question=t.question, answer=AdvisorAnswerOut.model_validate(t.answer),
                       at=t.at) for t in turns],
        retention_days=conversation_days(),
        advisor_left=advisor_left(db, org, particular))


def answer_out(answer: AgentAnswer) -> AdvisorAnswerOut:
    if answer.segments is None:
        return AdvisorAnswerOut(answer=None, text=None, failure=answer.failure, notes=answer.notes)
    return AdvisorAnswerOut(answer=[_segment(s) for s in answer.segments], text=answer.text,
                     failure=None, notes=answer.notes)


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


def _profile(db: Connection, keys: KeyProvider, org: UUID, client: UUID) -> UserProfile:
    profile_id = latest_profile_id(db, org, client)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Confirma primero tu perfil en /perfil")
    return store.load(db, keys, profile_id, org)


def _plan(db: Connection, keys: KeyProvider, org: UUID, client: UUID, book: ParamBook,
          rules: RuleBook, offer_id: UUID,
          particular: bool = False) -> tuple[UserProfile, FullPlan]:
    profile = _profile(db, keys, org, client)
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
