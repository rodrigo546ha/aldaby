"""Motor de valoración (F5.3, F5.4, ADR-0018). Valores calculados a mano en los comentarios."""

from decimal import Decimal

import pytest

from housefinder.engines.valuation import (
    RentStats,
    index_update,
    price_per_m2,
    price_to_rent_ratio,
    rent_for_area,
    scale,
    shrink,
)

D = Decimal
SECTION = RentStats(n=30, p25=D("14"), median=D("18"), p75=D("22"))
MUNICIPALITY = RentStats(n=5000, p25=D("10"), median=D("12"), p75=D("15"))


def test_contraccion_hacia_el_municipio():
    # w = n / (n + k) = 30 / (30 + 10) = 0,75
    # mediana = 0,75·18 + 0,25·12 = 13,5 + 3 = 16,5
    # P25 = 0,75·14 + 0,25·10 = 10,5 + 2,5 = 13; P75 = 0,75·22 + 0,25·15 = 16,5 + 3,75 = 20,25
    shrunk = shrink(SECTION, MUNICIPALITY, k=D("10"))
    assert shrunk.weight == D("0.75")
    assert (shrunk.p25, shrunk.median, shrunk.p75) == (D("13.00"), D("16.50"), D("20.25"))


def test_sin_k_o_sin_recuento_no_se_contrae():
    assert shrink(SECTION, MUNICIPALITY, k=D("0")).median == D("18.00")
    unknown = RentStats(n=None, p25=D("14"), median=D("18"), p75=D("22"))
    assert shrink(unknown, MUNICIPALITY, k=D("10")).weight == D("1")


def test_renta_de_un_piso_de_80_m2():
    # 16,5 €/m² × 80 = 1.320 €/mes; rango 13 × 80 = 1.040 y 20,25 × 80 = 1.620
    rent = rent_for_area(shrink(SECTION, MUNICIPALITY, k=D("10")), D("80"))
    assert (rent.low, rent.value, rent.high) == (D("1040.00"), D("1320.00"), D("1620.00"))


def test_relacion_precio_renta_del_municipio():
    # 4.200 €/m² / (14 €/m² mes × 12) = 4.200 / 168 = 25 años de renta
    assert price_to_rent_ratio(appraisal_m2=D("4200"), rent_m2_month=D("14")) == D("25.0000")
    with pytest.raises(ValueError):
        price_to_rent_ratio(appraisal_m2=D("4200"), rent_m2_month=D("0"))


def test_precio_por_m2_desde_la_renta():
    # 16,5 × 12 × 25 = 4.950 €/m²; 13 × 12 × 25 = 3.900; 20,25 × 12 × 25 = 6.075
    price = price_per_m2(shrink(SECTION, MUNICIPALITY, k=D("10")), ratio=D("25"))
    assert (price.low, price.value, price.high) == (D("3900.00"), D("4950.00"), D("6075.00"))


def test_actualizacion_con_el_indice():
    # 4.950 × 110 / 100 = 5.445
    assert index_update(D("4950"), index_from=D("100"), index_to=D("110")) == D("5445.00")
    with pytest.raises(ValueError):
        index_update(D("4950"), index_from=D("0"), index_to=D("110"))


def test_renta_llevada_con_un_indice():
    # 13 / 16,5 / 20,25 × 110 / 100 = 14,30 / 18,15 / 22,275 → 22,28 (redondeo comercial)
    scaled = scale(shrink(SECTION, MUNICIPALITY, k=D("10")), D("100"), D("110"))
    assert (scaled.p25, scaled.median, scaled.p75, scaled.weight) == (
        D("14.30"), D("18.15"), D("22.28"), D("0.75"))
