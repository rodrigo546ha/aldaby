"""Repositorio de indicadores por sección censal (F3.3).

Cada valor va con su sección y la cartografía en la que está definida: el ADRH de un año t
se cruza con el seccionado a 1 de enero de t+1 (docs/research/f3-3-atlas-renta.md).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

import psycopg

from housefinder.db.sections import SourceRecord, upsert_source


@dataclass(frozen=True)
class IndicatorRow:
    section_code: str
    section_vintage: int
    indicator: str  # clave estable: 'renta_neta_media_persona'
    year: int  # año al que se refiere el dato
    value: Decimal
    unit: str  # 'EUR', 'años', 'personas', 'ratio'


def existing_sections(conn: psycopg.Connection, vintages: Iterable[int]) -> set[tuple[str, int]]:
    rows = conn.execute(
        "SELECT code, vintage FROM census_sections WHERE vintage = ANY(%s)", (list(vintages),)
    ).fetchall()
    return {(code, vintage) for code, vintage in rows}


def upsert_indicators(
    conn: psycopg.Connection, rows: Iterable[IndicatorRow], source_id: str
) -> int:
    params = [
        (r.section_code, r.section_vintage, r.indicator, r.year, r.value, r.unit, source_id)
        for r in rows
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO section_indicators
                (section_code, section_vintage, indicator, year, value, unit, source_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (section_code, section_vintage, indicator, year) DO UPDATE SET
                value = EXCLUDED.value, unit = EXCLUDED.unit, source_id = EXCLUDED.source_id
            """,
            params,
        )
    return len(params)


@dataclass(frozen=True)
class LoadReport:
    loaded: int
    without_section: list[IndicatorRow]  # su sección no está en la cartografía cargada


def load_indicators(
    conninfo: str, source: SourceRecord, rows: list[IndicatorRow]
) -> LoadReport:
    """Registra la fuente y carga los indicadores cuya sección existe, en una transacción."""
    with psycopg.connect(conninfo) as conn, conn.transaction():
        known = existing_sections(conn, {r.section_vintage for r in rows})
        matched = [r for r in rows if (r.section_code, r.section_vintage) in known]
        missing = [r for r in rows if (r.section_code, r.section_vintage) not in known]
        upsert_source(conn, source)
        upsert_indicators(conn, matched, source.id)
        return LoadReport(len(matched), missing)


def indicators_for(
    conn: psycopg.Connection, code: str, vintage: int
) -> list[tuple[str, int, Decimal, str, str]]:
    """(indicador, año, valor, unidad, fuente) de una sección y cartografía."""
    return conn.execute(
        """
        SELECT indicator, year, value, unit, source_id FROM section_indicators
        WHERE section_code = %s AND section_vintage = %s
        ORDER BY indicator, year
        """,
        (code, vintage),
    ).fetchall()


def indicator_history(
    conn: psycopg.Connection, code: str, vintages: Iterable[int]
) -> list[IndicatorRow]:
    """Valores de una sección en las cartografías indicadas (cada año, con su seccionado)."""
    rows = conn.execute(
        """
        SELECT section_code, section_vintage, indicator, year, value, unit
        FROM section_indicators
        WHERE section_code = %s AND section_vintage = ANY(%s)
        ORDER BY indicator, year
        """,
        (code, list(vintages)),
    ).fetchall()
    return [IndicatorRow(*r) for r in rows]


def indicator_sources(
    conn: psycopg.Connection, code: str, vintages: Iterable[int]
) -> dict[tuple[str, int], str]:
    """Fuente de cada (indicador, año) de una sección."""
    rows = conn.execute(
        """
        SELECT indicator, year, source_id FROM section_indicators
        WHERE section_code = %s AND section_vintage = ANY(%s)
        """,
        (code, list(vintages)),
    ).fetchall()
    return {(i, int(y)): s for i, y, s in rows}
