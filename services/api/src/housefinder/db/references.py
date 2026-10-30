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


# --- Lecturas para el modelo de valoración ------------------------------------------------------


@dataclass(frozen=True)
class RentRow:
    level: str
    code: str
    year: int
    n: int | None
    p25: Decimal
    median: Decimal
    p75: Decimal


def rent_stats(
    conn: psycopg.Connection, level: str, code: str, typology: str, year: int | None = None,
    source_id: str = "serpavi",
) -> RentRow | None:
    """Renta €/m² mes de un territorio: el año pedido o, sin año, el último con mediana."""
    if year is None:
        row = conn.execute(
            """
            SELECT max(year) FROM market_references
            WHERE source_id = %s AND level = %s AND code = %s AND typology = %s
              AND measure = 'renta_m2_mes' AND stat = 'mediana'
            """,
            (source_id, level, code, typology),
        ).fetchone()
        if row is None or row[0] is None:
            return None
        year = int(row[0])
    values = dict(conn.execute(
        """
        SELECT measure || ':' || stat, value FROM market_references
        WHERE source_id = %s AND level = %s AND code = %s AND typology = %s AND year = %s
          AND quarter = 0 AND measure IN ('renta_m2_mes', 'alquileres')
        """,
        (source_id, level, code, typology, year),
    ).fetchall())
    needed = ("renta_m2_mes:p25", "renta_m2_mes:mediana", "renta_m2_mes:p75")
    if not all(key in values for key in needed):
        return None
    count = values.get("alquileres:n")
    return RentRow(level, code, year, int(count) if count is not None else None,
                   values[needed[0]], values[needed[1]], values[needed[2]])


def reference_value(
    conn: psycopg.Connection, source_id: str, level: str, code: str, measure: str, year: int,
    typology: str = "todas", stat: str = "valor",
) -> Decimal | None:
    row = conn.execute(
        """
        SELECT value FROM market_references
        WHERE source_id = %s AND level = %s AND code = %s AND measure = %s AND year = %s
          AND quarter = 0 AND typology = %s AND stat = %s
        """,
        (source_id, level, code, measure, year, typology, stat),
    ).fetchone()
    return row[0] if row else None


@dataclass(frozen=True)
class IndexPoint:
    year: int
    quarter: int
    value: Decimal


def latest_index(
    conn: psycopg.Connection, source_id: str, code: str, typology: str
) -> IndexPoint | None:
    row = conn.execute(
        """
        SELECT year, quarter, value FROM market_references
        WHERE source_id = %s AND level = 'comunidad' AND code = %s AND typology = %s
          AND stat = 'indice'
        ORDER BY year DESC, quarter DESC LIMIT 1
        """,
        (source_id, code, typology),
    ).fetchone()
    return IndexPoint(*row) if row else None


def annual_index(
    conn: psycopg.Connection, source_id: str, code: str, typology: str, year: int
) -> Decimal | None:
    """Media de los cuatro trimestres de un año; None si falta alguno."""
    row = conn.execute(
        """
        SELECT count(*), avg(value) FROM market_references
        WHERE source_id = %s AND level = 'comunidad' AND code = %s AND typology = %s
          AND stat = 'indice' AND year = %s AND quarter BETWEEN 1 AND 4
        """,
        (source_id, code, typology, year),
    ).fetchone()
    if row is None or row[0] != 4:
        return None
    return Decimal(row[1])


def rent_table(
    conn: psycopg.Connection, level: str, typology: str, code_prefix: str,
    source_id: str = "serpavi",
) -> dict[tuple[str, int], RentRow]:
    """Todas las rentas €/m² mes de un nivel con P25, mediana y P75, por (código, año)."""
    values: dict[tuple[str, int], dict[str, Decimal]] = {}
    for code, year, key, value in conn.execute(
        """
        SELECT code, year, measure || ':' || stat, value FROM market_references
        WHERE source_id = %s AND level = %s AND typology = %s AND code LIKE %s AND quarter = 0
          AND measure IN ('renta_m2_mes', 'alquileres')
        """,
        (source_id, level, typology, f"{code_prefix}%"),
    ):
        values.setdefault((code, year), {})[key] = value
    table = {}
    for (code, year), v in values.items():
        if all(k in v for k in ("renta_m2_mes:p25", "renta_m2_mes:mediana", "renta_m2_mes:p75")):
            n = v.get("alquileres:n")
            table[(code, year)] = RentRow(level, code, year, int(n) if n is not None else None,
                                          v["renta_m2_mes:p25"], v["renta_m2_mes:mediana"],
                                          v["renta_m2_mes:p75"])
    return table


def series_values(
    conn: psycopg.Connection, source_id: str, level: str, measure: str, code_prefix: str,
    typology: str = "todas",
) -> dict[tuple[str, int, int], Decimal]:
    """Valores de una medida por (código, año, trimestre)."""
    return {(code, year, quarter): value for code, year, quarter, value in conn.execute(
        """
        SELECT code, year, quarter, value FROM market_references
        WHERE source_id = %s AND level = %s AND measure = %s AND typology = %s AND code LIKE %s
        """,
        (source_id, level, measure, typology, f"{code_prefix}%"),
    )}
