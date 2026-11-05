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


def test_convergencia_por_periodo():
    from housefinder.valuation.backtest import convergence_by_period

    # Provincia 10 → 11 (+log 1,1). Municipio barato a 8 (brecha log 0,8) sube a 9,24: relativo
    # log(9,24/8) − log(1,1) = log(1,05) ≈ 0,04879; b = 0,04879 / log(0,8) ≈ −0,2186
    municipalities = {("28001", 2020): row("municipio", "28001", 2020, 50, D(8)),
                      ("28001", 2023): row("municipio", "28001", 2023, 50, D("9.24"))}
    provinces = {("28", 2020): row("provincia", "28", 2020, 9999, D(10)),
                 ("28", 2023): row("provincia", "28", 2023, 9999, D(11))}
    pooled, by_year = convergence_by_period(municipalities, provinces, "28")
    assert pooled == D("-0.2186") and by_year == {2020: D("-0.2186")}


# --- Convergencia municipal por comunidad (F5.5) ---------------------------------------------


def test_cada_municipio_frente_a_su_provincia():
    # Almería (04) a 10 → 11 €/m² y Granada (18) a 20 → 20 de 2011 a 2014. 04001 de 5 a 6,05 y
    # 18001 de 40 a 44: los dos crecen ln 1,1 más que su provincia, con brechas ln 0,5 y ln 2.
    # Frente a la provincia equivocada, la de 18001 sería ln 4.
    import math

    from housefinder.valuation.backtest import convergence_pairs

    municipalities = {("04001", 2011): row("municipio", "04001", 2011, 50, D(5)),
                      ("04001", 2014): row("municipio", "04001", 2014, 50, D("6.05")),
                      ("18001", 2011): row("municipio", "18001", 2011, 50, D(40)),
                      ("18001", 2014): row("municipio", "18001", 2014, 50, D(44))}
    provinces = {("04", 2011): row("provincia", "04", 2011, 900, D(10)),
                 ("04", 2014): row("provincia", "04", 2014, 900, D(11)),
                 ("18", 2011): row("provincia", "18", 2011, 900, D(20)),
                 ("18", 2014): row("provincia", "18", 2014, 900, D(20))}
    pairs = sorted(convergence_pairs(municipalities, provinces)[2011])
    assert [round(g, 6) for g, _ in pairs] == [round(math.log(0.5), 6), round(math.log(2), 6)]
    assert all(abs(r - math.log(1.1)) < 1e-9 for _, r in pairs)


def test_convergencia_de_una_comunidad():
    # Un caso por año con brecha 1 y crecimiento relativo (año − 2016) / 100: el b de cada año es
    # ese crecimiento, de −0,05 (2011) a +0,05 (2021).
    #   global: media 0; P25 y P75 de los 11 (interpolación): −0,025 y +0,025
    #   F5.5: ajuste 2018–2019 → 0,025; prueba 2020–2021: cero (0,04 + 0,05) / 2 = 0,045,
    #         con b (0,015 + 0,025) / 2 = 0,02
    #   base: b de 2011–2017 = −0,02; prueba 2018–2021: cero 0,035, con b 0,055
    from housefinder.valuation.backtest import region_convergence

    pairs = {year: [(1.0, (year - 2016) / 100)] for year in range(2011, 2022)}
    c = region_convergence("01", pairs, municipalities=1)
    assert c.pooled == D(0) and c.cases == 11
    assert (c.low, c.high) == (D("-0.0250"), D("0.0250"))
    assert (c.fitted_b, c.zero_error, c.fitted_error) == (D("0.025"), D("0.045"), D("0.02"))
    assert (c.early_b, c.early_zero_error, c.early_error) == (D("-0.02"), D("0.035"), D("0.055"))
    # Con menos de ocho periodos no hay percentiles
    assert region_convergence("01", {2020: [(1.0, 0.01)]}).low is None
