"""Repositorio de fuentes y secciones censales (F3.2, F3.7).

SQL explícito con psycopg 3 (ADR-0008). Las geometrías entran como GeoJSON en
longitud/latitud (EPSG:4326) y se guardan como MultiPolygon válidos.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

import psycopg


@dataclass(frozen=True)
class SourceRecord:
    """Una carga de datos: de dónde sale, con qué licencia y cuándo se descargó."""

    id: str  # 'ine-secciones-2025-28'
    name: str
    url: str
    license: str
    fetched_at: datetime
    notes: str = ""


@dataclass(frozen=True)
class SectionRow:
    code: str  # código INE de 10 dígitos: provincia, municipio, distrito y sección
    municipality: str  # código INE del municipio (5 dígitos)
    geojson: str  # geometría en GeoJSON, longitud/latitud


@dataclass(frozen=True)
class SectionHit:
    code: str
    municipality: str
    vintage: int


def upsert_source(conn: psycopg.Connection, source: SourceRecord) -> None:
    conn.execute(
        """
        INSERT INTO sources (id, name, url, license, fetched_at, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name, url = EXCLUDED.url, license = EXCLUDED.license,
            fetched_at = EXCLUDED.fetched_at, notes = EXCLUDED.notes
        """,
        (source.id, source.name, source.url, source.license, source.fetched_at, source.notes),
    )


def upsert_sections(
    conn: psycopg.Connection, rows: Iterable[SectionRow], vintage: int, source_id: str
) -> int:
    """Inserta o actualiza las secciones de una cartografía. Repetir la carga no duplica."""
    params = [(r.code, r.municipality, r.geojson, vintage, source_id) for r in rows]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO census_sections (code, municipality, geom, vintage, source_id)
            VALUES (%s, %s,
                    ST_Multi(ST_CollectionExtract(
                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)),
                    %s, %s)
            ON CONFLICT (code, vintage) DO UPDATE SET
                municipality = EXCLUDED.municipality, geom = EXCLUDED.geom,
                source_id = EXCLUDED.source_id
            """,
            params,
        )
    return len(params)


def count_sections(conn: psycopg.Connection, vintage: int, prefix: str = "") -> int:
    row = conn.execute(
        "SELECT count(*) FROM census_sections WHERE vintage = %s AND code LIKE %s",
        (vintage, f"{prefix}%"),
    ).fetchone()
    return int(row[0]) if row else 0


def section_at(
    conn: psycopg.Connection, lon: float, lat: float, vintage: int
) -> SectionHit | None:
    """Sección de una cartografía que contiene el punto (longitud, latitud)."""
    row = conn.execute(
        """
        SELECT code, municipality, vintage FROM census_sections
        WHERE vintage = %s AND ST_Covers(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
        ORDER BY code LIMIT 1
        """,
        (vintage, lon, lat),
    ).fetchone()
    return SectionHit(*row) if row else None


def load_sections(
    conninfo: str, source: SourceRecord, rows: list[SectionRow], vintage: int, prefix: str
) -> int:
    """Registra la fuente y carga las secciones en una sola transacción.

    Devuelve cuántas secciones de esa cartografía y prefijo hay en la base después.
    """
    with psycopg.connect(conninfo) as conn, conn.transaction():
        upsert_source(conn, source)
        upsert_sections(conn, rows, vintage, source.id)
        return count_sections(conn, vintage, prefix)
