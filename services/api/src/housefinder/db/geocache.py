"""Caché de geocodificación (ADR-0009). Guarda el resultado, nunca quién lo pidió."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import psycopg


@dataclass(frozen=True)
class CachedGeocode:
    lon: float
    lat: float
    match_type: str
    matched: str
    municipality: str | None
    cadastral_ref: str | None


def get_cached(
    conn: psycopg.Connection, query: str, max_age: timedelta
) -> CachedGeocode | None:
    row = conn.execute(
        """
        SELECT lon, lat, match_type, matched, municipality, cadastral_ref FROM geocode_cache
        WHERE query = %s AND fetched_at > now() - %s
        """,
        (query, max_age),
    ).fetchone()
    return CachedGeocode(*row) if row else None


def put_cached(
    conn: psycopg.Connection, query: str, result: CachedGeocode, source_id: str
) -> None:
    conn.execute(
        """
        INSERT INTO geocode_cache
            (query, lon, lat, match_type, matched, municipality, cadastral_ref, source_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (query) DO UPDATE SET
            lon = EXCLUDED.lon, lat = EXCLUDED.lat, match_type = EXCLUDED.match_type,
            matched = EXCLUDED.matched, municipality = EXCLUDED.municipality,
            cadastral_ref = EXCLUDED.cadastral_ref, source_id = EXCLUDED.source_id,
            fetched_at = now()
        """,
        (query, result.lon, result.lat, result.match_type, result.matched,
         result.municipality, result.cadastral_ref, source_id),
    )
