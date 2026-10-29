"""Cifras del territorio a partir de los indicadores por sección (F3.6). Funciones puras.

- Valor del último año de cada indicador.
- Cambio a 5 años, solo si la sección conserva el polígono en las dos cartografías: una
  sección redibujada con el mismo código no es la misma zona. Se tolera un 1 % de diferencia
  de área por redigitalización (supuesto propio, citado en la cifra).
- Serie anual de los años en que la sección conserva el polígono.
- Avisos de la metodología del ADRH: renta asignada en secciones de menos de 100 habitantes y
  cambio de fuente de población en 2023 (docs/research/f3-3-atlas-renta.md).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, ratio
from housefinder.db.indicators import IndicatorRow
from housefinder.ingestion.ine_adrh import INDICATORS

TREND_YEARS = 5
STABILITY_TOLERANCE = 0.01  # diferencia de área admitida entre cartografías (tanto por uno)
STABLE_SECTION = SourceRef("assumption", "seccion-estable-1-por-ciento")
SMALL_SECTION = 100  # habitantes: por debajo, el INE asigna la renta de la entidad superior
CENSUS_SOURCE_CHANGE = 2023  # año desde el que la población sale del Censo Anual
LABELS = {ind.key: name for name, ind in INDICATORS.items()}
UNITS = {"EUR": "EUR/año", "personas": "personas", "años": "años", "ratio": "ratio"}
# Indicadores cuyo cambio se da en diferencia (puntos o años) y no en porcentaje.
ABSOLUTE_CHANGE_UNITS = {"ratio", "años"}
INCOME_PREFIX = "renta_"


@dataclass(frozen=True)
class Context:
    code: str
    vintage: int  # cartografía de la sección encontrada
    location_sources: tuple[SourceRef, ...]  # geocodificador, si lo hubo
    map_sources: dict[int, SourceRef]  # cartografía → su fuente
    value_sources: dict[tuple[str, int], str]  # (indicador, año) → fuente del dato


def territory_figures(
    history: list[IndicatorRow], stable: set[int], ctx: Context
) -> tuple[list[Figure], dict[str, list[Figure]], list[str]]:
    """(cifras del último año y cambios, series por indicador, avisos)."""
    by_indicator: dict[str, dict[int, IndicatorRow]] = defaultdict(dict)
    for row in history:
        if row.section_vintage in stable:
            by_indicator[row.indicator][row.year] = row
    current_year = ctx.vintage - 1
    figures: list[Figure] = []
    series: dict[str, list[Figure]] = {}
    notes: list[str] = []

    population = by_indicator.get("poblacion", {}).get(current_year)
    small = population is not None and population.value < SMALL_SECTION
    if small:
        notes.append(
            f"La sección tiene menos de {SMALL_SECTION} habitantes: el INE le asigna la renta "
            "del distrito o del municipio que la contiene."
        )

    for indicator in sorted(by_indicator):
        rows = by_indicator[indicator]
        latest = rows.get(current_year)
        if latest is None:
            continue
        figures.append(_value_figure(latest, ctx, imputed=small and _is_income(indicator)))
        series[indicator] = [_value_figure(rows[y], ctx, key_year=True) for y in sorted(rows)]
        base = rows.get(current_year - TREND_YEARS)
        if base is not None and base.value != 0:
            figures.append(_change_figure(base, latest, ctx))

    if not any(f.key.endswith(f".change_{TREND_YEARS}y") for f in figures):
        notes.append(
            f"Sin cambio a {TREND_YEARS} años: la sección no existía o se redibujó en la "
            f"cartografía de {ctx.vintage - TREND_YEARS}."
        )
    elif current_year - TREND_YEARS < CENSUS_SOURCE_CHANGE <= current_year:
        notes.append(
            f"Desde {CENSUS_SOURCE_CHANGE} la población del Atlas sale del Censo Anual de "
            "Población y no del Fichero Precensal: parte del cambio puede deberse a la fuente."
        )
    return figures, series, notes


def _is_income(indicator: str) -> bool:
    return indicator.startswith(INCOME_PREFIX)


def _sources(row: IndicatorRow, ctx: Context) -> tuple[SourceRef, ...]:
    value_source = SourceRef("dataset", ctx.value_sources[(row.indicator, row.year)])
    map_source = ctx.map_sources.get(row.section_vintage)
    return combine_sources(
        (value_source,), (map_source,) if map_source else (), ctx.location_sources
    )


def _value_figure(
    row: IndicatorRow, ctx: Context, imputed: bool = False, key_year: bool = False
) -> Figure:
    key = f"territory.{row.indicator}" + (f".{row.year}" if key_year else "")
    formula = (
        f"{LABELS[row.indicator]} del Atlas de renta del INE, año {row.year}, sección "
        f"{row.section_code} (seccionado de {row.section_vintage})"
    )
    if imputed:
        formula += "; valor asignado por el INE desde el distrito o el municipio"
    return Figure(key, row.value, UNITS[row.unit], formula, _sources(row, ctx))


def _change_figure(base: IndicatorRow, latest: IndicatorRow, ctx: Context) -> Figure:
    key = f"territory.{latest.indicator}.change_{TREND_YEARS}y"
    sources = combine_sources(_sources(base, ctx), _sources(latest, ctx), (STABLE_SECTION,))
    label = LABELS[latest.indicator].lower()
    if latest.unit in ABSOLUTE_CHANGE_UNITS:
        delta = latest.value - base.value
        unit = UNITS[latest.unit]
        value = ratio(delta) if latest.unit == "ratio" else delta
        formula = f"{label} en {latest.year} − en {base.year}"
    else:
        value = ratio((latest.value - base.value) / base.value)
        unit = "ratio"
        formula = f"({label} en {latest.year} − en {base.year}) / en {base.year}"
    return Figure(key, Decimal(value), unit, formula, sources)
