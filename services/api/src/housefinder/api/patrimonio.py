"""Ventas directas del Patrimonio del Estado (ADR-0037), para consultarlas.

Como los anuncios del BOE: el texto de la ficha y de sus hojas de lote, y los lotes que extrajo el
LLM con la cita de cada dato (sin confirmar). Cita de Hacienda en cada respuesta.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from housefinder.db.offers import get_announcement, list_direct_sales, lots_of
from housefinder.offers.channels import patrimonio

from .boe import LotOut, Status, _lot
from .deps import DbDep

router = APIRouter(prefix="/patrimonio", tags=["ventas directas del Patrimonio del Estado"])

ATTRIBUTION = "Origen de los datos: Ministerio de Hacienda (Patrimonio del Estado)"


class DirectSaleOut(BaseModel):
    id: str  # ruta de la ficha en hacienda.gob.es: «VentasDirectas/DEH-OURENSE/…aspx»
    title: str | None
    published_on: str | None
    status: Status
    lots: int
    located_lots: int
    delegation: str | None
    deadline: str | None
    price: str | None


class DirectSaleDetailOut(BaseModel):
    id: str
    title: str | None
    url: str | None
    published_on: str | None
    status: Status
    paragraphs: list[str]
    lots: list[LotOut]
    attribution: str


@router.get("/sales")
def get_sales(db: DbDep) -> list[DirectSaleOut]:
    return [DirectSaleOut(
        id=s.external_id, title=s.title,
        published_on=s.published_on.isoformat() if s.published_on else None,
        status=s.extraction_status,  # type: ignore[arg-type]
        lots=s.lots, located_lots=s.located_lots, delegation=s.delegation, deadline=s.deadline,
        price=s.price,
    ) for s in list_direct_sales(db, patrimonio.NAME)]


@router.get("/sales/{sale_id:path}")
def get_sale(sale_id: str, db: DbDep) -> DirectSaleDetailOut:
    found = get_announcement(db, patrimonio.NAME, sale_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Venta directa no encontrada")
    published = found.published_on.isoformat() if found.published_on else None
    return DirectSaleDetailOut(
        id=found.external_id, title=found.title, url=found.url, published_on=published,
        status=found.extraction_status,  # type: ignore[arg-type]
        paragraphs=found.paragraphs,
        lots=[_lot(lot) for lot in lots_of(db, found.id) if lot.extraction_status != "retirada"],
        attribution=f"{ATTRIBUTION}. Actualizado: {published or 'sin fecha'}",
    )
