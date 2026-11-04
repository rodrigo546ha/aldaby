"""Anuncios de venta y subasta de inmuebles del BOE, sección V (F4.4), para consultarlos.

La API solo traduce: cada anuncio con su texto, los lotes que extrajo el LLM con la cita de cada
dato (sin confirmar: ADR-0013) y las correcciones publicadas después. Cita del BOE en cada
respuesta.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from housefinder.agent.boe_auction_extraction import extract_auction_ai
from housefinder.agent.extraction import FIELD_KINDS
from housefinder.db.offers import corrections_of, get_announcement, list_announcements, lots_of
from housefinder.geo import cartociudad, catastro
from housefinder.offers import boe_portal
from housefinder.offers.channels import boe_v

from .deps import DbDep, OptionalLlmDep, OrgDep

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
    return [
        AnnouncementOut(
            boe_id=a.external_id,
            title=a.title,
            published_on=a.published_on.isoformat() if a.published_on else None,
            status=a.extraction_status,  # type: ignore[arg-type]
            lots=a.lots,
            located_lots=a.located_lots,
            corrections=a.corrections,
        )
        for a in list_announcements(db, boe_v.NAME)
    ]


@router.get("/announcements/{boe_id}")
def get_announcement_detail(boe_id: str, db: DbDep) -> AnnouncementDetailOut:
    found = get_announcement(db, boe_v.NAME, boe_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    corrections = []
    for c in corrections_of(db, found.id):
        detail = get_announcement(db, boe_v.NAME, c.external_id)
        corrections.append(
            CorrectionOut(
                boe_id=c.external_id,
                url=c.url,
                title=c.title,
                published_on=c.published_on.isoformat() if c.published_on else None,
                paragraphs=detail.paragraphs if detail else [],
            )
        )
    return AnnouncementDetailOut(
        boe_id=found.external_id,
        title=found.title,
        url=found.url,
        published_on=found.published_on.isoformat() if found.published_on else None,
        status=found.extraction_status,  # type: ignore[arg-type]
        corrects=found.corrects,
        paragraphs=found.paragraphs,
        lots=[_lot(lot) for lot in lots_of(db, found.id)],
        corrections=corrections,
        attribution=BOE_ATTRIBUTION,
    )


def _lot(lot: Any) -> LotOut:
    extracted: dict[str, Any] = lot.extracted or {}
    fields = []
    for name, kind in FIELD_KINDS.items():
        field: dict[str, Any] = extracted.get(name) or {}
        status = field.get("status")
        fields.append(
            LotFieldOut(
                name=name,
                kind=kind,
                value=field.get("value") if status == "verificado" else None,
                evidence=field.get("evidence"),
                status=status,
                reason=field.get("reason") or "",
            )
        )
    return LotOut(
        id=lot.id,
        title=lot.title,
        status=lot.extraction_status,
        property_type=extracted.get("property_type"),
        fields=fields,
        located=lot.section_code is not None or lot.location_source is not None,
        section_code=lot.section_code,
        municipality=lot.municipality,
        location_attribution=LOCATION_ATTRIBUTION.get(lot.location_source or ""),
    )


# --- Portal de Subastas del BOE (scraping e IA de condiciones y documentos) ---------------------


class AuctionScrapeIn(BaseModel):
    url_or_id: str = Field(
        description="URL o identificador de la subasta (ej: SUB-JA-2026-267866 o https://subastas.boe.es/detalleSubasta.php?idSub=...)"
    )
    download_docs: bool = Field(
        default=True,
        description="Descargar y leer documentos oficiales adjuntos (edicto, certificación)",
    )
    run_ai: bool = Field(
        default=True,
        description="Si se ejecuta el extractor de IA y análisis jurídico de condiciones y cargas",
    )
    max_docs: int = Field(default=3, ge=1, le=10)


class AuctionSearchIn(BaseModel):
    province: str = Field(default="28", description="Código INE de la provincia (28 = Madrid)")
    status: Literal["EJ", "PU", "SU", "CA"] = Field(
        default="EJ", description="Estado: EJ (celebrándose), PU (próxima apertura)"
    )
    goods_type: Literal["I", "V", "M"] = Field(
        default="I", description="Tipo de bien: I (inmuebles), V (vehículos)"
    )
    page: int = Field(default=1, ge=1)
    page_hits: int = Field(default=20, ge=5, le=100)


class ScrapedAuctionOut(BaseModel):
    portal_id: str
    portal_url: str
    tipo_subasta: str | None
    cuenta_expediente: str | None
    anuncio_boe: str | None
    fecha_inicio: str | None
    fecha_conclusion: str | None
    cantidad_reclamada: str | None
    valor_subasta: str | None
    tasacion: str | None
    deposito: str | None
    puja_minima: str | None
    tramos: str | None
    highest_bid: str | None = None
    bid_status: str | None = None
    bidding_state: str = "sin_pujas"
    lot_bids: dict[str, Any] = Field(default_factory=dict)
    court: str | None
    court_address: str | None
    lots: list[dict[str, Any]]
    documents: list[dict[str, str]]
    ai_report: dict[str, Any] | None
    attribution: str


class AuctionSearchResultOut(BaseModel):
    portal_id: str
    court: str | None
    procedure: str | None
    status: str | None
    conclusion_date: str | None
    summary: str | None
    url: str


@router.post("/subastas/scrape")
def post_scrape_auction(
    body: AuctionScrapeIn,
    llm: OptionalLlmDep,
    _org: OrgDep,
) -> ScrapedAuctionOut:
    """Descarga una subasta del Portal del BOE, sus documentos y extrae sus condiciones con IA.
    Solo con sesión: cada llamada sale al Portal y al modelo (ADR-0049)."""
    try:
        portal_id = boe_portal.extract_portal_id(body.url_or_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    with boe_portal.make_client() as client:
        try:
            auction = boe_portal.scrape_auction(client, portal_id)
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"Error consultando el Portal de Subastas: {exc}"
            ) from exc

        downloaded_docs = []
        if body.download_docs and auction.notice.documents:
            downloaded_docs = boe_portal.download_documents(client, auction, max_docs=body.max_docs)

    ai_report = None
    if body.run_ai:
        report = extract_auction_ai(llm, auction, downloaded_docs)
        ai_report = report.as_dict()

    lots_out = []
    for lot in auction.lots:
        lots_out.append(
            {
                "lote_num": lot.lote_num,
                "titulo": lot.titulo,
                "valor_subasta": str(lot.valor_subasta) if lot.valor_subasta is not None else None,
                "tasacion": str(lot.tasacion) if lot.tasacion is not None else None,
                "deposito": str(lot.deposito) if lot.deposito is not None else None,
                "puja_minima": str(lot.puja_minima) if lot.puja_minima is not None else None,
                "tramos": str(lot.tramos) if lot.tramos is not None else None,
                "cantidad_reclamada": str(lot.cantidad_reclamada)
                if lot.cantidad_reclamada is not None
                else None,
                "bienes": [b.__dict__ for b in lot.bienes],
            }
        )

    docs_out = [
        {"id_doc": d.id_doc, "title": d.title, "url": d.url} for d in auction.notice.documents
    ]

    return ScrapedAuctionOut(
        portal_id=auction.portal_id,
        portal_url=auction.portal_url,
        tipo_subasta=auction.notice.tipo_subasta,
        cuenta_expediente=auction.notice.cuenta_expediente,
        anuncio_boe=auction.notice.anuncio_boe,
        fecha_inicio=auction.notice.fecha_inicio,
        fecha_conclusion=auction.notice.fecha_conclusion,
        cantidad_reclamada=str(auction.notice.cantidad_reclamada)
        if auction.notice.cantidad_reclamada is not None
        else None,
        valor_subasta=str(auction.notice.valor_subasta)
        if auction.notice.valor_subasta is not None
        else None,
        tasacion=str(auction.notice.tasacion) if auction.notice.tasacion is not None else None,
        deposito=str(auction.notice.importe_deposito)
        if auction.notice.importe_deposito is not None
        else None,
        puja_minima=str(auction.notice.puja_minima)
        if auction.notice.puja_minima is not None
        else None,
        tramos=str(auction.notice.tramos_entre_pujas)
        if auction.notice.tramos_entre_pujas is not None
        else None,
        highest_bid=str(auction.highest_bid) if auction.highest_bid is not None else None,
        bid_status=auction.bid_status,
        bidding_state=auction.bidding_state,
        lot_bids={str(k): v for k, v in auction.lot_bids.items()},
        court=auction.authority.descripcion if auction.authority else None,
        court_address=auction.authority.direccion if auction.authority else None,
        lots=lots_out,
        documents=docs_out,
        ai_report=ai_report,
        attribution=BOE_ATTRIBUTION,
    )


@router.get("/subastas/{portal_id}")
def get_scrape_auction(
    portal_id: str,
    llm: OptionalLlmDep,
    org: OrgDep,
) -> ScrapedAuctionOut:
    """Consulta directa y extracción de una subasta por su identificador SUB-..."""
    return post_scrape_auction(
        AuctionScrapeIn(url_or_id=portal_id, download_docs=True, run_ai=True),
        llm,
        org,
    )


@router.post("/subastas/search")
def post_search_auctions(
    body: AuctionSearchIn,
    _org: OrgDep,
) -> list[AuctionSearchResultOut]:
    """Búsqueda avanzada de subastas activas en el Portal del BOE."""
    with boe_portal.make_client() as client:
        try:
            results = boe_portal.search_boe_auctions(
                client,
                province=body.province,
                status=body.status,
                goods_type=body.goods_type,
                page=body.page,
                page_hits=body.page_hits,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"Error buscando en el Portal de Subastas: {exc}"
            ) from exc

    return [
        AuctionSearchResultOut(
            portal_id=r.portal_id,
            court=r.court,
            procedure=r.procedure,
            status=r.status,
            conclusion_date=r.conclusion_date,
            summary=r.summary,
            url=r.url,
        )
        for r in results
    ]
