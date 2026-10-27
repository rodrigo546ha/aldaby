from dataclasses import replace
from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines.cashflow import InvestmentInputs, RentalAssumptions, TaxParams
from housefinder.engines.irr import investment_irr, irr

OFERTA = SourceRef("user_input", "oferta-de-prueba")
REGLA = SourceRef("rule", "regla-de-prueba")
REVALORIZACION = SourceRef("assumption", "revalorizacion-de-prueba", provisional=True)
VENTA = SourceRef("assumption", "venta-de-prueba", provisional=True)


# --- irr() ------------------------------------------------------------------


def test_tir_un_periodo():
    assert irr([Decimal(-100), Decimal(110)]) == Decimal("0.1000")


def test_tir_solo_al_final():
    # 1.000 × 1,1³ = 1.331
    assert irr([Decimal(-1000), Decimal(0), Decimal(0), Decimal(1331)]) == Decimal("0.1000")


def test_tir_valor_conocido_dos_periodos():
    # 60x² + 60x − 100 = 0 con x = 1/(1+r) → r = 0,130662… → 0,1307
    assert irr([Decimal(-100), Decimal(60), Decimal(60)]) == Decimal("0.1307")


def test_tir_negativa():
    # Se recupera la mitad en un año: −50 %.
    assert irr([Decimal(-100), Decimal(50)]) == Decimal("-0.5000")


def test_sin_cambio_de_signo_no_hay_tir():
    assert irr([Decimal(-100), Decimal(-10), Decimal(0)]) is None


# --- investment_irr() -------------------------------------------------------

# Misma inversión que tests/test_cashflow.py, comprada al contado (sin préstamo).
INV = InvestmentInputs(
    price=Decimal(150000),
    purchase_costs=Decimal(15000),
    renovation=Decimal(0),
    loan=Decimal(0),
    monthly_mortgage_payment=Decimal(0),
    first_year_interest=Decimal(0),
    construction_value=Decimal(60000),
    sources=(OFERTA,),
)
RENT = RentalAssumptions(
    monthly_rent=Decimal(900),
    vacancy_rate=Decimal("0.05"),
    community_fees_monthly=Decimal(60),
    ibi_annual=Decimal(300),
    insurance_annual=Decimal(350),
    management_fee_rate=Decimal(0),
    maintenance_reserve_rate=Decimal("0.05"),
)
# Valores de prueba, NO normativa real (tampoco el 0,19 de plusvalía de abajo).
TAX = TaxParams(
    marginal_rate=Decimal("0.30"),
    rental_income_reduction=Decimal("0.50"),
    depreciation_rate=Decimal("0.03"),
    sources=(REGLA,),
)


def _irr(**overrides):
    args = dict(
        investment=INV,
        rent=RENT,
        tax=TAX,
        annual_rate=Decimal("0.03"),
        loan_years=25,
        appreciation_rate=Decimal("0.02"),
        sale_cost_rate=Decimal("0.05"),
        capital_gains_tax_rate=Decimal("0.19"),
        appreciation_sources=(REVALORIZACION,),
        sale_sources=(VENTA,),
    )
    args.update(overrides)
    return investment_irr(**args)


def test_compra_al_contado_valor_conocido():
    # Calculado a mano (y la TIR por Newton, método independiente de la bisección):
    #   flujo anual: 8.377,00 − impuesto 0,15 × (8.377 − 1.800) = 8.377,00 − 986,55 = 7.390,45
    #   venta año 10: 150.000 × 1,02¹⁰ = 182.849,16; gastos 5 % = 9.142,46
    #   ganancia: 182.849,16 − 9.142,46 − (165.000 − 10 × 1.800) = 26.706,70
    #   impuesto: 26.706,70 × 0,19 = 5.074,27 → neto de la venta 168.632,43
    #   flujos: −165.000; 7.390,45 × 9; 7.390,45 + 168.632,43 → TIR 0,046569… → 0,0466
    res = _irr()
    assert res.sale_price.value == Decimal("182849.16")
    assert res.net_sale_proceeds.value == Decimal("168632.43")
    assert res.irr is not None
    assert res.irr.value == Decimal("0.0466")
    assert res.irr.unit == "ratio"
    assert res.irr.key == "irr.rate"


def test_la_venta_descuenta_el_prestamo_pendiente():
    # Con préstamo, el neto de la venta resta el capital pendiente al año 10.
    con_prestamo = _irr(investment=replace(INV, loan=Decimal(105000)))
    contado = _irr()
    assert con_prestamo.net_sale_proceeds.value < contado.net_sale_proceeds.value
    assert con_prestamo.sale_price.value == contado.sale_price.value


def test_mas_revalorizacion_mas_tir():
    baja = _irr(appreciation_rate=Decimal(0))
    alta = _irr(appreciation_rate=Decimal("0.04"))
    assert baja.irr.value < alta.irr.value


def test_prestamo_que_termina_antes_del_horizonte():
    # Préstamo a 5 años: del año 6 al 10 no hay cuotas ni capital pendiente al vender.
    res = _irr(investment=replace(INV, loan=Decimal(105000)), loan_years=5)
    assert res.irr is not None
    contado = _irr()
    assert res.net_sale_proceeds.value == contado.net_sale_proceeds.value


def test_horizonte_configurable():
    assert _irr(horizon_years=5).irr.formula != _irr().irr.formula


def test_horizonte_invalido():
    with pytest.raises(ValueError):
        _irr(horizon_years=0)


def test_sin_tir_se_explica():
    # Renta nula y el inmueble pierde casi todo su valor: nunca se recupera lo invertido.
    res = _irr(
        rent=replace(RENT, monthly_rent=Decimal(0)),
        appreciation_rate=Decimal("-0.99"),
    )
    assert res.irr is None
    assert res.no_irr_reason


def test_cita_la_revalorizacion_y_la_venta():
    res = _irr()
    assert {OFERTA, REGLA, REVALORIZACION, VENTA} <= set(res.irr.sources)
    assert res.irr.provisional
