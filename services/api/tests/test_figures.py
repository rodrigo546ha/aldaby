from datetime import date
from decimal import Decimal

import pytest

from housefinder.core.figures import Figure, SourceRef, combine_sources, money, ratio

REGLA = SourceRef("rule", "madrid-itp-2026")
CRITERIO = SourceRef("param", "criterios-bancarios", provisional=True)


def test_money_redondeo_comercial():
    assert money("10.005") == Decimal("10.01")


def test_ratio_cuatro_decimales():
    # 0,072049 → 0,0720 (7,20 %)
    assert ratio(Decimal("0.072049")) == Decimal("0.0720")
    assert ratio(Decimal("0.07205")) == Decimal("0.0721")


def test_figura_sin_fuentes_provisionales_no_es_provisional():
    f = Figure("x.valor", Decimal(1), "EUR", "f", (REGLA,))
    assert not f.provisional


def test_una_fuente_provisional_contagia_la_figura():
    f = Figure("x.valor", Decimal(1), "EUR", "f", (REGLA, CRITERIO))
    assert f.provisional


def test_rango_valido():
    f = Figure("x.renta", Decimal(900), "EUR/mes", "f", low=Decimal(800), high=Decimal(1000))
    assert (f.low, f.high) == (Decimal(800), Decimal(1000))


def test_rango_incompleto_falla():
    with pytest.raises(ValueError):
        Figure("x.renta", Decimal(900), "EUR/mes", "f", low=Decimal(800))


def test_rango_que_no_contiene_el_valor_falla():
    with pytest.raises(ValueError):
        Figure("x.renta", Decimal(900), "EUR/mes", "f", low=Decimal(950), high=Decimal(1000))


def test_clave_obligatoria_con_dominio():
    with pytest.raises(ValueError):
        Figure("sin_dominio", Decimal(1), "EUR", "f")


def test_combinar_fuentes_sin_duplicados_y_en_orden():
    assert combine_sources((REGLA, CRITERIO), (CRITERIO,), (REGLA,)) == (REGLA, CRITERIO)


def test_serializacion():
    f = Figure(
        "x.renta",
        Decimal("900.00"),
        "EUR/mes",
        "f",
        (CRITERIO,),
        as_of=date(2026, 10, 27),
        low=Decimal("800.00"),
        high=Decimal("1000.00"),
    )
    assert f.to_dict() == {
        "key": "x.renta",
        "value": "900.00",
        "unit": "EUR/mes",
        "formula": "f",
        "sources": [{"kind": "param", "id": "criterios-bancarios", "provisional": True}],
        "provisional": True,
        "as_of": "2026-10-27",
        "low": "800.00",
        "high": "1000.00",
    }
