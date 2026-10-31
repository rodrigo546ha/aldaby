"""Búsqueda inversa (F6.5, ADR-0023): las ofertas que encajan con el plan del usuario."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from housefinder.api.deps import DbDep, KeysDep, OrgDep, ParamBookDep, RuleBookDep
from housefinder.api.figures import FigureOut, figure_out
from housefinder.db.profiles import latest_profile_id
from housefinder.profiles import store
from housefinder.search.service import SearchUnavailable, search

router = APIRouter(prefix="/search", tags=["búsqueda"])


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
def reverse_search(db: DbDep, keys: KeysDep, org: OrgDep, book: ParamBookDep,
                   rules: RuleBookDep) -> SearchOut:
    profile_id = latest_profile_id(db, org)
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
            figures=[figure_out(f) for f in s.figures], notes=list(s.notes))
            for s in report.ranked],
        skipped=[SkippedOut(offer_id=s.offer_id, title=s.title, reason=s.reason)
                 for s in report.skipped],
        market=[figure_out(f) for f in report.market], notes=report.notes)
