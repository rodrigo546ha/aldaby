"""Motor de escenarios de revalorización (F5.5). Valores calculados a mano en los comentarios."""

from decimal import Decimal

import pytest

from housefinder.engines.appreciation import (
    percentile,
    relative_log_growth,
    scenario_bounds,
    scenario_rate,
    window_growths,
)

D = Decimal


def test_crecimiento_anual_de_las_ventanas():
    # 100 → 200 en 10 años: 2^(1/10) − 1 = 0,071773… → 0,0718; 100 → 100: 0
    points = [(2000, 1, D(100)), (2010, 1, D(200)), (2000, 2, D(100)), (2010, 2, D(100)),
              (2001, 1, D(150))]  # sin pareja a 10 años: no cuenta
    assert sorted(window_growths(points, 10)) == [D("0.0000"), D("0.0718")]


def test_percentil_con_interpolacion():
    # [1, 2, 3, 4]: posición 0,25 × 3 = 0,75 → 1 + 0,75 × (2 − 1) = 1,75; mediana 2,5
    values = [D(4), D(1), D(3), D(2)]
    assert percentile(values, D("0.25")) == D("1.75")
    assert percentile(values, D("0.5")) == D("2.5")
    with pytest.raises(ValueError):
        percentile([], D("0.5"))


def test_brecha_que_se_cierra_o_se_abre():
    # brecha −0,2 (municipio barato), b = −0,1, 6 años con pasos de 3: (0,9)² = 0,81
    # relativo = −0,2 × (0,81 − 1) = +0,038 (sube más que la comunidad)
    assert relative_log_growth(D("-0.2"), D("-0.1"), 6) == D("0.0380")
    # el mismo municipio si diverge (b = +0,1): −0,2 × (1,21 − 1) = −0,042
    assert relative_log_growth(D("-0.2"), D("0.1"), 6) == D("-0.0420")
    assert relative_log_growth(D("-0.2"), D("0"), 6) == D("0.0000")


def test_optimista_y_conservador_segun_la_brecha():
    # barato: converger (b < 0) es lo optimista; caro: lo optimista es divergir
    # (b optimista, b conservador)
    assert scenario_bounds(D("-0.2"), D("-0.03"), D("0.04")) == (D("-0.03"), D("0.04"))
    assert scenario_bounds(D("0.3"), D("-0.03"), D("0.04")) == (D("0.04"), D("-0.03"))


def test_tasa_del_escenario():
    # comunidad +2 %, relativo +0,05 en 10 años: 1,02 × e^(0,005) − 1 = 1,02 × 1,0050125 − 1
    # = 0,0251128 → 0,0251
    assert scenario_rate(D("0.02"), D("0.05"), 10) == D("0.0251")
    assert scenario_rate(D("0.02"), D("0"), 10) == D("0.0200")
