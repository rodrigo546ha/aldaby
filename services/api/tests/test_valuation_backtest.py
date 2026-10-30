"""Backtesting de la valoración (F5.6) con datos sintéticos de errores conocidos."""

from decimal import Decimal

from housefinder.db.references import RentRow
from housefinder.valuation.backtest import (
    by_size,
    errors,
    index_backtest,
    ratio_backtest,
    rent_backtest,
    rent_cases,
)

D = Decimal


def row(level, code, year, n, median):
    return RentRow(level, code, year, n, median - 2, median, median + 2)


def test_errores():
    # |11 − 10| / 10 = 10 %; |8 − 10| / 10 = 20 %; |30 − 30| = 0 → mediana 10 %, MAE (1+2+0)/3 = 1
    err = errors([(D(11), D(10)), (D(8), D(10)), (D(30), D(30)), (D(5), D(0))])
    assert err.count == 3
    assert err.mdape == D("0.1")
    assert err.mae == D(1)
    assert err.within_10 == D(2) / D(3)


# Sección de 30 alquileres a 18 €/m² en 2023 y 20 en 2024; municipio a 12 y 13,2 (+10 %).
SECTIONS = {("2899701001", 2023): row("seccion", "2899701001", 2023, 30, D(18)),
            ("2899701001", 2024): row("seccion", "2899701001", 2024, 30, D(20))}
MUNICIPALITIES = {("28997", 2023): row("municipio", "28997", 2023, 5000, D(12)),
                  ("28997", 2024): row("municipio", "28997", 2024, 5000, D("13.2"))}


def test_renta_de_t_contra_la_de_t_mas_1():
    raw = rent_backtest(SECTIONS, MUNICIPALITIES, growth_adjusted=False,
                        grid=(D(0), D(10), None))
    # k = 0: 18 frente a 20 → 10 %. k = 10: 0,75·18 + 0,25·12 = 16,5 → 17,5 %. Municipio: 12 → 40 %
    assert raw["0"].mdape == D("0.1")
    assert raw["10"].mdape == D("0.175")
    assert raw["municipio"].mdape == D("0.4")
    adjusted = rent_backtest(SECTIONS, MUNICIPALITIES, growth_adjusted=True, grid=(D(0),))
    # 18 × 13,2 / 12 = 19,8 frente a 20 → 1 %
    assert adjusted["0"].mdape == D("0.01")


def test_por_tamano_de_la_seccion():
    groups = by_size(rent_cases(SECTIONS, MUNICIPALITIES, D(0), growth_adjusted=False))
    assert groups["30–99"].count == 1 and groups["10–29"].count == 0


def test_actualizacion_con_el_indice_y_relacion_del_ano_anterior():
    appraisal = {("28997", 2023, 0): D(3000), ("28997", 2024, 0): D(3300)}
    index = {("13", 2023, q): D(100) for q in range(1, 5)}
    index |= {("13", 2024, q): D(v) for q, v in zip(range(1, 5), (104, 108, 112, 116), strict=True)}
    # IPV medio 100 → 110: 3.000 × 1,1 = 3.300, sin error
    assert index_backtest(appraisal, index, "13").mdape == D(0)
    # relación 2023 = 3.000 / (12 × 12) = 20,833…; 2024: 13,2 × 12 × 20,833… = 3.300, sin error
    # (la relación no es exacta en decimal: queda un resto del orden de 1e-24)
    assert ratio_backtest(appraisal, MUNICIPALITIES).mdape < D("1e-12")


def test_horizonte_y_sesgo():
    from housefinder.valuation.backtest import signed_bias

    sections = dict(SECTIONS)
    sections[("2899701001", 2025)] = row("seccion", "2899701001", 2025, 30, D("22.5"))
    # k = 0, dos años: 18 frente a 22,5 → −20 %, el modelo se queda corto
    cases = rent_cases(sections, MUNICIPALITIES, D(0), growth_adjusted=False, horizon=2)
    assert [(c.predicted, c.actual) for c in cases] == [(D("18.00"), D("22.5"))]
    assert signed_bias(cases) == D("-0.2")


def test_renta_actualizada_con_el_ipc():
    from housefinder.valuation.backtest import cpi_updated_cases, monthly_annual_means

    monthly = {("13", 2023, m): D(100) for m in range(1, 13)}
    monthly |= {("13", 2024, m): D(110) for m in range(1, 13)}
    monthly[("13", 2025, 1)] = D(120)  # año incompleto: no cuenta
    annual = monthly_annual_means(monthly)
    assert annual == {2023: D(100), 2024: D(110)}
    # 18 × 110 / 100 = 19,8 frente a 20
    cases = cpi_updated_cases(SECTIONS, annual, horizon=1)
    assert [(c.predicted, c.actual) for c in cases] == [(D("19.8"), D(20))]
