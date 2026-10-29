"""Formas de cálculo de gastos y tributos de compra y venta (engines/taxes.py).

Valores conocidos calculados a mano tramo a tramo con los importes del arancel
(RD 1426/1989 y RD 1427/1989, anexo I, número 2), el art. 32 y 37 del DL 1/2010 de Madrid
y el art. 107 del TRLRHL. Los importes del test reproducen los de data/rules a propósito:
aquí se prueba la fórmula, no la regla.
"""

from decimal import Decimal

import pytest

from housefinder.engines.taxes import (
    FeeBand,
    FeeSchedule,
    MunicipalGainsTax,
    RateBand,
    banded_tax,
    municipal_gains_tax,
    scheduled_fee,
)

D = Decimal

NOTARY = FeeSchedule(
    base_fee=D("90.151816"),
    bands=(
        FeeBand(D("6010.12"), D("0.0045")),
        FeeBand(D("30050.61"), D("0.0015")),
        FeeBand(D("60101.21"), D("0.001")),
        FeeBand(D("150253.03"), D("0.0005")),
        FeeBand(D("601012.10"), D("0.0003")),
    ),
    max_base=D("6010121.04"),
    rebate=D("0.05"),
)
REGISTRY = FeeSchedule(
    base_fee=D("24.040484"),
    bands=(
        FeeBand(D("6010.12"), D("0.00175")),
        FeeBand(D("30050.61"), D("0.00125")),
        FeeBand(D("60101.21"), D("0.00075")),
        FeeBand(D("150253.03"), D("0.0003")),
        FeeBand(D("601012.10"), D("0.0002")),
    ),
    min_fee=D("24.040484"),
    max_fee=D("2181.673939"),
    rebate=D("0.05"),
)
AJD = (
    RateBand(D(120000), D("0.004")),
    RateBand(D(180000), D("0.005")),
    RateBand(None, D("0.0075")),
)


def test_arancel_notarial_200000():
    # 90,15 + 24.040,49 × 4,5‰ + 30.050,60 × 1,5‰ + 90.151,82 × 1‰ + 49.746,97 × 0,5‰
    # = 358,4352; con la rebaja del 5 %, 340,5135.
    assert scheduled_fee(D(200000), NOTARY) == D("340.51")


def test_arancel_notarial_primer_tramo():
    assert scheduled_fee(D(5000), NOTARY) == D("85.64")  # 90,151816 × 0,95


def test_arancel_notarial_por_encima_del_maximo_es_pacto_libre():
    with pytest.raises(ValueError, match="pacto libre"):
        scheduled_fee(D(7000000), NOTARY)


def test_arancel_registral_200000():
    # 24,04 + 42,07 + 37,56 + 67,61 + 14,92 = 186,2125; × 0,95 = 176,9019.
    assert scheduled_fee(D(200000), REGISTRY) == D("176.90")


def test_arancel_registral_con_maximo():
    # A 10 M€ la escala da 2.186,31: se limita a 2.181,67 y después la rebaja.
    assert scheduled_fee(D(10000000), REGISTRY) == D("2072.59")


def test_arancel_registral_minimo():
    assert scheduled_fee(D(0), REGISTRY) == D("22.84")  # 24,040484 × 0,95


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (100000, "400.00"),  # 0,4 %
        (120000, "480.00"),
        (120001, "481.00"),  # 0,5 % daría 600,01: se limita a 480 + 1
        (120100, "580.00"),
        (150000, "750.00"),  # 0,5 % ya es menor que el límite
        (180000, "900.00"),
        (180001, "901.00"),
        (181000, "1357.50"),
        (300000, "2250.00"),  # 0,75 %
    ],
)
def test_ajd_por_bandas_con_salto_limitado(value, expected):
    assert banded_tax(D(value), AJD, cap_jumps=True) == D(expected)


def test_ajd_sin_limitar_el_salto():
    assert banded_tax(D(120001), AJD, cap_jumps=False) == D("600.01")


PLUSVALIA = MunicipalGainsTax(
    land_value=D(60000), coefficient=D("0.12"), rate=D("0.29"), land_share=D("0.4")
)


def test_plusvalia_base_objetiva():
    # Incremento real (243.798,88 − 200.000) × 0,4 = 17.519,55 > 60.000 × 0,12 = 7.200.
    tax, method = municipal_gains_tax(PLUSVALIA, D(200000), D("243798.88"))
    assert tax == D("2088.00")  # 7.200 × 29 %
    assert "objetiva" in method


def test_plusvalia_incremento_real_menor():
    tax, method = municipal_gains_tax(PLUSVALIA, D(200000), D(205000))
    assert tax == D("580.00")  # 5.000 × 0,4 × 29 %
    assert "real" in method


def test_plusvalia_sin_ganancia_no_sujeta():
    tax, method = municipal_gains_tax(PLUSVALIA, D(200000), D(190000))
    assert tax == D("0.00")
    assert "no sujeta" in method
