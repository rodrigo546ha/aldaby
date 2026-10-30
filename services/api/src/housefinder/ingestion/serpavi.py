"""SERPAVI: referencias de alquiler por sección censal, distrito y municipio (F5.2, ADR-0018).

Sistema Estatal de Referencia del Precio del Alquiler de Vivienda (Ministerio de Vivienda y Agenda
Urbana): explotación del IRPF (alquileres de vivienda habitual) con la superficie del Catastro.
Por territorio y año, para vivienda colectiva (VC) y unifamiliar (VU): número de viviendas
alquiladas y mediana, P25 y P75 de la renta por m² al mes, de la renta mensual y de la superficie.
Solo se publican los territorios con al menos 10 alquileres. Códigos del seccionado del Censo 2021.

Fichero: Excel 2011–2024 (67,8 MB), una hoja por nivel y una columna por medida y año
(`ALQM2_LV_M_VC_24`: renta €/m² mes, mediana, colectiva, 2024).

Reutilización (aviso legal del Ministerio): libre, también comercial, sin desnaturalizar el
contenido, citando la fuente y la fecha de la última actualización.

Uso: `python -m housefinder.ingestion.serpavi --province 28` con `DATABASE_URL`.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx

from housefinder.db.references import ReferenceRow
from housefinder.db.sections import SourceRecord
from housefinder.ingestion.xlsx import iter_rows

URL = ("https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/"
       "2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx")
PAGE = "https://www.mivau.gob.es/vivienda/alquila-bien-es-tu-derecho/serpavi"
LICENSE = ("Aviso legal del Ministerio de Vivienda y Agenda Urbana: reutilización libre, también "
           "comercial, citando la fuente y la fecha de la última actualización")
LICENSE_URL = "https://www.mivau.gob.es/ministerio/aviso-legal"
SOURCE_ID = "serpavi"
USER_AGENT = "HouseFinder/0.1 (datos abiertos)"
VINTAGE = 2021  # seccionado del Censo 2021

# Hoja → (nivel, columna con el código, columna con la provincia)
SHEETS = {
    "Secciones censales": ("seccion", "CUSEC", "CPRO"),
    "Distritos": ("distrito", "CUDIS", "CPRO"),
    "Municipios": ("municipio", "CUMUN", "CPRO"),
    "Provincias": ("provincia", "CPRO", "CPRO"),
}
COLUMN = re.compile(r"^(BI_ALVHEPCO_T|ALQM2_LV_|ALQTBID12_|SLVM2_)(?:(M|25|75)_)?(VC|VU)_(\d{2})$")
MEASURES = {
    "BI_ALVHEPCO_T": ("alquileres", "viviendas"),
    "ALQM2_LV_": ("renta_m2_mes", "EUR/m2 mes"),
    "ALQTBID12_": ("renta_mes", "EUR/mes"),
    "SLVM2_": ("superficie", "m2"),
}
STATS = {"M": "mediana", "25": "p25", "75": "p75", None: "n"}
TYPOLOGIES = {"VC": "colectiva", "VU": "unifamiliar"}
FOUR = Decimal("0.0001")


@dataclass
class ParsedSerpavi:
    rows: list[ReferenceRow] = field(default_factory=list)
    territories: Counter[str] = field(default_factory=Counter)  # por nivel
    unknown_columns: set[str] = field(default_factory=set)
    bad_values: int = 0

    @property
    def years(self) -> list[int]:
        return sorted({r.year for r in self.rows})


def default_cache() -> Path:
    return Path.home() / ".cache" / "housefinder" / "serpavi"


def download(client: httpx.Client, url: str, cache: Path) -> Path:
    """Descarga el Excel a la caché si no está ya (el nombre cambia con cada edición)."""
    target = cache / Path(httpx.URL(url).path).name.replace("%20", " ")
    if target.exists() and target.stat().st_size > 0:
        return target
    cache.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    with client.stream("GET", url, timeout=600) as response:
        response.raise_for_status()
        with partial.open("wb") as out:
            for chunk in response.iter_bytes():
                out.write(chunk)
    partial.rename(target)
    return target


def parse(path: Path, province: str) -> ParsedSerpavi:
    parsed = ParsedSerpavi()
    for sheet, (level, code_column, province_column) in SHEETS.items():
        for row in iter_rows(path, sheet):
            if row.get(province_column, "").zfill(2) != province:
                continue
            code = row[code_column]
            parsed.territories[level] += 1
            parsed.rows.extend(_values(row, level, code, parsed))
    return parsed


def _values(row: dict[str, str], level: str, code: str,
            parsed: ParsedSerpavi) -> Iterator[ReferenceRow]:
    for column, raw in row.items():
        match = COLUMN.match(column)
        if match is None:
            if column.upper() == column and re.search(r"_\d{2}$", column):
                parsed.unknown_columns.add(column)
            continue
        prefix, stat, typology, year = match.groups()
        try:
            value = Decimal(raw).quantize(FOUR)
        except InvalidOperation:
            parsed.bad_values += 1
            continue
        measure, unit = MEASURES[prefix]
        yield ReferenceRow(level=level, code=code, vintage=VINTAGE, year=2000 + int(year),
                           quarter=0, measure=measure, typology=TYPOLOGIES[typology],
                           stat=STATS[stat], value=value, unit=unit)


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_record(path: Path, url: str, parsed: ParsedSerpavi) -> SourceRecord:
    years = parsed.years
    return SourceRecord(
        id=SOURCE_ID,
        name="SERPAVI: Sistema Estatal de Referencia del Precio del Alquiler de Vivienda "
             "(Ministerio de Vivienda y Agenda Urbana)",
        url=PAGE,
        license=LICENSE,
        fetched_at=datetime.now(UTC),
        notes=(f"Fichero {url}; sha256 {fingerprint(path)}; años {years[0]}–{years[-1]}; "
               f"{len(parsed.rows)} valores; seccionado {VINTAGE}. Condiciones: {LICENSE_URL}"
               if years else f"Fichero {url}: sin valores"),
    )


def load(province: str, conninfo: str, url: str = URL, cache: Path | None = None,
         client: httpx.Client | None = None) -> dict[str, Any]:
    """Descarga (si hace falta) y carga el SERPAVI de una provincia. Idempotente."""
    from housefinder.db.references import load_references

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        path = download(client or own, url, cache or default_cache())
    parsed = parse(path, province)
    if not parsed.rows:
        raise LookupError(f"El SERPAVI no trae valores para la provincia {province}")
    sections = {r.code for r in parsed.rows if r.level == "seccion"}
    loaded, without_map = load_references(conninfo, source_record(path, url, parsed),
                                          parsed.rows, sections, VINTAGE)
    return {"loaded": loaded, "years": parsed.years, "territories": dict(parsed.territories),
            "sections_without_map": len(without_map), "bad_values": parsed.bad_values,
            "unknown_columns": sorted(parsed.unknown_columns)}


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--province", required=True, help="código INE de 2 cifras (28)")
    parser.add_argument("--url", default=URL, help="Excel del SERPAVI (cambia con cada edición)")
    args = parser.parse_args()
    result = load(args.province, database_url(), args.url)
    print(f"SERPAVI: {result['loaded']} valores, años {result['years'][0]}–{result['years'][-1]}, "
          f"territorios {result['territories']}")
    if result["sections_without_map"]:
        print(f"Aviso: {result['sections_without_map']} secciones sin cartografía {VINTAGE} "
              "cargada (make sections YEAR=2021)")
    if result["unknown_columns"]:
        print(f"Aviso: columnas no reconocidas: {', '.join(result['unknown_columns'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
