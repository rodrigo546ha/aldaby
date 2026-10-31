"""Backtesting del modelo de valoración (F5.6, ADR-0018): qué habría estimado con datos de años
anteriores.

1. **Renta por sección.** Con los datos del año t se estima la mediana de la sección (contraída
   hacia el municipio con cada k de la rejilla) y se compara con la mediana real de t+1. Dos
   versiones: tal cual funciona el modelo (sin actualizar: el error incluye la subida del mercado)
   y descontando la variación del municipio entre t y t+1 (aísla el error de la zona, que es el que
   corrige k). Con k = None, solo el municipio.
2. **Actualización con el índice.** El valor tasado municipal de t+1 estimado como el de t por la
   variación del IPV (media de los cuatro trimestres), frente al real.
3. **Relación precio/renta de un año antes.** El valor tasado de t+1 estimado como la renta
   municipal de t+1 × 12 × la relación de t, frente al real.

El precio por sección no se puede medir: no hay precio público por sección con el que comparar.

Uso: `python -m housefinder.valuation.backtest --province 28` con `DATABASE_URL`.
"""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from statistics import median

from housefinder.db.references import RentRow
from housefinder.engines.valuation import RentStats, shrink

K_GRID: tuple[Decimal | None, ...] = (Decimal(0), Decimal(2), Decimal(5), Decimal(10),
                                       Decimal(20), Decimal(40), Decimal(80), Decimal(160), None)
TEN_PERCENT = Decimal("0.10")
BUCKETS = ((10, 29, "10–29"), (30, 99, "30–99"), (100, 10**9, "100 o más"))


@dataclass(frozen=True)
class Errors:
    count: int
    mdape: Decimal  # mediana del error absoluto relativo (tanto por uno)
    mae: Decimal  # error absoluto medio, en la unidad de la medida
    within_10: Decimal  # parte de las estimaciones a menos de un 10 % del valor real

    def as_dict(self) -> dict[str, str | int]:
        return {"count": self.count, "mdape": f"{self.mdape:.4f}", "mae": f"{self.mae:.2f}",
                "within_10": f"{self.within_10:.4f}"}


def errors(pairs: Iterable[tuple[Decimal, Decimal]]) -> Errors:
    """(estimado, real) → errores. Los pares con valor real 0 o negativo no cuentan."""
    absolute, relative = [], []
    for predicted, actual in pairs:
        if actual <= 0:
            continue
        absolute.append(abs(predicted - actual))
        relative.append(abs(predicted - actual) / actual)
    if not relative:
        return Errors(0, Decimal(0), Decimal(0), Decimal(0))
    within = sum(1 for r in relative if r <= TEN_PERCENT)
    return Errors(len(relative), Decimal(median(relative)), sum(absolute) / len(absolute),
                  Decimal(within) / len(relative))


def _stats(row: RentRow) -> RentStats:
    return RentStats(row.n, row.p25, row.median, row.p75)


@dataclass(frozen=True)
class RentCase:
    n: int | None
    predicted: Decimal
    actual: Decimal


def rent_cases(
    sections: dict[tuple[str, int], RentRow], municipalities: dict[tuple[str, int], RentRow],
    k: Decimal | None, growth_adjusted: bool, horizon: int = 1,
) -> list[RentCase]:
    """Estimación con el año t frente a la mediana real de t + `horizon`."""
    cases = []
    for (code, year), now in sections.items():
        later = sections.get((code, year + horizon))
        muni_now = municipalities.get((code[:5], year))
        muni_later = municipalities.get((code[:5], year + horizon))
        if later is None or muni_now is None:
            continue
        if k is None:
            predicted = muni_now.median
        else:
            predicted = shrink(_stats(now), _stats(muni_now), k).median
        if growth_adjusted:
            if muni_later is None or muni_now.median <= 0:
                continue
            predicted = predicted * muni_later.median / muni_now.median
        cases.append(RentCase(now.n, predicted, later.median))
    return cases


def rent_backtest(
    sections: dict[tuple[str, int], RentRow], municipalities: dict[tuple[str, int], RentRow],
    growth_adjusted: bool, grid: tuple[Decimal | None, ...] = K_GRID, horizon: int = 1,
) -> dict[str, Errors]:
    """Errores de la mediana de t + horizon por cada k de la rejilla («municipio»: solo el
    municipio)."""
    return {("municipio" if k is None else str(k)):
            errors((c.predicted, c.actual)
                   for c in rent_cases(sections, municipalities, k, growth_adjusted, horizon))
            for k in grid}


def signed_bias(cases: list[RentCase]) -> Decimal:
    """Mediana de (estimado − real) / real: negativa si el modelo se queda corto."""
    values = [(c.predicted - c.actual) / c.actual for c in cases if c.actual > 0]
    return Decimal(median(values)) if values else Decimal(0)


def by_size(cases: list[RentCase]) -> dict[str, Errors]:
    """Errores por número de alquileres de la sección en el año t."""
    groups: dict[str, list[RentCase]] = defaultdict(list)
    for case in cases:
        for low, high, label in BUCKETS:
            if case.n is not None and low <= case.n <= high:
                groups[label].append(case)
    return {label: errors((c.predicted, c.actual) for c in groups[label])
            for _, _, label in BUCKETS}


def cpi_updated_cases(
    sections: dict[tuple[str, int], RentRow], cpi_annual: dict[int, Decimal], horizon: int,
    since: int = 0,
) -> list[RentCase]:
    """Mediana de la sección de t × IPC de alquiler medio de t + h / de t, frente a la real."""
    cases = []
    for (code, year), now in sections.items():
        later = sections.get((code, year + horizon))
        if year < since or later is None or year not in cpi_annual or \
                year + horizon not in cpi_annual:
            continue
        cases.append(RentCase(now.n, now.median * cpi_annual[year + horizon] / cpi_annual[year],
                              later.median))
    return cases


def monthly_annual_means(monthly: dict[tuple[str, int, int], Decimal]) -> dict[int, Decimal]:
    """(código, año, mes) → media anual de los años con los doce meses."""
    months: dict[int, list[Decimal]] = defaultdict(list)
    for (_, year, month), value in monthly.items():
        if 1 <= month <= 12:
            months[year].append(value)
    return {year: sum(v) / 12 for year, v in months.items() if len(v) == 12}


def convergence_by_period(
    municipalities: dict[tuple[str, int], RentRow], provinces: dict[tuple[str, int], RentRow],
    province: str, step: int = 3,
) -> tuple[Decimal, dict[int, Decimal]]:
    """Coeficiente b de rel = b · brecha, sin constante: global y por año de partida.

    brecha = log(renta municipal / provincial) en t; rel = crecimiento logarítmico municipal
    menos provincial entre t y t + step. b < 0: los municipios baratos suben más (convergen).
    """
    pairs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for (code, year), now in municipalities.items():
        later = municipalities.get((code, year + step))
        prov_now, prov_later = provinces.get((province, year)), provinces.get(
            (province, year + step))
        if later is None or prov_now is None or prov_later is None:
            continue
        gap = math.log(now.median / prov_now.median)
        relative = math.log(later.median / now.median) - math.log(
            prov_later.median / prov_now.median)
        pairs[year].append((gap, relative))

    def slope(data: list[tuple[float, float]]) -> Decimal:
        den = sum(g * g for g, _ in data)
        return Decimal(str(round(sum(g * r for g, r in data) / den, 4))) if den else Decimal(0)

    by_year = {year: slope(data) for year, data in sorted(pairs.items())}
    return slope([p for data in pairs.values() for p in data]), by_year


def index_backtest(
    appraisal: dict[tuple[str, int, int], Decimal], index: dict[tuple[str, int, int], Decimal],
    region: str,
) -> Errors:
    """Valor tasado de t+1 = valor de t × IPV medio de t+1 / IPV medio de t."""
    annual = _annual_means(index, region)
    pairs = []
    for (code, year, _), value in appraisal.items():
        later = appraisal.get((code, year + 1, 0))
        if later is None or year not in annual or year + 1 not in annual:
            continue
        pairs.append((value * annual[year + 1] / annual[year], later))
    return errors(pairs)


def ratio_backtest(
    appraisal: dict[tuple[str, int, int], Decimal], rents: dict[tuple[str, int], RentRow],
) -> Errors:
    """Valor tasado de t+1 = renta municipal de t+1 × 12 × (valor tasado / renta anual) de t."""
    pairs = []
    for (code, year, _), value in appraisal.items():
        later = appraisal.get((code, year + 1, 0))
        rent_now, rent_later = rents.get((code, year)), rents.get((code, year + 1))
        if later is None or rent_now is None or rent_later is None or rent_now.median <= 0:
            continue
        ratio = value / (rent_now.median * 12)
        pairs.append((rent_later.median * 12 * ratio, later))
    return errors(pairs)


def _since(sections: dict[tuple[str, int], RentRow], year: int) -> dict[tuple[str, int], RentRow]:
    """Solo los años desde `year`: las estimaciones de t ≥ year y sus valores reales de t + h."""
    return {key: row for key, row in sections.items() if key[1] >= year}


def _annual_means(index: dict[tuple[str, int, int], Decimal], region: str) -> dict[int, Decimal]:
    quarters: dict[int, list[Decimal]] = defaultdict(list)
    for (code, year, quarter), value in index.items():
        if code == region and 1 <= quarter <= 4:
            quarters[year].append(value)
    return {year: sum(v) / 4 for year, v in quarters.items() if len(v) == 4}


def run(conninfo: str, province: str, region: str) -> dict[str, object]:
    from housefinder.db.connection import connect
    from housefinder.db.references import rent_table, series_values

    with connect(conninfo) as conn:
        cpi = {(code, year, month): value for code, year, month, value in conn.execute(
            "SELECT code, year, month, value FROM market_references WHERE source_id = "
            "'ine-ipc-alquiler' AND code = %s AND month > 0", (region,))}
        sections = rent_table(conn, "seccion", "colectiva", province)
        municipalities = rent_table(conn, "municipio", "colectiva", province)
        provinces = rent_table(conn, "provincia", "colectiva", province)
        appraisal = series_values(conn, "valor-tasado-comunidad-madrid", "municipio",
                                  "valor_tasado_m2", province)
        index = series_values(conn, "ine-ipv-80270", "comunidad", "ipv", region)
    chosen = Decimal(10)
    return {
        "years": sorted({y for _, y in sections}),
        "rent_raw": rent_backtest(sections, municipalities, growth_adjusted=False),
        "rent_growth_adjusted": rent_backtest(sections, municipalities, growth_adjusted=True),
        "rent_by_size_k10": by_size(rent_cases(sections, municipalities, chosen, True)),
        "rent_by_size_k0": by_size(rent_cases(sections, municipalities, Decimal(0), True)),
        "rent_raw_2y": rent_backtest(sections, municipalities, growth_adjusted=False,
                                     grid=(Decimal(0), chosen), horizon=2),
        "bias_raw_1y_k0": signed_bias(rent_cases(sections, municipalities, Decimal(0), False)),
        "bias_raw_2y_k0": signed_bias(rent_cases(sections, municipalities, Decimal(0), False,
                                                 horizon=2)),
        "bias_raw_2y_k0_recent": signed_bias(
            rent_cases(_since(sections, 2021), municipalities, Decimal(0), False, horizon=2)),
        "bias_cpi_2y": signed_bias(cpi_updated_cases(sections, monthly_annual_means(cpi), 2)),
        "bias_cpi_2y_recent": signed_bias(cpi_updated_cases(
            sections, monthly_annual_means(cpi), 2, since=2021)),
        "rent_cpi_2y_recent": errors((c.predicted, c.actual) for c in cpi_updated_cases(
            sections, monthly_annual_means(cpi), 2, since=2021)),
        "convergence": convergence_by_period(municipalities, provinces, province),
        "index_update": index_backtest(appraisal, index, region),
        "ratio_previous_year": ratio_backtest(appraisal, municipalities),
    }


def main() -> int:
    from housefinder.db.migrate import database_url

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--province", default="28")
    parser.add_argument("--region", default="13")
    args = parser.parse_args()
    result = run(database_url(), args.province, args.region)
    print(f"Años del SERPAVI: {result['years']}")
    for name in ("rent_raw", "rent_growth_adjusted", "rent_by_size_k10", "rent_by_size_k0",
                 "rent_raw_2y"):
        print(f"\n{name}")
        for key, err in result[name].items():  # type: ignore[union-attr]
            print(f"  {key:>10}: n={err.count:6d}  MdAPE={err.mdape:.2%}  "
                  f"MAE={err.mae:.2f}  ±10%={err.within_10:.1%}")
    for name in ("bias_raw_1y_k0", "bias_raw_2y_k0", "bias_raw_2y_k0_recent", "bias_cpi_2y",
                 "bias_cpi_2y_recent"):
        print(f"\n{name}: {result[name]:.2%}")  # type: ignore[str-format]
    pooled, by_year = result["convergence"]  # type: ignore[misc]
    print(f"\nconvergencia municipal (b a 3 años, sin constante): global {pooled}; por año "
          + ", ".join(f"{y}: {b}" for y, b in by_year.items()))
    for name in ("rent_cpi_2y_recent", "index_update", "ratio_previous_year"):
        err = result[name]
        print(f"\n{name}: n={err.count}  MdAPE={err.mdape:.2%}  MAE={err.mae:.0f}  "  # type: ignore[union-attr]
              f"±10%={err.within_10:.1%}")  # type: ignore[union-attr]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
