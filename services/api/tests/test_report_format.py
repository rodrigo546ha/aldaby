"""Formato de las cifras del PDF (ADR-0026): español y sin float."""

from decimal import Decimal

import pytest

from housefinder.reports.format import format_value, number, percent

D = Decimal


@pytest.mark.parametrize(("value", "expected"), [
    ("1234567.891", "1.234.567,89"), ("0.5", "0,50"), ("-36.66", "−36,66"), ("999", "999,00"),
])
def test_numero_con_puntos_de_miles(value, expected):
    assert number(D(value)) == expected


def test_porcentaje_y_unidades():
    assert percent(D("0.0475")) == "4,75 %"
    assert percent(D("0.03")) == "3 %"
    assert format_value(D("672.43"), "EUR/mes") == "672,43 € al mes"
    assert format_value(D("30"), "años") == "30 años"
    assert format_value(D("235000"), "EUR") == "235.000,00 €"
