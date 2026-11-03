"""Atlas de Distribución de Renta de los Hogares (ADRH) del INE por sección censal (F3.3).

Fuente: API Tempus del INE, tablas por provincia (Madrid: 31097 renta, 31105 demografía; las de
todas, en data/territory/adrh_tablas.yaml), serie 2015–2024. Cada serie trae en sus metadatos el
código de la sección.

Cruce con la cartografía: el dato del año t va sobre el seccionado a 1 de enero de t+1
(la población del ADRH es la del Censo Anual a esa fecha). Ver
docs/research/f3-3-atlas-renta.md. Una sección del ADRH que no existe en la cartografía
t+1 cargada se informa y no se carga.

Los porcentajes del INE se guardan en tanto por uno. Licencia: CC BY 4.0 (aviso legal del INE).

Uso: `python -m housefinder.ingestion.ine_adrh --province 28` con `DATABASE_URL`, después de
cargar las cartografías de 2016 en adelante (`make sections`).
"""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import yaml

from housefinder.db.indicators import IndicatorRow
from housefinder.db.sections import SourceRecord
from housefinder.ingestion.ine_sections import CODE, LICENSE, LICENSE_URL, USER_AGENT

TEMPUS = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table}"
TABLE_PAGE = "https://www.ine.es/jaxiT3/Tabla.htm?t={table}"
SECTION_VARIABLE = "Secciones"
BASE_DATA = "Dato base"
HUNDRED = Decimal(100)


@dataclass(frozen=True)
class Indicator:
    key: str
    unit: str  # 'EUR', 'años', 'personas', 'ratio'
    percent: bool = False  # el INE lo da en %, se guarda en tanto por uno


# Nombre del INE → indicador. Un nombre que no esté aquí para la carga: no se adivina.
INDICATORS: dict[str, Indicator] = {
    "Renta neta media por persona": Indicator("renta_neta_media_persona", "EUR"),
    "Renta neta media por hogar": Indicator("renta_neta_media_hogar", "EUR"),
    "Media de la renta por unidad de consumo": Indicator("renta_media_unidad_consumo", "EUR"),
    "Mediana de la renta por unidad de consumo": Indicator(
        "renta_mediana_unidad_consumo", "EUR"
    ),
    "Renta mediana por hogar": Indicator("renta_mediana_hogar", "EUR"),
    "Renta bruta media por persona": Indicator("renta_bruta_media_persona", "EUR"),
    "Renta bruta media por hogar": Indicator("renta_bruta_media_hogar", "EUR"),
    "Edad media de la población": Indicator("edad_media", "años"),
    "Porcentaje de población menor de 18 años": Indicator(
        "poblacion_menor_18", "ratio", percent=True
    ),
    "Porcentaje de población de 65 y más años": Indicator(
        "poblacion_65_y_mas", "ratio", percent=True
    ),
    "Tamaño medio del hogar": Indicator("tamano_medio_hogar", "personas"),
    "Porcentaje de hogares unipersonales": Indicator(
        "hogares_unipersonales", "ratio", percent=True
    ),
    "Población": Indicator("poblacion", "personas"),
    "Porcentaje de población española": Indicator(
        "poblacion_espanola", "ratio", percent=True
    ),
}

# Tablas por provincia (INEbase, ADRH, resultados por provincias), desde su fichero de datos.
def _province_tables() -> dict[str, dict[str, int]]:
    """Tablas de cada provincia: data/territory/adrh_tablas.yaml (cómo se sacaron, allí)."""
    path = Path(__file__).resolve().parents[3] / "data" / "territory" / "adrh_tablas.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))["provincias"]
    return {str(code): {k: int(v) for k, v in tables.items()} for code, tables in data.items()}


PROVINCE_TABLES = _province_tables()


@dataclass(frozen=True)
class ParsedTable:
    rows: list[IndicatorRow]
    skipped_levels: int  # series de municipios y distritos (no se cargan aquí)
    empty_values: int  # años sin dato publicado
    other_province: int  # series de secciones de otra provincia, mal archivadas por el INE
    years: tuple[int, ...]


def parse_table(payload: list[dict[str, Any]], province: str) -> ParsedTable:
    """Indicadores por sección de una respuesta de DATOS_TABLA con `tip=AM`."""
    rows: list[IndicatorRow] = []
    skipped = empty = foreign = 0
    years: set[int] = set()
    for series in payload:
        meta = {_variable(m): m for m in series.get("MetaData", [])}
        section = meta.get(SECTION_VARIABLE)
        if section is None:
            skipped += 1
            continue
        code = str(section.get("Codigo", ""))
        if not CODE.match(code):
            raise ValueError(f"{series.get('COD')}: código de sección no válido {code!r}")
        if not code.startswith(province):
            # p. ej. la tabla de Baleares trae una sección de Sant Joan d'Alacant: se carga con
            # la tabla de su provincia, no con esta
            foreign += 1
            continue
        kind = meta.get("Tipo de dato")
        if kind is not None and kind.get("Nombre") != BASE_DATA:
            raise ValueError(f"{series.get('COD')}: tipo de dato no esperado {kind!r}")
        names = [m["Nombre"] for var, m in meta.items()
                 if var not in (SECTION_VARIABLE, "Tipo de dato")]
        if len(names) != 1 or names[0] not in INDICATORS:
            raise ValueError(f"{series.get('COD')}: indicador desconocido {names!r}")
        indicator = INDICATORS[names[0]]
        for point in series.get("Data", []):
            year = int(point["Anyo"])
            years.add(year)
            raw = point.get("Valor")
            if raw is None or point.get("Secreto"):
                empty += 1
                continue
            value = Decimal(str(raw))
            if indicator.percent:
                value = value / HUNDRED
            rows.append(IndicatorRow(code, year + 1, indicator.key, year, value, indicator.unit))
    return ParsedTable(rows, skipped, empty, foreign, tuple(sorted(years)))


def _variable(meta: dict[str, Any]) -> str:
    """Nombre de la variable: `T3_Variable` en DATOS_TABLA, `Variable.Nombre` en SERIES_TABLA."""
    return str(meta.get("T3_Variable") or (meta.get("Variable") or {}).get("Nombre", ""))


def fetch_table(client: httpx.Client, table: int, last_years: int) -> list[dict[str, Any]]:
    response = client.get(
        TEMPUS.format(table=table), params={"tip": "AM", "nult": str(last_years)}, timeout=600
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Respuesta no esperada de la tabla {table}: {type(payload).__name__}")
    return payload


def fingerprint(rows: list[IndicatorRow]) -> str:
    digest = hashlib.sha256()
    for r in sorted(rows, key=lambda r: (r.section_code, r.indicator, r.year)):
        digest.update(f"{r.section_code}|{r.indicator}|{r.year}|{r.value}".encode())
    return digest.hexdigest()


def source_record(table: int, name: str, parsed: ParsedTable) -> SourceRecord:
    years = f"{parsed.years[0]}–{parsed.years[-1]}" if parsed.years else "sin años"
    return SourceRecord(
        id=f"ine-adrh-{table}",
        name=f"Atlas de Distribución de Renta de los Hogares (INE), {name}, tabla {table}",
        url=TABLE_PAGE.format(table=table),
        license=LICENSE,
        fetched_at=datetime.now(UTC),
        notes=(
            f"Años {years}; {len(parsed.rows)} valores por sección; sha256 "
            f"{fingerprint(parsed.rows)}. El año t va sobre el seccionado de t+1. "
            f"Condiciones: {LICENSE_URL}"
        ),
    )


def missing_by_year(missing: list[IndicatorRow]) -> Iterator[tuple[int, int]]:
    counts = Counter((r.year, r.section_code) for r in missing)
    per_year = Counter(year for year, _ in counts)
    yield from sorted(per_year.items())


class MissingSections(LookupError):
    """Hay valores cuya sección no está en la cartografía t+1: falta cargar esa cartografía."""


def load(
    province: str, last_years: int, conninfo: str, client: httpx.Client | None = None
) -> dict[str, Any]:
    """Descarga y carga las tablas del ADRH de una provincia. Idempotente.

    Si algún valor no encuentra su sección, carga el resto y lanza `MissingSections` para que
    el trabajo falle, se reintente y avise: casi siempre falta la cartografía del año nuevo.
    """
    from housefinder.db.indicators import load_indicators

    tables = PROVINCE_TABLES.get(province)
    if tables is None:
        raise LookupError(f"Sin tablas del ADRH registradas para la provincia {province}")
    summary: list[dict[str, Any]] = []
    missing: dict[int, int] = {}
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as own:
        http = client or own
        for name, table in tables.items():
            parsed = parse_table(fetch_table(http, table, last_years), province)
            report = load_indicators(conninfo, source_record(table, name, parsed), parsed.rows)
            table_missing = dict(missing_by_year(report.without_section))
            for year, count in table_missing.items():
                missing[year] = max(missing.get(year, 0), count)
            summary.append({
                "table": table, "name": name, "years": list(parsed.years),
                "loaded": report.loaded, "empty": parsed.empty_values,
                "skipped_levels": parsed.skipped_levels,
                "other_province": parsed.other_province, "missing_by_year": table_missing,
            })
    if missing:
        detail = ", ".join(f"{year}: {n} secciones sin cartografía {year + 1}"
                           for year, n in sorted(missing.items()))
        raise MissingSections(f"Faltan cartografías ({detail}); el resto está cargado")
    return {"tables": summary}


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--province", required=True, help="código INE de 2 cifras (28)")
    parser.add_argument("--last-years", type=int, default=10)
    args = parser.parse_args()
    try:
        result = load(args.province, args.last_years, database_url())
    except MissingSections as exc:
        print(f"Aviso: {exc}")
        return 1
    for t in result["tables"]:
        print(f"Tabla {t['table']} ({t['name']}): años {tuple(t['years'])}, {t['loaded']} "
              f"valores cargados, {t['empty']} sin dato, {t['skipped_levels']} series de "
              "municipio o distrito no cargadas"
              + (f", {t['other_province']} de otra provincia" if t["other_province"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
