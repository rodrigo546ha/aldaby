"""Extracción de los lotes de los anuncios pendientes (ADR-0013).

Cada anuncio con `extraction_status = 'pendiente'` pasa por el LLM; de cada lote se crea una
oferta hija (`kind = 'lote'`) solo con los valores que su cita respalda, y se ubica y deduplica
como cualquier otra oferta. Lo extraído queda `extraida`: no entra en un cálculo hasta que un
usuario lo confirme. Si el modelo declina o la salida no vale, el anuncio sigue pendiente.

Un lote que no se pudo ubicar por un fallo de un servicio o porque su provincia no tenía secciones
cargadas se vuelve a ubicar al empezar la siguiente vez, con lo ya extraído y sin el LLM
(ADR-0031).

Lo que propone el modelo se guarda en el anuncio (`proposed`): si cambian las reglas de la
comprobación, `recheck` vuelve a comprobarlo sin el LLM. Una extracción nueva de un anuncio
actualiza sus lotes sin confirmar y retira los que ya no encuentra; los confirmados no se tocan
(ADR-0033).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from housefinder.agent.extraction import (
    CheckedDocument,
    CheckedLot,
    ProposalMismatch,
    extract,
    recheck_document,
)
from housefinder.agent.llm import LLMClient, LLMOutputError
from housefinder.db.connection import Connection
from housefinder.db.offers import (
    LotToRelocate,
    OfferRow,
    PendingAnnouncement,
    lots_to_relocate,
    mark_extracted,
    pending_announcements,
    refresh_lot,
    retire_lots,
    upsert_offer,
    with_proposals,
)
from housefinder.offers.ingest import IngestReport, Locator, locate_and_link
from housefinder.offers.model import NormalizedOffer, RawItem


@dataclass
class ExtractionReport:
    announcements: int = 0
    lots: int = 0
    corrections: int = 0
    rejected_fields: int = 0
    failed: int = 0  # el modelo declinó o la salida no valía: siguen pendientes
    retried: int = 0  # lotes de otras veces que se volvieron a ubicar, sin el LLM
    retired: int = 0  # lotes que una extracción nueva del anuncio ya no encuentra
    located: int = 0
    properties_new: int = 0
    properties_matched: int = 0
    unlocated: list[dict[str, Any]] = field(default_factory=list)  # lote, motivo y si se reintenta

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "unlocated": list(self.unlocated)}


def extract_pending(
    conn: Connection, llm: LLMClient, channel: str, locate: Locator, limit: int = 20,
    only: list[str] | None = None, recheck: bool = False,
) -> ExtractionReport:
    """Extrae los anuncios pendientes. Con `recheck`, en lugar de eso vuelve a comprobar, sin el
    LLM, lo que el modelo propuso para los anuncios ya extraídos."""
    report = ExtractionReport()
    links = IngestReport()
    if only is None and not recheck:
        for pending in lots_to_relocate(conn, channel):
            _locate(conn, pending.id, relocated_offer(pending), locate, links, report)
            report.retried += 1
            conn.commit()
    if recheck:
        for announcement, proposed in with_proposals(conn, channel, only):
            try:
                checked = recheck_document(announcement_text(announcement), proposed)
            except ProposalMismatch:  # se partió con otras reglas: se extrae otra vez con el LLM
                report.failed += 1
                continue
            _store(conn, channel, announcement, checked, locate, links, report)
    else:
        for announcement in pending_announcements(conn, channel, limit, only):
            try:
                checked = extract(llm, announcement_text(announcement))
            except LLMOutputError:
                report.failed += 1
                continue
            _store(conn, channel, announcement, checked, locate, links, report)
    report.located = links.located
    report.properties_new = links.properties_new
    report.properties_matched = links.properties_matched
    return report


def _store(conn: Connection, channel: str, announcement: PendingAnnouncement,
           checked: CheckedDocument, locate: Locator, links: IngestReport,
           report: ExtractionReport) -> None:
    report.announcements += 1
    report.rejected_fields += checked.rejected
    if checked.is_correction:
        # Una corrección no trae lotes nuevos (F4.4): si el canal no la reconoció por el
        # título, la detecta el LLM y no se crean lotes duplicados.
        report.corrections += 1
        mark_extracted(conn, announcement.id, document_summary(checked))
        conn.commit()
        return
    kept: list[str] = []
    for index, lot in enumerate(checked.lots, start=1):
        offer = lot_offer(announcement, lot, index)
        row = OfferRow(
            channel=channel, external_id=offer.external_id, kind="lote", title=offer.title,
            url=offer.url, published_on=offer.published_on, description=None,
            asking_price=None, auction_min_bid=offer.auction_min_bid,
            deposit_required=offer.deposit_required, address=offer.address,
            cadastral_ref=offer.cadastral_ref, built_area_m2=offer.built_area_m2,
            extraction_status="extraida", source_id=announcement.source_id,
            parent_id=announcement.id, extracted=offer.extracted,
        )
        raw = {"anuncio": announcement.external_id, "lote": index}
        result = upsert_offer(conn, row, raw, RawItem("", "", None, raw).sha256)
        if not result.created:
            refresh_lot(conn, result.offer_id, row)
        _locate(conn, result.offer_id, offer, locate, links, report)
        kept.append(offer.external_id)
        report.lots += 1
    report.retired += retire_lots(conn, announcement.id, kept)
    mark_extracted(conn, announcement.id, document_summary(checked))
    conn.commit()


def _locate(conn: Connection, offer_id: UUID, offer: NormalizedOffer, locate: Locator,
            links: IngestReport, report: ExtractionReport) -> None:
    missed = locate_and_link(conn, offer_id, offer, locate, links)
    if missed is not None:
        report.unlocated.append({"offer": offer.external_id, "reason": missed.reason,
                                 "retry": missed.retry})


def relocated_offer(lot: LotToRelocate) -> NormalizedOffer:
    """El lote como se extrajo, para volver a ubicarlo sin el LLM."""
    return NormalizedOffer(
        external_id=lot.external_id, kind="lote", url=lot.url or "", title=lot.title,
        published_on=lot.published_on, address=lot.address, cadastral_ref=lot.cadastral_ref,
        municipality=_verified(lot.extracted, "municipality"),
        province=_verified(lot.extracted, "province"), built_area_m2=lot.built_area_m2,
        extraction_status="extraida", extracted=lot.extracted,
    )


def _verified(extracted: dict[str, Any], name: str) -> str | None:
    checked = extracted.get(name)
    if not isinstance(checked, dict) or checked.get("status") != "verificado":
        return None
    value = checked.get("value")
    return value if isinstance(value, str) else None


def announcement_text(announcement: PendingAnnouncement) -> str:
    paragraphs = announcement.raw.get("texto", [])
    return "\n".join([announcement.title or "", *paragraphs]).strip()


def lot_offer(announcement: PendingAnnouncement, lot: CheckedLot, index: int) -> NormalizedOffer:
    label = lot.value("label")
    address = _text(lot.value("address"))
    municipality = _text(lot.value("municipality"))
    province = _text(lot.value("province"))
    # Para geocodificar: dirección con municipio y provincia si no los lleva ya.
    full_address = ", ".join(p for p in (address, municipality, province) if p) if address else None
    return NormalizedOffer(
        external_id=f"{announcement.external_id}#{index}",
        kind="lote",
        url=announcement.url or "",
        title=f"{label} · {announcement.title}" if label else announcement.title,
        published_on=announcement.published_on,
        address=full_address,
        municipality=municipality,
        province=province,
        cadastral_ref=_text(lot.value("cadastral_ref")),
        built_area_m2=_number(lot.value("built_area_m2")),
        auction_min_bid=_number(lot.value("price")),
        deposit_required=_number(lot.value("deposit")),
        extraction_status="extraida",
        extracted=lot.as_dict(),
    )


def document_summary(checked: CheckedDocument) -> dict[str, Any]:
    return {
        "lots": len(checked.lots),
        "is_correction": checked.is_correction,
        "corrected_reference": checked.corrected_reference.as_dict(),
        "rejected_fields": checked.rejected,
        "proposed": checked.proposed,
    }


def _text(value: Decimal | str | None) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: Decimal | str | None) -> Decimal | None:
    return value if isinstance(value, Decimal) else None
