"""Ofertas privadas: enlace o texto pegado por el usuario y su confirmación (F4.1, ADR-0015).

La API solo traduce. La descarga es inmediata y, si el sitio no la permite, responde 422 con el
motivo y `paste_text: true` para que el usuario pegue el texto. La extracción va a la cola: la
oferta queda `pendiente` hasta que el trabajo `extract_link` la deja `extraida`.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from housefinder.agent.extraction import LISTING_KINDS
from housefinder.db.offers import PrivateOffer, get_private_offer, list_private_offers
from housefinder.geo import cartociudad, catastro
from housefinder.offers.link import LinkRefused
from housefinder.offers.locate import offer_locator
from housefinder.offers.pasted import ConfirmationError, confirm, submit_link, submit_text

from .deps import DbDep, GeocoderDep, LinkClientDep, OrgDep, ParcelFinderDep, ResolverDep

router = APIRouter(prefix="/offers", tags=["ofertas"])

ExtractionStatus = Literal["pendiente", "extraida", "confirmada"]
LOCATION_ATTRIBUTION = {"catastro": catastro.ATTRIBUTION, "cartociudad": cartociudad.ATTRIBUTION}


class LinkIn(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


class TextIn(BaseModel):
    text: str = Field(min_length=20, max_length=60_000)
    url: str | None = Field(default=None, max_length=2000)


class ConfirmIn(BaseModel):
    operation: Literal["venta", "alquiler", "desconocida"] | None = None
    values: dict[str, str | None]


class FieldOut(BaseModel):
    name: str
    kind: Literal["number", "cadastral", "text"]
    proposed: str | None  # valor extraído y verificado contra su cita
    evidence: str | None
    status: Literal["verificado", "rechazado", "ausente"] | None  # None: aún sin extraer
    reason: str
    confirmed: str | None
    origin: Literal["extraido", "corregido", "usuario"] | None


class OfferSummary(BaseModel):
    id: UUID
    url: str | None
    title: str | None
    status: ExtractionStatus
    first_seen: str


class OfferOut(OfferSummary):
    source: Literal["enlace", "texto"]
    images: list[str]
    operation: str | None  # la confirmada, o la propuesta si aún no hay confirmación
    property_type: str | None
    fields: list[FieldOut]
    located: bool
    location_source: str | None  # 'catastro' o 'cartociudad'
    attribution: str | None  # cita de la fuente de la ubicación
    section_code: str | None
    municipality: str | None


@router.post("/link", status_code=201)
def post_link(body: LinkIn, db: DbDep, org: OrgDep, client: LinkClientDep,
              resolve: ResolverDep) -> OfferOut:
    try:
        submitted = submit_link(db, org, body.url, client, resolve)
    except LinkRefused as exc:
        raise HTTPException(status_code=422,
                            detail={"reason": exc.reason, "paste_text": True}) from exc
    return _detail(db, org, submitted.offer_id)


@router.post("/text", status_code=201)
def post_text(body: TextIn, db: DbDep, org: OrgDep) -> OfferOut:
    submitted = submit_text(db, org, body.text, body.url)
    return _detail(db, org, submitted.offer_id)


@router.get("")
def get_offers(db: DbDep, org: OrgDep) -> list[OfferSummary]:
    return [_summary(o) for o in list_private_offers(db, org)]


@router.get("/{offer_id}")
def get_offer(offer_id: UUID, db: DbDep, org: OrgDep) -> OfferOut:
    return _detail(db, org, offer_id)


@router.post("/{offer_id}/confirm")
def post_confirm(offer_id: UUID, body: ConfirmIn, db: DbDep, org: OrgDep,
                 geocoder: GeocoderDep, parcels: ParcelFinderDep) -> OfferOut:
    try:
        done = confirm(db, org, offer_id, body.values, body.operation,
                       offer_locator(db, geocoder, parcels))
    except ConfirmationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not done:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    return _detail(db, org, offer_id)


def _summary(offer: PrivateOffer) -> OfferSummary:
    return OfferSummary(id=offer.id, url=offer.url, title=offer.title,
                        status=offer.extraction_status,  # type: ignore[arg-type]
                        first_seen=offer.first_seen.isoformat())


def _detail(db: DbDep, org: UUID, offer_id: UUID) -> OfferOut:
    offer = get_private_offer(db, offer_id, org)
    if offer is None:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    extracted: dict[str, Any] = offer.extracted or {}
    listing = extracted.get("listing") or {}
    proposed = listing.get("fields") or {}
    confirmed = extracted.get("confirmed") or {}
    confirmed_fields = confirmed.get("fields") or {}
    fields = []
    for name, kind in LISTING_KINDS.items():
        suggestion = proposed.get(name) or {}
        status = suggestion.get("status")
        chosen = confirmed_fields.get(name) or {}
        fields.append(FieldOut(
            name=name, kind=kind,
            proposed=suggestion.get("value") if status == "verificado" else None,
            evidence=suggestion.get("evidence"), status=status,
            reason=suggestion.get("reason") or "",
            confirmed=chosen.get("value"), origin=chosen.get("origin"),
        ))
    return OfferOut(
        **_summary(offer).model_dump(),
        source=offer.raw.get("source", "enlace"),
        images=list(offer.raw.get("images") or []),
        operation=confirmed.get("operation") or listing.get("operation"),
        property_type=listing.get("property_type"),
        fields=fields,
        located=offer.property_id is not None,
        location_source=offer.location_source,
        attribution=LOCATION_ATTRIBUTION.get(offer.location_source or ""),
        section_code=offer.section_code,
        municipality=offer.municipality,
    )
