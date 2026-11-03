"""Búsqueda inversa (F6.5, ADR-0023): las ofertas que encajan con el plan del usuario, con el
tipo de alquiler y la gestión recomendados en cada una (F6.6, ADR-0024)."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from housefinder.api.deps import ClientDep, DbDep, KeysDep, OrgDep, ParamBookDep, RuleBookDep
from housefinder.api.figures import FigureOut, figure_out
from housefinder.db.offers import searchable_offer, set_rent_expectation
from housefinder.db.profiles import latest_profile_id
from housefinder.profiles import store
from housefinder.search.rental import OfferRentalAdvice
from housefinder.search.service import SearchUnavailable, search

router = APIRouter(prefix="/search", tags=["búsqueda"])


class RequirementOut(BaseModel):
    code: str
    description: str
    source_url: str


class RentalTypeOut(BaseModel):
    rental_type: str
    allowed: bool
    regime: str
    requirements: list[RequirementOut]
    irpf_reduction: bool | None  # None: por confirmar
    rule_ids: list[str]
    management: str
    management_reason: str
    figures: list[FigureOut]  # renta, cash flow con su gestión y coste de delegar
    notes: list[str]


class RentalAdviceOut(BaseModel):
    recommended: str | None
    reasons: list[str]
    types: list[RentalTypeOut]
    scenario: list[str]  # lo que cambiaría con las reglas pendientes
    notes: list[str]


class ScoredOut(BaseModel):
    offer_id: UUID
    kind: str
    title: str | None
    url: str | None
    auction: bool
    passes: bool
    reasons: list[str]
    metric: FigureOut | None
    figures: list[FigureOut]
    notes: list[str]
    advice: RentalAdviceOut | None
    # El punto del inmueble y de dónde sale, para el mapa (ADR-0051)
    lon: float | None = None
    lat: float | None = None
    location_source: str | None = None


class SkippedOut(BaseModel):
    offer_id: UUID
    title: str | None
    reason: str


class SearchOut(BaseModel):
    ranked: list[ScoredOut]
    skipped: list[SkippedOut]
    market: list[FigureOut]
    notes: list[str]


@router.get("", response_model=SearchOut)
def reverse_search(db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep,
                   book: ParamBookDep, rules: RuleBookDep) -> SearchOut:
    profile_id = latest_profile_id(db, org, client)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Confirma primero tu perfil en /perfil")
    profile = store.load(db, keys, profile_id, org)
    try:
        report = search(db, book, rules, profile, org)
    except SearchUnavailable as exc:
        raise HTTPException(status_code=422, detail=exc.reasons) from exc
    return SearchOut(
        ranked=[ScoredOut(
            offer_id=s.offer_id, kind=s.kind, title=s.title, url=s.url, auction=s.auction,
            passes=s.verdict.passes, reasons=list(s.verdict.reasons),
            metric=figure_out(s.verdict.metric) if s.verdict.metric else None,
            figures=[figure_out(f) for f in s.figures], notes=list(s.notes),
            advice=advice_out(s.advice) if s.advice else None,
            lon=s.lon, lat=s.lat, location_source=s.location_source)
            for s in report.ranked],
        skipped=[SkippedOut(offer_id=s.offer_id, title=s.title, reason=s.reason)
                 for s in report.skipped],
        market=[figure_out(f) for f in report.market], notes=report.notes)


class RentExpectationIn(BaseModel):
    """Lo que el usuario espera sacar al mes con un tipo sin renta pública; null lo borra."""

    rental_type: Literal["temporada", "habitaciones", "turistico"]
    monthly_income: Decimal | None = Field(default=None, gt=0, le=100000)


@router.put("/offers/{offer_id}/rent", status_code=204)
def save_rent_expectation(offer_id: UUID, body: RentExpectationIn, db: DbDep,
                          org: OrgDep) -> None:
    if not searchable_offer(db, offer_id, org):
        raise HTTPException(status_code=404, detail="No existe esa oferta en tu búsqueda")
    set_rent_expectation(db, org, offer_id, body.rental_type, body.monthly_income)
    db.commit()


def advice_out(advice: OfferRentalAdvice) -> RentalAdviceOut:
    return RentalAdviceOut(
        recommended=advice.advice.recommended, reasons=list(advice.advice.reasons),
        types=[RentalTypeOut(
            rental_type=t.option.rental_type, allowed=t.option.allowed, regime=t.option.regime,
            requirements=[RequirementOut(code=r.code, description=r.description,
                                         source_url=r.source_url)
                          for r in t.option.requirements],
            irpf_reduction=t.option.irpf_reduction, rule_ids=list(t.option.rule_ids),
            management=t.management, management_reason=t.management_reason,
            figures=[figure_out(f) for f in t.figures()], notes=list(t.notes))
            for t in advice.advice.types],
        scenario=list(advice.scenario), notes=list(advice.notes))
