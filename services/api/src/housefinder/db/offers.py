"""SQL de ofertas e inmuebles (F4, F4.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class OfferRow:
    """Lo que se guarda de una oferta normalizada."""

    channel: str
    external_id: str
    kind: str
    title: str | None
    url: str | None
    published_on: date | None
    description: str | None
    asking_price: Decimal | None
    auction_min_bid: Decimal | None
    deposit_required: Decimal | None
    address: str | None
    cadastral_ref: str | None
    built_area_m2: Decimal | None
    extraction_status: str
    source_id: str | None
    org_id: UUID | None = None
    parent_id: UUID | None = None
    extracted: dict[str, Any] | None = None  # campos extraídos con su evidencia


@dataclass(frozen=True)
class UpsertResult:
    offer_id: UUID
    created: bool
    raw_changed: bool  # lo recibido es distinto de la última versión


def upsert_offer(
    conn: psycopg.Connection, offer: OfferRow, raw: dict[str, Any], raw_sha256: str
) -> UpsertResult:
    """Inserta o actualiza la oferta por (canal, identificador) y guarda la versión recibida."""
    row = conn.execute(
        """
        INSERT INTO offers (channel, external_id, kind, title, url, published_on, description,
                            asking_price, auction_min_bid, deposit_required, address,
                            cadastral_ref, built_area_m2, extraction_status, source_id, org_id,
                            parent_id, extracted, raw, raw_sha256)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (channel, external_id) DO UPDATE SET
            last_seen = now(),
            title = EXCLUDED.title, url = EXCLUDED.url, description = EXCLUDED.description,
            raw = EXCLUDED.raw, raw_sha256 = EXCLUDED.raw_sha256
        RETURNING id, (xmax = 0) AS created
        """,
        (offer.channel, offer.external_id, offer.kind, offer.title, offer.url,
         offer.published_on, offer.description, offer.asking_price, offer.auction_min_bid,
         offer.deposit_required, offer.address, offer.cadastral_ref, offer.built_area_m2,
         offer.extraction_status, offer.source_id, offer.org_id, offer.parent_id,
         Jsonb(offer.extracted) if offer.extracted is not None else None, Jsonb(raw), raw_sha256),
    ).fetchone()
    if row is None:
        raise RuntimeError("La inserción de la oferta no devolvió fila")
    offer_id, created = row
    version = conn.execute(
        """
        INSERT INTO offer_raw_versions (offer_id, sha256, raw) VALUES (%s, %s, %s)
        ON CONFLICT (offer_id, sha256) DO NOTHING RETURNING id
        """,
        (offer_id, raw_sha256, Jsonb(raw)),
    ).fetchone()
    return UpsertResult(offer_id, bool(created), version is not None and not created)


def offer_property(conn: psycopg.Connection, offer_id: UUID) -> UUID | None:
    row = conn.execute("SELECT property_id FROM offers WHERE id = %s", (offer_id,)).fetchone()
    return row[0] if row else None


def link_offer(
    conn: psycopg.Connection, offer_id: UUID, property_id: UUID, location_source: str
) -> None:
    conn.execute(
        "UPDATE offers SET property_id = %s, location_source = %s WHERE id = %s",
        (property_id, location_source, offer_id),
    )


def unlink_offer(conn: psycopg.Connection, offer_id: UUID) -> None:
    conn.execute("UPDATE offers SET property_id = NULL, location_source = NULL WHERE id = %s",
                 (offer_id,))


def find_property_by_ref(conn: psycopg.Connection, cadastral_ref: str) -> UUID | None:
    row = conn.execute(
        "SELECT id FROM properties WHERE cadastral_ref = %s", (cadastral_ref,)
    ).fetchone()
    return row[0] if row else None


def find_property_near(
    conn: psycopg.Connection,
    lon: float,
    lat: float,
    meters: float,
    built_area_m2: Decimal | None,
    area_tolerance: Decimal,
) -> UUID | None:
    """Inmueble más cercano a menos de `meters` cuya superficie encaja con la de la oferta.

    Si alguna de las dos superficies falta, basta la cercanía.
    """
    row = conn.execute(
        """
        SELECT id FROM properties
        WHERE location IS NOT NULL
          AND ST_DWithin(location, ST_SetSRID(ST_Point(%s, %s), 4326)::geography, %s)
          AND (%s::numeric IS NULL OR built_area_m2 IS NULL
               OR abs(built_area_m2 - %s::numeric) <= %s::numeric * %s::numeric)
        ORDER BY location <-> ST_SetSRID(ST_Point(%s, %s), 4326)::geography
        LIMIT 1
        """,
        (lon, lat, meters, built_area_m2, built_area_m2, area_tolerance, built_area_m2,
         lon, lat),
    ).fetchone()
    return row[0] if row else None


def create_property(
    conn: psycopg.Connection,
    *,
    lon: float,
    lat: float,
    cadastral_ref: str | None,
    address: str | None,
    built_area_m2: Decimal | None,
    municipality: str | None,
    section: tuple[str, int] | None,
) -> UUID:
    row = conn.execute(
        """
        INSERT INTO properties (cadastral_ref, address, location, built_area_m2, municipality,
                                section_code, section_vintage)
        VALUES (%s, %s, ST_SetSRID(ST_Point(%s, %s), 4326)::geography, %s, %s, %s, %s)
        RETURNING id
        """,
        (cadastral_ref, address, lon, lat, built_area_m2, municipality,
         section[0] if section else None, section[1] if section else None),
    ).fetchone()
    if row is None:
        raise RuntimeError("La inserción del inmueble no devolvió fila")
    return row[0]


@dataclass(frozen=True)
class PendingAnnouncement:
    id: UUID
    external_id: str
    title: str | None
    url: str | None
    published_on: date | None
    raw: dict[str, Any]
    source_id: str | None


def pending_announcements(
    conn: psycopg.Connection, channel: str, limit: int
) -> list[PendingAnnouncement]:
    rows = conn.execute(
        """
        SELECT id, external_id, title, url, published_on, raw, source_id FROM offers
        WHERE channel = %s AND kind = 'anuncio' AND extraction_status = 'pendiente'
        ORDER BY published_on, external_id LIMIT %s
        """,
        (channel, limit),
    ).fetchall()
    return [PendingAnnouncement(*r) for r in rows]


def mark_extracted(conn: psycopg.Connection, offer_id: UUID, extracted: dict[str, Any]) -> None:
    conn.execute(
        "UPDATE offers SET extraction_status = 'extraida', extracted = %s WHERE id = %s",
        (Jsonb(extracted), offer_id),
    )


# --- Ofertas privadas: enlaces pegados por el usuario (F4.1, ADR-0015) --------------------------


@dataclass(frozen=True)
class PrivateOffer:
    id: UUID
    url: str | None
    title: str | None
    extraction_status: str
    extracted: dict[str, Any] | None
    raw: dict[str, Any]
    asking_price: Decimal | None
    built_area_m2: Decimal | None
    address: str | None
    cadastral_ref: str | None
    property_id: UUID | None
    location_source: str | None
    section_code: str | None
    municipality: str | None
    first_seen: datetime


_PRIVATE = """
    SELECT o.id, o.url, o.title, o.extraction_status, o.extracted, o.raw, o.asking_price,
           o.built_area_m2, o.address, o.cadastral_ref, o.property_id, o.location_source,
           p.section_code,
           p.municipality, o.first_seen
    FROM offers o LEFT JOIN properties p ON p.id = o.property_id
"""


def get_private_offer(
    conn: psycopg.Connection, offer_id: UUID, org_id: UUID
) -> PrivateOffer | None:
    row = conn.execute(_PRIVATE + " WHERE o.id = %s AND o.org_id = %s",
                       (offer_id, org_id)).fetchone()
    return PrivateOffer(*row) if row else None


def list_private_offers(
    conn: psycopg.Connection, org_id: UUID, limit: int = 50
) -> list[PrivateOffer]:
    rows = conn.execute(_PRIVATE + " WHERE o.org_id = %s ORDER BY o.first_seen DESC LIMIT %s",
                        (org_id, limit)).fetchall()
    return [PrivateOffer(*r) for r in rows]


def offer_to_extract(
    conn: psycopg.Connection, offer_id: UUID
) -> tuple[str, dict[str, Any]] | None:
    """Estado y lo recibido de una oferta, para el trabajo de extracción (sin organización)."""
    row = conn.execute("SELECT extraction_status, raw FROM offers WHERE id = %s",
                       (offer_id,)).fetchone()
    return (row[0], row[1]) if row else None


def confirm_offer(
    conn: psycopg.Connection,
    offer_id: UUID,
    org_id: UUID,
    *,
    asking_price: Decimal | None,
    built_area_m2: Decimal | None,
    address: str | None,
    cadastral_ref: str | None,
    extracted: dict[str, Any],
) -> bool:
    row = conn.execute(
        """
        UPDATE offers SET extraction_status = 'confirmada', asking_price = %s,
                          built_area_m2 = %s, address = %s, cadastral_ref = %s, extracted = %s
        WHERE id = %s AND org_id = %s
          AND extraction_status IN ('pendiente', 'extraida', 'confirmada')
        RETURNING id
        """,
        (asking_price, built_area_m2, address, cadastral_ref, Jsonb(extracted), offer_id,
         org_id),
    ).fetchone()
    return row is not None
