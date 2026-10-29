"""Anuncios de venta y subasta de inmuebles del BOE, sección V (F4.4), para consultarlos.

La API solo traduce: cada anuncio con su texto, los lotes que extrajo el LLM con la cita de cada
dato (sin confirmar: ADR-0013) y las correcciones publicadas después. Cita del BOE en cada
respuesta.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from housefinder.agent.extraction import FIELD_KINDS
from housefinder.db.offers import corrections_of, get_announcement, list_announcements, lots_of
from housefinder.geo import cartociudad, catastro
from housefinder.offers.channels import boe_v

from .deps import DbDep

router = APIRouter(prefix="/boe", tags=["anuncios del BOE"])

BOE_ATTRIBUTION = "Fuente: Agencia Estatal Boletín Oficial del Estado (www.boe.es)"
LOCATION_ATTRIBUTION = {"catastro": catastro.ATTRIBUTION, "cartociudad": cartociudad.ATTRIBUTION}
Status = Literal["no_aplica", "pendiente", "extraida", "confirmada"]


class AnnouncementOut(BaseModel):
    boe_id: str
    title: str | None
    published_on: str | None
    status: Status
    lots: int
    located_lots: int
    corrections: int


class LotFieldOut(BaseModel):
    name: str
    kind: Literal["number", "cadastral", "text"]
    value: str | None  # solo si su cita lo respalda
    evidence: str | None
    status: Literal["verificado", "rechazado", "ausente"] | None
    reason: str


class LotOut(BaseModel):
    id: UUID
    title: str | None
    status: Status
    property_type: str | None
    fields: list[LotFieldOut]
    located: bool
    section_code: str | None
    municipality: str | None
    location_attribution: str | None


class CorrectionOut(BaseModel):
    boe_id: str
    url: str | None
    published_on: str | None
    title: str | None
    paragraphs: list[str]


class AnnouncementDetailOut(BaseModel):
    boe_id: str
    title: str | None
    url: str | None
    published_on: str | None
    status: Status
    corrects: str | None
    paragraphs: list[str]
    lots: list[LotOut]
    corrections: list[CorrectionOut]
    attribution: str


@router.get("/announcements")
def get_announcements(db: DbDep) -> list[AnnouncementOut]:
    return [AnnouncementOut(
        boe_id=a.external_id, title=a.title,
        published_on=a.published_on.isoformat() if a.published_on else None,
        status=a.extraction_status,  # type: ignore[arg-type]
        lots=a.lots, located_lots=a.located_lots, corrections=a.corrections,
    ) for a in list_announcements(db, boe_v.NAME)]


@router.get("/announcements/{boe_id}")
def get_announcement_detail(boe_id: str, db: DbDep) -> AnnouncementDetailOut:
    found = get_announcement(db, boe_v.NAME, boe_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    corrections = []
    for c in corrections_of(db, found.id):
        detail = get_announcement(db, boe_v.NAME, c.external_id)
        corrections.append(CorrectionOut(
            boe_id=c.external_id, url=c.url, title=c.title,
            published_on=c.published_on.isoformat() if c.published_on else None,
            paragraphs=detail.paragraphs if detail else [],
        ))
    return AnnouncementDetailOut(
        boe_id=found.external_id, title=found.title, url=found.url,
        published_on=found.published_on.isoformat() if found.published_on else None,
        status=found.extraction_status,  # type: ignore[arg-type]
        corrects=found.corrects, paragraphs=found.paragraphs,
        lots=[_lot(lot) for lot in lots_of(db, found.id)],
        corrections=corrections, attribution=BOE_ATTRIBUTION,
    )


def _lot(lot: Any) -> LotOut:
    extracted: dict[str, Any] = lot.extracted or {}
    fields = []
    for name, kind in FIELD_KINDS.items():
        field: dict[str, Any] = extracted.get(name) or {}
        status = field.get("status")
        fields.append(LotFieldOut(
            name=name, kind=kind, value=field.get("value") if status == "verificado" else None,
            evidence=field.get("evidence"), status=status, reason=field.get("reason") or "",
        ))
    return LotOut(
        id=lot.id, title=lot.title, status=lot.extraction_status,
        property_type=extracted.get("property_type"), fields=fields,
        located=lot.section_code is not None or lot.location_source is not None,
        section_code=lot.section_code, municipality=lot.municipality,
        location_attribution=LOCATION_ATTRIBUTION.get(lot.location_source or ""),
    )
