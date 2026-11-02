"""Plan completo de una oferta (F6.7, ADR-0025): sus secciones y la explicación del asesor."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from housefinder.advisor.tools import explain_plan
from housefinder.agent.references import FigureSegment, OfferSegment, Segment
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
from housefinder.api.figures import FigureOut, figure_out
from housefinder.api.search import RentalAdviceOut, advice_out
from housefinder.branding import service as branding
from housefinder.crypto.envelope import KeyProvider
from housefinder.db.connection import Connection
from housefinder.db.profiles import latest_profile_id
from housefinder.db.tiers import record_plan_use
from housefinder.params.book import ParamBook
from housefinder.plans.service import FullPlan, PlanUnavailable, full_plan
from housefinder.profiles import store
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook
from housefinder.reports.pdf import plan_html, plan_pdf, plan_sources
from housefinder.search.service import SearchUnavailable

router = APIRouter(prefix="/plans", tags=["plan"])


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


class SegmentOut(BaseModel):
    kind: Literal["text", "figure", "offer"]
    text: str | None = None
    figure: FigureOut | None = None
    part: str | None = None  # value, low, high o range
    offer: str | None = None
    label: str | None = None


class ExplanationOut(BaseModel):
    segments: list[SegmentOut] | None  # None: el texto no pasó la comprobación
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
        notes=list(plan.notes))


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


@router.post("/offers/{offer_id}/explanation", response_model=ExplanationOut)
def explanation(offer_id: UUID, db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
                book: ParamBookDep, rules: RuleBookDep, llm: LLMDep,
                current: SessionDep) -> ExplanationOut:
    profile, plan = _plan(db, keys, org, client, book, rules, offer_id, is_particular(current))
    explained = explain_plan(db, book, llm, org, plan, profile, rules)
    answer = explained.answer
    return ExplanationOut(
        segments=[_segment(s) for s in answer.segments] if answer.segments is not None else None,
        failure=answer.failure, notes=answer.notes,
        extra_arguments=explained.extra_arguments)


def _plan(db: Connection, keys: KeyProvider, org: UUID, client: UUID, book: ParamBook,
          rules: RuleBook, offer_id: UUID,
          particular: bool = False) -> tuple[UserProfile, FullPlan]:
    profile_id = latest_profile_id(db, org, client)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Confirma primero tu perfil en /perfil")
    profile = store.load(db, keys, profile_id, org)
    record = check_full_plan(db, org, offer_id, particular)  # nivel gratuito (ADR-0041)
    try:
        plan = full_plan(db, book, rules, profile, org, offer_id)
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
