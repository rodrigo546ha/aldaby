"""Ingesta de ofertas: guarda lo recibido, normaliza, ubica, deduplica y asigna sección (F4.6).

Deduplicación del inmueble:
1. Por referencia catastral (los 20 caracteres identifican el inmueble).
2. Si no la hay, por cercanía: a menos de 30 metros y con una superficie que no difiera más de
   un 5 % (si las dos se conocen). Supuesto propio, revisable con datos reales.
Una oferta sin ubicación se guarda igual, sin inmueble, a la espera de la extracción.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from housefinder.db.connection import Connection
from housefinder.db.offers import (
    OfferRow,
    create_property,
    find_property_by_ref,
    find_property_near,
    link_offer,
    mark_unlocated,
    offer_property,
    upsert_offer,
)
from housefinder.db.sections import latest_vintage, section_at
from housefinder.offers.model import Channel, NormalizedOffer, RawItem

NEAR_METERS = 30.0
AREA_TOLERANCE = Decimal("0.05")


@dataclass(frozen=True)
class Point:
    lon: float
    lat: float
    source: str  # 'canal', 'cartociudad', 'catastro'…


@dataclass(frozen=True)
class Unlocated:
    """Por qué no se pudo ubicar (ADR-0031)."""

    reason: str
    retry: bool  # otro intento puede ubicarla: un servicio falló o falta cargar su provincia


# Ubica una oferta: punto, o por qué no se puede (None si no hay nada que contar).
Locator = Callable[[NormalizedOffer], Point | Unlocated | None]


@dataclass
class IngestReport:
    items: int = 0
    offers_new: int = 0
    offers_changed: int = 0
    offers_unchanged: int = 0
    pending_extraction: int = 0
    located: int = 0
    properties_new: int = 0
    properties_matched: int = 0

    def as_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


def ingest(
    conn: Connection, channel: Channel, items: Iterable[RawItem], locate: Locator
) -> IngestReport:
    report = IngestReport()
    for item in items:
        report.items += 1
        for offer in channel.parse(item):
            _ingest_offer(conn, channel, item, offer, locate, report)
        conn.commit()
    return report


def _ingest_offer(
    conn: Connection,
    channel: Channel,
    item: RawItem,
    offer: NormalizedOffer,
    locate: Locator,
    report: IngestReport,
) -> None:
    result = upsert_offer(conn, _row(channel, offer), item.raw, item.sha256)
    if result.created:
        report.offers_new += 1
    elif result.raw_changed:
        report.offers_changed += 1
    else:
        report.offers_unchanged += 1
    if offer.extraction_status == "pendiente":
        report.pending_extraction += 1
    locate_and_link(conn, result.offer_id, offer, locate, report)


def locate_and_link(
    conn: Connection,
    offer_id: UUID,
    offer: NormalizedOffer,
    locate: Locator,
    report: IngestReport,
) -> Unlocated | None:
    """Ubica la oferta y la enlaza con su inmueble (existente o nuevo, con su sección). Si no se
    puede, guarda el motivo en la oferta y lo devuelve."""
    if offer_property(conn, offer_id) is not None or not offer.locatable:
        return None
    point = (Point(offer.lon, offer.lat, "canal")
             if offer.lon is not None and offer.lat is not None else locate(offer))
    if not isinstance(point, Point):
        if point is not None:
            mark_unlocated(conn, offer_id, point.reason, point.retry)
        return point
    report.located += 1
    property_id = _match_property(conn, offer, point)
    if property_id is None:
        vintage = latest_vintage(conn)
        hit = section_at(conn, point.lon, point.lat, vintage) if vintage else None
        property_id = create_property(
            conn, lon=point.lon, lat=point.lat, cadastral_ref=offer.cadastral_ref,
            address=offer.address, built_area_m2=offer.built_area_m2,
            municipality=hit.municipality if hit else None,
            section=(hit.code, hit.vintage) if hit else None,
        )
        report.properties_new += 1
    else:
        report.properties_matched += 1
    link_offer(conn, offer_id, property_id, point.source)
    return None


def _match_property(conn: Connection, offer: NormalizedOffer, point: Point) -> UUID | None:
    if offer.cadastral_ref:
        found = find_property_by_ref(conn, offer.cadastral_ref)
        if found is not None:
            return found
    return find_property_near(conn, point.lon, point.lat, NEAR_METERS, offer.built_area_m2,
                              AREA_TOLERANCE)


def _row(channel: Channel, offer: NormalizedOffer) -> OfferRow:
    return OfferRow(
        channel=channel.name, external_id=offer.external_id, kind=offer.kind,
        title=offer.title, url=offer.url, published_on=offer.published_on,
        description=offer.description, asking_price=offer.asking_price,
        auction_min_bid=offer.auction_min_bid, deposit_required=offer.deposit_required,
        address=offer.address, cadastral_ref=offer.cadastral_ref,
        built_area_m2=offer.built_area_m2, extraction_status=offer.extraction_status,
        source_id=channel.source_id,
    )
