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
        """
        UPDATE offers SET property_id = %s, location_source = %s, location_issue = NULL,
                          location_retry = false
        WHERE id = %s
        """,
        (property_id, location_source, offer_id),
    )


def mark_unlocated(conn: psycopg.Connection, offer_id: UUID, issue: str, retry: bool) -> None:
    """Por qué la oferta se quedó sin ubicar y si merece otro intento (ADR-0031)."""
    conn.execute("UPDATE offers SET location_issue = %s, location_retry = %s WHERE id = %s",
                 (issue, retry, offer_id))


@dataclass(frozen=True)
class LotToRelocate:
    id: UUID
    external_id: str
    url: str | None
    title: str | None
    published_on: date | None
    address: str | None
    cadastral_ref: str | None
    built_area_m2: Decimal | None
    extracted: dict[str, Any]


def lots_to_relocate(conn: psycopg.Connection, channel: str) -> list[LotToRelocate]:
    """Lotes sin ubicar que merecen otro intento (ADR-0031)."""
    rows = conn.execute(
        """
        SELECT id, external_id, url, title, published_on, address, cadastral_ref, built_area_m2,
               coalesce(extracted, '{}'::jsonb)
        FROM offers
        WHERE channel = %s AND kind = 'lote' AND location_retry AND property_id IS NULL
        ORDER BY external_id
        """,
        (channel,),
    ).fetchall()
    return [LotToRelocate(*r) for r in rows]


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


def rss_dates(conn: psycopg.Connection, channel: str) -> dict[str, str]:
    """Fecha de publicación del RSS de cada anuncio guardado de un canal (ADR-0037): si no cambia,
    no se vuelve a descargar."""
    rows = conn.execute(
        """
        SELECT external_id, raw->'rss'->>'pubDate' FROM offers
        WHERE channel = %s AND kind = 'anuncio' AND raw->'rss'->>'pubDate' IS NOT NULL
        """,
        (channel,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def pending_announcements(
    conn: psycopg.Connection, channel: str, limit: int, only: list[str] | None = None
) -> list[PendingAnnouncement]:
    """Anuncios pendientes de extraer; con `only`, solo esos identificadores."""
    rows = conn.execute(
        """
        SELECT id, external_id, title, url, published_on, raw, source_id FROM offers
        WHERE channel = %s AND kind = 'anuncio' AND extraction_status = 'pendiente'
          AND (%s::text[] IS NULL OR external_id = ANY(%s::text[]))
        ORDER BY published_on, external_id LIMIT %s
        """,
        (channel, only, only, limit),
    ).fetchall()
    return [PendingAnnouncement(*r) for r in rows]


def with_proposals(
    conn: psycopg.Connection, channel: str, only: list[str] | None = None
) -> list[tuple[PendingAnnouncement, dict[str, Any]]]:
    """Anuncios ya extraídos con lo que propuso el modelo guardado, para volver a comprobarlo sin
    el LLM (ADR-0033)."""
    rows = conn.execute(
        """
        SELECT id, external_id, title, url, published_on, raw, source_id, extracted->'proposed'
        FROM offers
        WHERE channel = %s AND kind = 'anuncio' AND extraction_status = 'extraida'
          AND jsonb_typeof(extracted->'proposed') = 'object'
          AND (%s::text[] IS NULL OR external_id = ANY(%s::text[]))
        ORDER BY published_on, external_id
        """,
        (channel, only, only),
    ).fetchall()
    return [(PendingAnnouncement(*r[:7]), r[7]) for r in rows]


def refresh_lot(conn: psycopg.Connection, offer_id: UUID, lot: OfferRow) -> None:
    """Lo que da una extracción nueva del anuncio, si el lote no está confirmado (ADR-0033). Si
    cambia lo que lo ubica, o si estaba retirado, se desenlaza para volver a ubicarlo."""
    conn.execute(
        """
        UPDATE offers SET
            title = %(title)s, auction_min_bid = %(bid)s, deposit_required = %(deposit)s,
            built_area_m2 = %(area)s, extracted = %(extracted)s, extraction_status = 'extraida',
            address = %(address)s, cadastral_ref = %(ref)s,
            property_id = CASE WHEN moved THEN NULL ELSE property_id END,
            location_source = CASE WHEN moved THEN NULL ELSE location_source END,
            location_issue = CASE WHEN moved THEN NULL ELSE location_issue END,
            location_retry = CASE WHEN moved THEN false ELSE location_retry END
        FROM (SELECT address IS DISTINCT FROM %(address)s
                     OR cadastral_ref IS DISTINCT FROM %(ref)s
                     OR extraction_status = 'retirada' AS moved
              FROM offers WHERE id = %(id)s) AS change
        WHERE id = %(id)s AND extraction_status IN ('extraida', 'retirada')
        """,
        {"title": lot.title, "bid": lot.auction_min_bid, "deposit": lot.deposit_required,
         "area": lot.built_area_m2, "address": lot.address, "ref": lot.cadastral_ref,
         "extracted": Jsonb(lot.extracted) if lot.extracted is not None else None,
         "id": offer_id},
    )


def retire_lots(conn: psycopg.Connection, announcement_id: UUID, kept: list[str]) -> int:
    """Retira los lotes sin confirmar que la extracción nueva del anuncio ya no encuentra."""
    rows = conn.execute(
        """
        UPDATE offers SET extraction_status = 'retirada', property_id = NULL,
                          location_source = NULL, location_retry = false,
                          location_issue = 'una extracción nueva del anuncio ya no lo encuentra'
        WHERE parent_id = %s AND kind = 'lote' AND extraction_status = 'extraida'
          AND NOT (external_id = ANY(%s::text[]))
        RETURNING id
        """,
        (announcement_id, kept),
    ).fetchall()
    return len(rows)


def stored_listing(conn: psycopg.Connection, channel: str,
                   external_id: str) -> tuple[str | None, str | None, str | None] | None:
    """Referencia catastral y coordenada de lo último recibido de un anuncio de feed (ADR-0038),
    para saber si hay que volver a ubicarlo."""
    row = conn.execute(
        "SELECT cadastral_ref, raw->>'latitude', raw->>'longitude' FROM offers "
        "WHERE channel = %s AND external_id = %s",
        (channel, external_id),
    ).fetchone()
    return (row[0], row[1], row[2]) if row else None


def refresh_listing(conn: psycopg.Connection, offer_id: UUID, listing: OfferRow,
                    relocate: bool) -> None:
    """Pone al día un anuncio de feed que ya estaba (ADR-0038): precio, superficie, referencia,
    alcance y estado. Si estaba retirado vuelve; si se movió, se desliga para volver a ubicarlo."""
    conn.execute(
        """
        UPDATE offers SET
            asking_price = %(price)s, built_area_m2 = %(area)s, cadastral_ref = %(ref)s,
            published_on = %(published)s, extracted = %(extracted)s, org_id = %(org)s,
            extraction_status = %(status)s,
            property_id = CASE WHEN %(relocate)s OR extraction_status = 'retirada' THEN NULL
                               ELSE property_id END,
            location_source = CASE WHEN %(relocate)s OR extraction_status = 'retirada' THEN NULL
                                   ELSE location_source END,
            location_retry = CASE WHEN %(relocate)s OR extraction_status = 'retirada' THEN false
                                  ELSE location_retry END,
            location_issue = CASE WHEN %(relocate)s OR extraction_status = 'retirada' THEN NULL
                                  ELSE location_issue END
        WHERE id = %(id)s
        """,
        {"price": listing.asking_price, "area": listing.built_area_m2,
         "ref": listing.cadastral_ref, "published": listing.published_on,
         "extracted": Jsonb(listing.extracted) if listing.extracted is not None else None,
         "org": listing.org_id, "status": listing.extraction_status, "relocate": relocate,
         "id": offer_id},
    )


def retire_missing(conn: psycopg.Connection, channel: str, source_id: str,
                   kept: list[str]) -> int:
    """Retira los anuncios de un feed que ya no vienen en él: el feed es una foto completa."""
    rows = conn.execute(
        """
        UPDATE offers SET extraction_status = 'retirada', property_id = NULL,
                          location_source = NULL, location_retry = false,
                          location_issue = 'ya no está en el feed de la agencia'
        WHERE channel = %s AND source_id = %s AND kind = 'anuncio'
          AND extraction_status <> 'retirada' AND NOT (external_id = ANY(%s::text[]))
        RETURNING id
        """,
        (channel, source_id, kept),
    ).fetchall()
    return len(rows)


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
    lon: float | None = None  # punto del inmueble, si está ubicada
    lat: float | None = None


_PRIVATE = """
    SELECT o.id, o.url, o.title, o.extraction_status, o.extracted, o.raw, o.asking_price,
           o.built_area_m2, o.address, o.cadastral_ref, o.property_id, o.location_source,
           p.section_code, p.municipality, o.first_seen,
           ST_X(p.location::geometry), ST_Y(p.location::geometry)
    FROM offers o LEFT JOIN properties p ON p.id = o.property_id
"""


def get_private_offer(
    conn: psycopg.Connection, offer_id: UUID, org_id: UUID
) -> PrivateOffer | None:
    row = conn.execute(_PRIVATE + " WHERE o.id = %s AND o.org_id = %s AND o.kind = 'enlace'",
                       (offer_id, org_id)).fetchone()
    return PrivateOffer(*row) if row else None


def list_private_offers(
    conn: psycopg.Connection, org_id: UUID, limit: int = 50
) -> list[PrivateOffer]:
    # Solo los enlaces y textos pegados: la cartera de los feeds de agencias (también de la
    # organización, ADR-0038) va en su propia página.
    rows = conn.execute(_PRIVATE + " WHERE o.org_id = %s AND o.kind = 'enlace' "
                        "ORDER BY o.first_seen DESC LIMIT %s", (org_id, limit)).fetchall()
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
        WHERE id = %s AND org_id = %s AND kind = 'enlace'
          AND extraction_status IN ('pendiente', 'extraida', 'confirmada')
        RETURNING id
        """,
        (asking_price, built_area_m2, address, cadastral_ref, Jsonb(extracted), offer_id,
         org_id),
    ).fetchone()
    return row is not None


# --- Avisos de subastas judiciales del BOE (F4.3, ADR-0017) --------------------------------------


@dataclass(frozen=True)
class AuctionNoticeRow:
    portal_id: str
    portal_url: str | None
    title: str | None
    published_on: date | None
    court: str | None
    kind: str | None
    boe_url: str | None


def list_auction_notices(
    conn: psycopg.Connection, channel: str, limit: int = 50
) -> list[AuctionNoticeRow]:
    rows = conn.execute(
        """
        SELECT external_id, url, title, published_on, raw->'aviso'->>'court',
               raw->'aviso'->>'kind', raw->>'boe'
        FROM offers WHERE channel = %s AND org_id IS NULL
        ORDER BY published_on DESC NULLS LAST, external_id DESC LIMIT %s
        """,
        (channel, limit),
    ).fetchall()
    return [AuctionNoticeRow(*r) for r in rows]


# --- Correcciones del BOE (F4.4) -----------------------------------------------------------------


def link_corrections(conn: psycopg.Connection, channel: str) -> int:
    """Enlaza las correcciones sin enlazar con el anuncio que corrigen, si ya está guardado.

    Un anuncio guardado como pendiente antes de reconocerse como corrección deja de estarlo: no
    tiene lotes nuevos que extraer.
    """
    conn.execute(
        """
        UPDATE offers SET extraction_status = 'no_aplica'
        WHERE channel = %s AND raw ? 'corrige' AND extraction_status = 'pendiente'
        """,
        (channel,),
    )
    rows = conn.execute(
        """
        UPDATE offers c SET corrects_id = o.id
        FROM offers o
        WHERE c.channel = %s AND c.corrects_id IS NULL AND o.channel = c.channel
          AND o.external_id = c.raw->'corrige'->>'boe'
        RETURNING c.id
        """,
        (channel,),
    ).fetchall()
    return len(rows)


@dataclass(frozen=True)
class CorrectionRow:
    external_id: str
    url: str | None
    published_on: date | None
    title: str | None


def corrections_of(conn: psycopg.Connection, offer_id: UUID) -> list[CorrectionRow]:
    """Correcciones publicadas de un anuncio, de la más antigua a la más reciente."""
    rows = conn.execute(
        """
        SELECT external_id, url, published_on, title FROM offers
        WHERE corrects_id = %s ORDER BY published_on, external_id
        """,
        (offer_id,),
    ).fetchall()
    return [CorrectionRow(*r) for r in rows]


# --- Anuncios del BOE para la web (F4.4) --------------------------------------------------------


@dataclass(frozen=True)
class AnnouncementSummary:
    id: UUID
    external_id: str
    title: str | None
    published_on: date | None
    extraction_status: str
    lots: int
    located_lots: int
    corrections: int


def list_announcements(
    conn: psycopg.Connection, channel: str, limit: int = 100
) -> list[AnnouncementSummary]:
    """Anuncios del canal sin las correcciones, que van dentro del anuncio que corrigen."""
    rows = conn.execute(
        """
        SELECT a.id, a.external_id, a.title, a.published_on, a.extraction_status,
               (SELECT count(*) FROM offers l WHERE l.parent_id = a.id),
               (SELECT count(*) FROM offers l WHERE l.parent_id = a.id
                                               AND l.property_id IS NOT NULL),
               (SELECT count(*) FROM offers c WHERE c.corrects_id = a.id)
        FROM offers a
        WHERE a.channel = %s AND a.kind = 'anuncio' AND a.org_id IS NULL
          AND NOT (a.raw ? 'corrige')
        ORDER BY a.published_on DESC NULLS LAST, a.external_id DESC LIMIT %s
        """,
        (channel, limit),
    ).fetchall()
    return [AnnouncementSummary(*r) for r in rows]


@dataclass(frozen=True)
class AnnouncementDetail:
    id: UUID
    external_id: str
    title: str | None
    url: str | None
    published_on: date | None
    extraction_status: str
    paragraphs: list[str]
    corrects: str | None  # BOE-B-… del anuncio que corrige, si es una corrección


def get_announcement(
    conn: psycopg.Connection, channel: str, external_id: str
) -> AnnouncementDetail | None:
    row = conn.execute(
        """
        SELECT a.id, a.external_id, a.title, a.url, a.published_on, a.extraction_status,
               a.raw->'texto', o.external_id
        FROM offers a LEFT JOIN offers o ON o.id = a.corrects_id
        WHERE a.channel = %s AND a.external_id = %s AND a.kind = 'anuncio'
          AND a.org_id IS NULL
        """,
        (channel, external_id),
    ).fetchone()
    if row is None:
        return None
    return AnnouncementDetail(*row[:6], list(row[6] or []), row[7])


@dataclass(frozen=True)
class LotRow:
    id: UUID
    external_id: str
    title: str | None
    extraction_status: str
    extracted: dict[str, Any] | None
    location_source: str | None
    section_code: str | None
    municipality: str | None


def lots_of(conn: psycopg.Connection, announcement_id: UUID) -> list[LotRow]:
    rows = conn.execute(
        """
        SELECT l.id, l.external_id, l.title, l.extraction_status, l.extracted,
               l.location_source, p.section_code, p.municipality
        FROM offers l LEFT JOIN properties p ON p.id = l.property_id
        WHERE l.parent_id = %s AND l.extraction_status <> 'retirada' ORDER BY l.external_id
        """,
        (announcement_id,),
    ).fetchall()
    return [LotRow(*r) for r in rows]


@dataclass(frozen=True)
class SearchCandidate:
    """Una oferta que la búsqueda inversa puede intentar puntuar (F6.5)."""

    offer_id: UUID
    kind: str  # 'enlace' (del usuario) o 'lote' (del BOE)
    title: str | None
    url: str | None
    asking_price: Decimal | None
    auction_min_bid: Decimal | None
    built_area_m2: Decimal | None
    lon: float
    lat: float
    section_code: str
    extracted: dict[str, Any] | None
    deposit_required: Decimal | None = None  # depósito para pujar, si el anuncio lo dice


_CANDIDATES = """
    SELECT o.id, o.kind, o.title, o.url, o.asking_price, o.auction_min_bid,
           coalesce(o.built_area_m2, p.built_area_m2),
           ST_X(p.location::geometry), ST_Y(p.location::geometry), p.section_code, o.extracted,
           o.deposit_required
    FROM offers o JOIN properties p ON p.id = o.property_id
    WHERE p.location IS NOT NULL AND p.section_code IS NOT NULL
      AND ((o.org_id = %(org)s AND o.kind = 'enlace' AND o.extraction_status = 'confirmada')
           OR (o.org_id IS NULL AND o.kind = 'lote' AND o.corrects_id IS NULL)
           OR (o.channel = 'feed_agencia' AND o.kind = 'anuncio'
               AND o.extraction_status = 'no_aplica'
               AND (o.org_id IS NULL OR o.org_id = %(org)s)))
"""


def search_candidates(conn: psycopg.Connection, org_id: UUID) -> list[SearchCandidate]:
    """Ofertas ubicadas con sección: las confirmadas del usuario, los lotes del BOE (públicos) y
    los anuncios de los feeds de agencias que puede ver (ADR-0038). Lo que no se puede puntuar
    (otro tipo, sin precio) lo decide quien llama, con su motivo."""
    rows = conn.execute(_CANDIDATES + " ORDER BY o.first_seen", {"org": org_id}).fetchall()
    return [SearchCandidate(*r) for r in rows]


def search_candidate(conn: psycopg.Connection, org_id: UUID,
                     offer_id: UUID) -> SearchCandidate | None:
    """Una oferta de la búsqueda del usuario (para su plan completo)."""
    row = conn.execute(_CANDIDATES + " AND o.id = %(offer)s",
                       {"org": org_id, "offer": offer_id}).fetchone()
    return SearchCandidate(*row) if row else None


def searchable_offer(conn: psycopg.Connection, offer_id: UUID, org_id: UUID) -> bool:
    """Si la búsqueda del usuario puede ver la oferta: suya y confirmada, un lote del BOE o un
    anuncio de un feed de agencia que puede ver."""
    row = conn.execute(
        """
        SELECT 1 FROM offers
        WHERE id = %(offer)s
          AND ((org_id = %(org)s AND kind = 'enlace' AND extraction_status = 'confirmada')
               OR (org_id IS NULL AND kind = 'lote')
               OR (channel = 'feed_agencia' AND kind = 'anuncio'
                   AND extraction_status = 'no_aplica'
                   AND (org_id IS NULL OR org_id = %(org)s)))
        """,
        {"offer": offer_id, "org": org_id},
    ).fetchone()
    return row is not None


def rent_expectations(conn: psycopg.Connection, org_id: UUID) -> dict[UUID, dict[str, Decimal]]:
    """Lo que el usuario espera sacar de cada oferta por tipo de alquiler (ADR-0024)."""
    rows = conn.execute(
        "SELECT offer_id, rental_type, monthly_income FROM offer_rent_expectations "
        "WHERE org_id = %s",
        (org_id,),
    ).fetchall()
    result: dict[UUID, dict[str, Decimal]] = {}
    for offer_id, rental_type, income in rows:
        result.setdefault(offer_id, {})[rental_type] = income
    return result


def set_rent_expectation(conn: psycopg.Connection, org_id: UUID, offer_id: UUID,
                         rental_type: str, monthly_income: Decimal | None) -> None:
    """Guarda la renta esperada de un tipo; None la borra."""
    if monthly_income is None:
        conn.execute(
            "DELETE FROM offer_rent_expectations "
            "WHERE org_id = %s AND offer_id = %s AND rental_type = %s",
            (org_id, offer_id, rental_type),
        )
        return
    conn.execute(
        """
        INSERT INTO offer_rent_expectations (org_id, offer_id, rental_type, monthly_income)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (org_id, offer_id, rental_type)
        DO UPDATE SET monthly_income = EXCLUDED.monthly_income, updated_at = now()
        """,
        (org_id, offer_id, rental_type, monthly_income),
    )


# --- Ventas directas del Patrimonio del Estado para la web (ADR-0037) ---------------------------


@dataclass(frozen=True)
class DirectSaleSummary:
    external_id: str
    title: str | None
    published_on: date | None
    extraction_status: str
    lots: int
    located_lots: int
    delegation: str | None
    deadline: str | None  # «Fecha límite presentación solicitudes», tal como viene: 23/03/2027
    price: str | None  # el de la ficha, si lo trae: 1.344,49


def list_direct_sales(conn: psycopg.Connection, channel: str,
                      limit: int = 100) -> list[DirectSaleSummary]:
    rows = conn.execute(
        """
        SELECT a.external_id, a.title, a.published_on, a.extraction_status,
               (SELECT count(*) FROM offers l WHERE l.parent_id = a.id
                                               AND l.extraction_status <> 'retirada'),
               (SELECT count(*) FROM offers l WHERE l.parent_id = a.id
                                               AND l.property_id IS NOT NULL),
               a.raw->'ficha'->>'Delegación',
               a.raw->'ficha'->>'Fecha límite presentación solicitudes',
               a.raw->'ficha'->>'Precio'
        FROM offers a
        WHERE a.channel = %s AND a.kind = 'anuncio' AND a.org_id IS NULL
        ORDER BY a.published_on DESC NULLS LAST, a.external_id DESC LIMIT %s
        """,
        (channel, limit),
    ).fetchall()
    return [DirectSaleSummary(*r) for r in rows]


# --- Cartera de los feeds de agencias para la web (ADR-0038) ------------------------------------


@dataclass(frozen=True)
class FeedListing:
    id: UUID
    title: str | None
    url: str | None
    asking_price: Decimal | None
    built_area_m2: Decimal | None
    municipality: str | None
    province: str | None
    property_type: str | None
    agency: str | None  # nombre de la fuente: «Feed de …»
    public: bool  # la ven todos los usuarios (alcance «todos»)
    located: bool
    section_code: str | None


def list_feed_listings(conn: psycopg.Connection, org_id: UUID,
                       limit: int = 500) -> list[FeedListing]:
    """Anuncios vigentes de los feeds de agencias que la organización puede ver: los suyos y los
    que una agencia cedió a todos."""
    rows = conn.execute(
        """
        SELECT o.id, o.title, o.url, o.asking_price, o.built_area_m2,
               o.raw->>'town', o.raw->>'province', o.extracted->>'property_type', s.name,
               o.org_id IS NULL, o.property_id IS NOT NULL, p.section_code
        FROM offers o
        LEFT JOIN sources s ON s.id = o.source_id
        LEFT JOIN properties p ON p.id = o.property_id
        WHERE o.channel = 'feed_agencia' AND o.kind = 'anuncio'
          AND o.extraction_status = 'no_aplica' AND (o.org_id IS NULL OR o.org_id = %s)
        ORDER BY o.published_on DESC NULLS LAST, o.title LIMIT %s
        """,
        (org_id, limit),
    ).fetchall()
    return [FeedListing(*r) for r in rows]
