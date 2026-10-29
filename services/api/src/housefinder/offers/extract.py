"""Extracción de los lotes de los anuncios pendientes (ADR-0013).

Cada anuncio con `extraction_status = 'pendiente'` pasa por el LLM; de cada lote se crea una
oferta hija (`kind = 'lote'`) solo con los valores que su cita respalda, y se ubica y deduplica
como cualquier otra oferta. Lo extraído queda `extraida`: no entra en un cálculo hasta que un
usuario lo confirme. Si el modelo declina o la salida no vale, el anuncio sigue pendiente.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from housefinder.agent.extraction import CheckedDocument, CheckedLot, extract
from housefinder.agent.llm import LLMClient, LLMOutputError
from housefinder.db.connection import Connection
from housefinder.db.offers import (
    OfferRow,
    PendingAnnouncement,
    mark_extracted,
    pending_announcements,
    upsert_offer,
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
    located: int = 0
    properties_new: int = 0
    properties_matched: int = 0

    def as_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


def extract_pending(
    conn: Connection, llm: LLMClient, channel: str, locate: Locator, limit: int = 20,
    only: list[str] | None = None,
) -> ExtractionReport:
    report = ExtractionReport()
    for announcement in pending_announcements(conn, channel, limit, only):
        document = announcement_text(announcement)
        try:
            checked = extract(llm, document)
        except LLMOutputError:
            report.failed += 1
            continue
        report.announcements += 1
        report.rejected_fields += checked.rejected
        if checked.is_correction:
            # Una corrección no trae lotes nuevos (F4.4): si el canal no la reconoció por el
            # título, la detecta el LLM y no se crean lotes duplicados.
            report.corrections += 1
            mark_extracted(conn, announcement.id, document_summary(checked))
            conn.commit()
            continue
        links = IngestReport()
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
            locate_and_link(conn, result.offer_id, offer, locate, links)
            report.lots += 1
        mark_extracted(conn, announcement.id, document_summary(checked))
        conn.commit()
        report.located += links.located
        report.properties_new += links.properties_new
        report.properties_matched += links.properties_matched
    return report


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
    }


def _text(value: Decimal | str | None) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: Decimal | str | None) -> Decimal | None:
    return value if isinstance(value, Decimal) else None
