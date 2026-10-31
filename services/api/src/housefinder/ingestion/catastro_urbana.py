"""Estadísticas catastrales urbanas por municipio (ADR-0022).

Fichero anual `URBANA{año}.xls` de la Dirección General del Catastro: por municipio, inmuebles y
valor catastral residenciales, y valor catastral total con su reparto en suelo y construcción
(todos los usos). Sirve para estimar el valor catastral de una vivienda (media residencial del
municipio) y la parte de construcción del precio, base de la amortización.

Condiciones: «Se autoriza la reproducción total o parcial de los contenidos del Portal, siempre
que se cite expresamente su origen» (https://www.catastro.hacienda.gob.es/es-ES/avisolegal.html).
El Catastro no publica la superficie construida residencial por municipio, y oculta los valores
con menos de tres inmuebles.

Uso: `python -m housefinder.ingestion.catastro_urbana --year 2026 --province 28`.
"""

from __future__ import annotations

import argparse
import hashlib
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from housefinder.db.references import ReferenceRow
from housefinder.db.sections import SourceRecord
from housefinder.ingestion.ine_sections import USER_AGENT

URL = "https://www.catastro.hacienda.gob.es/documentos/estadisticas/URBANA{year}.xls"
PAGE = "https://www.catastro.hacienda.gob.es/es-ES/estadisticas_7.html"
LICENSE = "Dirección General del Catastro, citando expresamente su origen"
# Columna del fichero → (medida, estadístico, unidad)
COLUMNS = {
    "UU_RES": ("inmuebles_residenciales", "n", "inmuebles"),
    "V_CAT_RES": ("valor_catastral_residencial", "valor", "EUR"),
    "V_CATASTRAL": ("valor_catastral", "valor", "EUR"),
    "V_CONSTRUCCION": ("valor_construccion", "valor", "EUR"),
    "V_SUELO": ("valor_suelo", "valor", "EUR"),
}


def parse(records: Iterable[Mapping[str, Any]], province: str | None) -> list[ReferenceRow]:
    """Filas del Excel (cabecera → valor) a referencias por municipio."""
    rows = []
    for record in records:
        code = str(record.get("COD_INE_MUNI", "")).strip()
        if len(code) != 5 or (province and not code.startswith(province)):
            continue
        year = int(str(record["AREF"]).strip())
        for column, (measure, stat, unit) in COLUMNS.items():
            value = record.get(column)
            if value in ("", None):
                continue  # oculto por secreto estadístico (menos de tres inmuebles)
            rows.append(ReferenceRow(level="municipio", code=code, vintage=None, year=year,
                                     quarter=0, measure=measure, typology="todas", stat=stat,
                                     value=Decimal(str(value)), unit=unit))
    return rows


def read_xls(content: bytes) -> list[dict[str, Any]]:
    import xlrd  # solo aquí: Excel antiguo del Catastro

    sheet = xlrd.open_workbook(file_contents=content, logfile=_Silent()).sheet_by_index(0)
    head = [str(sheet.cell_value(0, c)) for c in range(sheet.ncols)]
    return [dict(zip(head, (sheet.cell_value(r, c) for c in range(sheet.ncols)), strict=True))
            for r in range(1, sheet.nrows)]


class _Silent:
    """xlrd avisa de que el fichero del Catastro no cuadra con el tamaño de sector: es inocuo."""

    def write(self, _text: str) -> None:
        pass


def source_record(year: int, content: bytes, rows: list[ReferenceRow]) -> SourceRecord:
    return SourceRecord(
        id=f"catastro-urbana-{year}",
        name=f"Estadísticas catastrales urbanas por municipio, {year} (Dirección General del "
             "Catastro)",
        url=PAGE, license=LICENSE, fetched_at=datetime.now(UTC),
        notes=(f"{len(rows)} valores; sha256 {hashlib.sha256(content).hexdigest()}. Fichero: "
               f"{URL.format(year=year)}"))


def load(year: int, province: str | None, conninfo: str,
         client: httpx.Client | None = None) -> dict[str, Any]:
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        response = (client or own).get(URL.format(year=year), timeout=120)
        response.raise_for_status()
    rows = parse(read_xls(response.content), province)
    if not rows:
        raise LookupError(f"El fichero del Catastro {year} no trae municipios de {province}")
    loaded, _ = load_references(conninfo, source_record(year, response.content, rows), rows,
                                set(), 0)
    return {"loaded": loaded, "municipalities": len({r.code for r in rows})}


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--province", help="código INE de la provincia (28); sin él, España")
    args = parser.parse_args()
    result = load(args.year, args.province, database_url())
    print(f"Catastro {args.year}: {result['loaded']} valores de {result['municipalities']} "
          "municipios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
