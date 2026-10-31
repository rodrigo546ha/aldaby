"""Escenarios de revalorización de un municipio (F5.5, ADR-0018).

- **Ciclo de la comunidad:** P25, mediana y P75 del crecimiento anual de todas las ventanas
  históricas del IPV de la duración del horizonte (vivienda de segunda mano o nueva).
- **Municipio:** su brecha de renta frente a la provincia se cierra o se abre con el coeficiente
  b del parámetro `convergencia_municipal`. El signo de b cambia con el ciclo: el escenario base
  usa el b global (casi cero), el optimista el que favorece al municipio y el conservador el otro.
- El crecimiento relativo se mide con la renta y se aplica al precio: supuesto explícito.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef
from housefinder.db.connection import Connection
from housefinder.db.references import rent_stats, series_values
from housefinder.engines.appreciation import (
    percentile,
    relative_log_growth,
    scenario_bounds,
    scenario_rate,
    window_growths,
)
from housefinder.params.book import ParamBook
from housefinder.params.valuation import convergence
from housefinder.valuation.service import IPV, REGION_BY_PROVINCE, SERPAVI

MIN_WINDOWS = 8  # por debajo, ventanas más cortas: si no, el percentil no dice nada
QUANTILES = {"conservative": Decimal("0.25"), "base": Decimal("0.5"),
             "optimistic": Decimal("0.75")}
NAMES = {"conservative": "conservador", "base": "base", "optimistic": "optimista"}
MODEL = SourceRef("model", "escenarios-revalorizacion-v1")
HISTORY = SourceRef("assumption", "el-ciclo-futuro-como-el-historico-del-ipv")
RENT_TO_PRICE = SourceRef("assumption", "el-precio-sigue-a-la-renta-frente-a-la-provincia")


class NoScenarios(LookupError):
    """Sin índice de precios para la comunidad del municipio."""


@dataclass(frozen=True)
class Scenario:
    name: str  # 'conservative', 'base' u 'optimistic'
    rate: Decimal  # revalorización anual (tanto por uno)
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class AppreciationReport:
    scenarios: dict[str, Scenario]
    figures: list[Figure]
    notes: list[str] = field(default_factory=list)


def appreciation_scenarios(
    conn: Connection, book: ParamBook, municipality_code: str, horizon_years: int = 10,
    new_build: bool = False, on: date | None = None,
) -> AppreciationReport:
    on = on or date.today()
    province = municipality_code[:2]
    region = REGION_BY_PROVINCE.get(province)
    if region is None:
        raise NoScenarios(f"Sin índice de precios cargado para la provincia {province}")
    typology = "nueva" if new_build else "segunda_mano"
    series = series_values(conn, IPV, "comunidad", "ipv", region, typology)
    points = [(year, quarter, value) for (_, year, quarter), value in series.items() if quarter]
    if not points:
        raise NoScenarios(f"Sin IPV de la comunidad {region}")
    years = horizon_years
    growths = window_growths(points, years)
    while len(growths) < MIN_WINDOWS and years > 1:
        years -= 1
        growths = window_growths(points, years)
    if not growths:
        raise NoScenarios("El IPV no tiene historia suficiente para ninguna ventana")
    regional = {name: percentile(growths, q) for name, q in QUANTILES.items()}
    first, last = min(points)[:2], max(points)[:2]
    notes = [f"Ciclo de la comunidad: {len(growths)} ventanas de {years} años del IPV "
             f"({first[0]}T{first[1]}–{last[0]}T{last[1]}), percentiles 25, 50 y 75."]
    if years < horizon_years:
        notes.append(f"No hay historia para ventanas de {horizon_years} años: se usan de {years}.")

    conv = convergence(book, f"ES-{region}", on)
    municipal = rent_stats(conn, "municipio", municipality_code, "colectiva")
    provincial = (rent_stats(conn, "provincia", province, "colectiva", municipal.year)
                  if municipal else None)
    sources = (SourceRef("dataset", f"{IPV}@{last[0]}T{last[1]}"), MODEL, HISTORY)
    if municipal is None or provincial is None:
        gap = Decimal(0)
        notes.append("Sin renta del municipio: los tres escenarios son los de la comunidad.")
    else:
        gap = (municipal.median / provincial.median).ln()
        sources = (*sources, SourceRef("dataset", f"{SERPAVI}@{municipal.year}"), conv.source,
                   RENT_TO_PRICE)
        position = "por debajo" if gap < 0 else "por encima"
        distance = _pct(abs(municipal.median / provincial.median - 1), 0)
        notes.append(
            f"La renta del municipio está un {distance} "
            f"{position} de la de la provincia ({municipal.year}). En 2011–2017 los municipios "
            "caros se alejaron y desde 2018 los baratos se acercaron: el escenario optimista "
            "toma lo que le favorece y el conservador, lo contrario.")
    b_optimistic, b_conservative = scenario_bounds(gap, conv.b_low, conv.b_high)
    betas = {"conservative": b_conservative, "base": conv.b_base, "optimistic": b_optimistic}

    scenarios, figures = {}, []
    as_of = _quarter_end(*last)
    for name in QUANTILES:
        relative = relative_log_growth(gap, betas[name], horizon_years, conv.step_years)
        rate = scenario_rate(regional[name], relative, horizon_years)
        scenarios[name] = Scenario(name, rate, sources)
        figures.append(Figure(
            key=f"valuation.appreciation_{name}", value=rate, unit="ratio", as_of=as_of,
            sources=sources,
            formula=(f"Escenario {NAMES[name]}: IPV de la comunidad {_pct(regional[name], 2)} "
                     f"al año (percentil {int(QUANTILES[name] * 100)} de las ventanas de "
                     f"{years} años) "
                     f"y brecha de renta del municipio con b = {betas[name]} cada "
                     f"{conv.step_years} años durante {horizon_years} años"),
        ))
    return AppreciationReport(scenarios, figures, notes)


def _pct(value: Decimal, places: int) -> str:
    """0,0203 → «2,03 %»."""
    return f"{value * 100:.{places}f}".replace(".", ",") + " %"


def _quarter_end(year: int, quarter: int) -> date:
    return {1: date(year, 3, 31), 2: date(year, 6, 30), 3: date(year, 9, 30),
            4: date(year, 12, 31)}[quarter]
