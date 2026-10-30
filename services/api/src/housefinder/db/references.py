"""SQL de las referencias públicas de alquiler y de precio (G6, ADR-0018)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

import psycopg

from housefinder.db.sections import SourceRecord, upsert_source


@dataclass(frozen=True)
class ReferenceRow:
    level: str  # 'seccion', 'distrito', 'municipio', 'provincia', 'comunidad'
    code: str
    vintage: int | None
    year: int
    quarter: int  # 0: dato anual
    measure: str
    typology: str
    stat: str
    value: Decimal
    unit: str


COLUMNS = ("source_id", "level", "code", "vintage", "year", "quarter", "measure", "typology",
           "stat", "value", "unit")


def replace_references(
    conn: psycopg.Connection, source: SourceRecord, rows: Iterable[ReferenceRow]
) -> int:
    """Sustituye todas las filas de la fuente por `rows`, en la transacción de `conn`.

    Una carga trae la serie entera (el SERPAVI revisa años anteriores): se borra lo de la fuente
    y se copia lo nuevo, en lugar de mezclar versiones.
    """
    upsert_source(conn, source)
    conn.execute("DELETE FROM market_references WHERE source_id = %s", (source.id,))
    count = 0
    with conn.cursor().copy(
        f"COPY market_references ({', '.join(COLUMNS)}) FROM STDIN"
    ) as copy:
        for r in rows:
            copy.write_row((source.id, r.level, r.code, r.vintage, r.year, r.quarter, r.measure,
                            r.typology, r.stat, r.value, r.unit))
            count += 1
    return count


def load_references(
    conninfo: str, source: SourceRecord, rows: list[ReferenceRow], sections: set[str],
    vintage: int,
) -> tuple[int, set[str]]:
    """Carga la fuente en una transacción; devuelve cuántas filas y qué secciones no están en
    la cartografía `vintage` cargada (se cargan igual: el aviso es para cargarla)."""
    with psycopg.connect(conninfo) as conn, conn.transaction():
        loaded = replace_references(conn, source, rows)
        known = {r[0] for r in conn.execute(
            "SELECT code FROM census_sections WHERE vintage = %s AND code = ANY(%s)",
            (vintage, list(sections))).fetchall()}
    return loaded, sections - known
