"""Feeds de las agencias de la organización y su cartera (ADR-0038).

El profesional da de alta el feed de una agencia declarando que tiene su consentimiento por
escrito; la URL se cifra y nunca vuelve a salir de la API. La cartera se lee en el trabajo diario.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from housefinder.db.agency_feeds import deactivate_org_feed, org_feeds
from housefinder.db.offers import list_feed_listings, retire_missing
from housefinder.feeds.registry import FeedError, register
from housefinder.offers.channels.agency_feed import NAME

from .deps import DbDep, KeysDep, OrgDep

router = APIRouter(prefix="/feeds", tags=["feeds de agencias"])

Scope = Literal["organizacion", "todos"]


class FeedOut(BaseModel):
    id: UUID
    agency_name: str
    scope: Scope
    consent_on: date
    consent_ref: str
    created_at: str
    last_run_at: str | None
    listings: int | None  # inmuebles en venta en el último feed leído
    without_location: int | None
    retired: int | None
    error: str | None


class FeedIn(BaseModel):
    agency_name: str = Field(max_length=200)
    url: str = Field(max_length=2000)
    scope: Scope
    consent_on: date
    consent_ref: str = Field(max_length=300)
    consent_confirmed: bool  # «tengo el consentimiento por escrito de la agencia»


class ListingOut(BaseModel):
    id: UUID
    title: str | None
    url: str | None
    asking_price: Decimal | None
    built_area_m2: Decimal | None
    municipality: str | None
    province: str | None
    property_type: str | None
    agency: str | None
    public: bool
    located: bool
    section_code: str | None


def _feed(row: Any) -> FeedOut:
    report: dict[str, Any] = row.last_report or {}
    return FeedOut(
        id=row.id, agency_name=row.agency_name, scope=row.scope, consent_on=row.consent_on,
        consent_ref=row.consent_ref, created_at=row.created_at.isoformat(),
        last_run_at=row.last_run_at.isoformat() if row.last_run_at else None,
        listings=report.get("listings"), without_location=report.get("without_location"),
        retired=report.get("retired"), error=report.get("error"),
    )


@router.get("", response_model=list[FeedOut])
def list_feeds(db: DbDep, org: OrgDep) -> list[FeedOut]:
    return [_feed(row) for row in org_feeds(db, org)]


@router.post("", status_code=201, response_model=FeedOut)
def create_feed(body: FeedIn, db: DbDep, keys: KeysDep, org: OrgDep) -> FeedOut:
    if not body.consent_confirmed:
        raise HTTPException(status_code=422,
                            detail="Hace falta el consentimiento por escrito de la agencia")
    try:
        feed_id = register(db, keys, org, body.agency_name, body.url, body.scope,
                           body.consent_on, body.consent_ref)
    except FeedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return next(_feed(row) for row in org_feeds(db, org) if row.id == feed_id)


@router.delete("/{feed_id}", status_code=204)
def delete_feed(feed_id: UUID, db: DbDep, org: OrgDep) -> None:
    """Deja de leer el feed y retira sus ofertas. Las que la agencia cedió a todos las retira el
    trabajo diario: la API no puede tocar las ofertas públicas."""
    if not deactivate_org_feed(db, feed_id, org):
        raise HTTPException(status_code=404, detail="Feed no encontrado")
    retire_missing(db, NAME, f"feed-agencia-{feed_id}", [])
    db.commit()


@router.get("/listings", response_model=list[ListingOut])
def listings(db: DbDep, org: OrgDep) -> list[ListingOut]:
    return [ListingOut(**row.__dict__) for row in list_feed_listings(db, org)]
