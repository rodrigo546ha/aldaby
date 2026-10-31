"""Escenarios de revalorización (F5.5, ADR-0018). Funciones puras.

- **Ciclo:** crecimiento anual compuesto de todas las ventanas históricas de la duración pedida de
  un índice trimestral (el IPV de la comunidad); sus percentiles dan el escenario.
- **Municipio:** la brecha de su renta frente a la de la provincia (en logaritmos) se cierra o se
  abre un factor (1 + b) cada `step` años. El signo de b cambia con el ciclo, así que el escenario
  optimista toma el b que favorece al municipio y el conservador, el otro.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from housefinder.core.figures import ratio

STEP_YEARS = 3  # paso de la estimación de b (crecimientos a 3 años)


def window_growths(points: Iterable[tuple[int, int, Decimal]], years: int) -> list[Decimal]:
    """Crecimiento anual compuesto de cada pareja (año, trimestre) → (año + years, trimestre)."""
    series = {(year, quarter): value for year, quarter, value in points}
    growths = []
    for (year, quarter), start in series.items():
        end = series.get((year + years, quarter))
        if end is None or start <= 0:
            continue
        growths.append(ratio((end / start) ** (Decimal(1) / years) - 1))
    return growths


def percentile(values: list[Decimal], p: Decimal) -> Decimal:
    """Percentil con interpolación lineal (como `percentile_cont` de PostgreSQL)."""
    if not values:
        raise ValueError("Sin valores para el percentil")
    ordered = sorted(values)
    position = p * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (position - low) * (ordered[high] - ordered[low])


def relative_log_growth(gap: Decimal, b: Decimal, horizon_years: int,
                        step_years: int = STEP_YEARS) -> Decimal:
    """Crecimiento logarítmico del municipio sobre el de la comunidad en el horizonte."""
    factor = (1 + b) ** (Decimal(horizon_years) / step_years)
    return ratio(gap * (factor - 1))


def scenario_bounds(gap: Decimal, b_low: Decimal, b_high: Decimal) -> tuple[Decimal, Decimal]:
    """(b optimista, b conservador): el que más sube al municipio y el que menos."""
    # relativo = brecha × ((1 + b)^n − 1): crece con b si la brecha es positiva
    return (b_high, b_low) if gap >= 0 else (b_low, b_high)


def scenario_rate(regional_rate: Decimal, relative: Decimal, horizon_years: int) -> Decimal:
    """Tasa anual del escenario: la de la comunidad más el diferencial anual del municipio."""
    yearly = (relative / horizon_years).exp()
    return ratio((1 + regional_rate) * yearly - 1)
