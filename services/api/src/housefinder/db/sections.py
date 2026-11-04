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


def sources_by_id(conn: psycopg.Connection, ids: list[str]) -> dict[str, SourceRecord]:
    """Las fuentes de datos guardadas con esos identificadores (el anexo del PDF, ADR-0026)."""
    rows = conn.execute(
        "SELECT id, name, url, license, fetched_at, notes FROM sources WHERE id = ANY(%s)",
        (ids,),
    ).fetchall()
    return {r[0]: SourceRecord(r[0], r[1], r[2] or "", r[3] or "", r[4], r[5] or "")
            for r in rows}


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


def latest_vintage(conn: psycopg.Connection) -> int | None:
    row = conn.execute("SELECT max(vintage) FROM census_sections").fetchone()
    return int(row[0]) if row and row[0] is not None else None


def loaded_provinces(conn: psycopg.Connection, vintage: int) -> frozenset[str]:
    """Códigos INE de las provincias con secciones cargadas en la cartografía `vintage`."""
    rows = conn.execute(
        "SELECT DISTINCT left(code, 2) FROM census_sections WHERE vintage = %s", (vintage,)
    ).fetchall()
    return frozenset(r[0] for r in rows)


def section_source(conn: psycopg.Connection, code: str, vintage: int) -> str | None:
    row = conn.execute(
        "SELECT source_id FROM census_sections WHERE code = %s AND vintage = %s",
        (code, vintage),
    ).fetchone()
    return row[0] if row else None


def stable_vintages(
    conn: psycopg.Connection, code: str, vintage: int, tolerance: float
) -> set[int]:
    """Cartografías en las que la sección tiene el mismo código y (casi) el mismo polígono.

    «Casi»: el área de la diferencia simétrica no pasa de `tolerance` (tanto por uno) del área
    de la sección en `vintage`. Incluye la propia `vintage`.
    """
    rows = conn.execute(
        """
        SELECT o.vintage FROM census_sections c
        JOIN census_sections o ON o.code = c.code
        WHERE c.code = %s AND c.vintage = %s
          AND (o.vintage = c.vintage OR
               ST_Area(ST_SymDifference(c.geom, o.geom)::geography)
               <= %s * ST_Area(c.geom::geography))
        """,
        (code, vintage, tolerance),
    ).fetchall()
    return {int(r[0]) for r in rows}


def municipality_point(conn: psycopg.Connection, municipality: str,
                       vintage: int) -> tuple[float, float] | None:
    """Un punto dentro del municipio (código INE): el de la superficie de su sección más grande que
    contiene el centro de todas, o el centro si cae fuera (ADR-0054). None si no tiene secciones."""
    row = conn.execute(
        """
        WITH m AS (SELECT geom FROM census_sections WHERE municipality = %s AND vintage = %s),
             c AS (SELECT ST_Centroid(ST_Collect(geom)) AS p FROM m)
        SELECT ST_X(pt), ST_Y(pt) FROM (
            SELECT coalesce(
                (SELECT c.p FROM c, m WHERE ST_Covers(m.geom, c.p) LIMIT 1),
                (SELECT ST_PointOnSurface(geom) FROM m ORDER BY ST_Area(geom) DESC LIMIT 1)) AS pt
        ) x WHERE pt IS NOT NULL
        """,
        (municipality, vintage),
    ).fetchone()
    return (float(row[0]), float(row[1])) if row else None
