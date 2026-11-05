from dataclasses import replace
from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines.cashflow import (
    InvestmentInputs,
    PendingExcess,
    RentalAssumptions,
    TaxParams,
    compute_cashflow,
)
from housefinder.engines.irr import investment_irr, irr, sale_base, yearly_cashflows
from housefinder.engines.mortgage import amortization_schedule
from housefinder.engines.valuation import Range

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
    interest_repair_carryforward_years=4,
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


# --- Valor de partida de la venta (ADR-0059) -------------------------------------------------

VALORACION = SourceRef("dataset", "valoracion-de-prueba")


@pytest.mark.parametrize("price, expected", [
    (Decimal(150000), Decimal(200000)),  # por debajo del P25: el P25
    (Decimal(230000), Decimal(230000)),  # dentro del rango: el precio pagado
    (Decimal(300000), Decimal(260000)),  # por encima del P75: el P75
])
def test_valor_de_partida_acotado_al_rango(price, expected):
    assert sale_base(price, Range(Decimal(200000), Decimal(230000), Decimal(260000))) == expected


def test_comprar_por_debajo_del_valor_cuenta_en_la_venta():
    # Calculado a mano (TIR por Newton, independiente de la bisección):
    #   precio 150.000, rango estimado 200.000–260.000 → la venta parte del P25, 200.000
    #   venta año 10: 200.000 × 1,02¹⁰ = 243.798,88; gastos 5 % = 12.189,94
    #   ganancia: 243.798,88 − 12.189,94 − (165.000 − 18.000) = 84.608,94 (resta el precio pagado)
    #   impuesto: 84.608,94 × 0,19 = 16.075,70 → neto de la venta 215.533,24
    #   flujos: −165.000; 7.390,45 × 9; 7.390,45 + 215.533,24 → TIR 0,067247… → 0,0672
    res = _irr(market_value=Range(Decimal(200000), Decimal(230000), Decimal(260000)),
               market_value_sources=(VALORACION,))
    assert res.sale_base.value == Decimal("200000.00")
    assert res.sale_price.value == Decimal("243798.88")
    assert res.net_sale_proceeds.value == Decimal("215533.24")
    assert res.irr.value == Decimal("0.0672")
    assert VALORACION in res.sale_price.sources and VALORACION in res.irr.sources
    assert "P25" in res.sale_base.formula


def test_comprar_por_encima_del_valor_no_se_revaloriza():
    # 150.000 con el rango 100.000–120.000: la venta parte del P75 → 120.000 × 1,02¹⁰
    res = _irr(market_value=Range(Decimal(100000), Decimal(110000), Decimal(120000)))
    assert res.sale_price.value == Decimal("146279.33")
    assert res.irr.value < _irr().irr.value


def test_sin_valor_de_mercado_parte_del_precio():
    res = _irr()
    assert res.sale_base.value == Decimal(150000)
    assert res.sale_price.value == Decimal("182849.16")


def test_cita_la_revalorizacion_y_la_venta():
    res = _irr()
    assert {OFERTA, REGLA, REVALORIZACION, VENTA} <= set(res.irr.sources)
    assert res.irr.provisional



def test_el_exceso_de_intereses_pasa_al_ano_siguiente():
    # Préstamo de 105.000 al 20 % a 2 años (intereses del cuadro: 16.818,45 y 6.438,99).
    # Tope de intereses + reparación = renta cobrada = 10.260; reparación = 513 al año.
    #   Año 1: 16.818,45 + 513 = 17.331,45 → exceso 7.071,45 (cuatro años por delante)
    #   Año 2: el arrastre ocupa 7.071,45 del tope; quedan 3.188,55 para los 6.951,99 del año
    #          → nuevo exceso 3.763,44
    #   Impuesto del año 2: 0 con el arrastre; sin él, (10.260 − 1.370 − 6.951,99 − 1.800)
    #          × 0,5 × 0,30 = 20,70
    caro = replace(INV, loan=Decimal(105000))
    anos = yearly_cashflows(caro, RENT, TAX, Decimal("0.20"), 2, 2)
    assert anos[0].pending_excess == (PendingExcess(Decimal("7071.45"), 4),)
    assert anos[1].pending_excess == (PendingExcess(Decimal("3763.44"), 4),)
    assert anos[1].annual_tax.value == Decimal("0.00")

    rows = amortization_schedule(Decimal(105000), Decimal("0.20"), 2)
    ano2 = replace(
        caro,
        monthly_mortgage_payment=sum(r.payment for r in rows[12:]) / 12,
        first_year_interest=sum(r.interest for r in rows[12:]),
    )
    assert compute_cashflow(ano2, RENT, TAX).annual_tax.value == Decimal("20.70")


# --- Subida anual de la renta (ADR-0060) ------------------------------------------------------


def test_la_renta_sube_desde_el_segundo_ano():
    # Calculado a mano, al contado, con la renta subiendo un 2 % al año:
    #   año 2: renta 918,00; cobrada 918 × 12 × 0,95 = 10.465,20; mantenimiento 5 % = 523,26
    #          operativo 10.465,20 − 1.370 − 523,26 = 8.571,94
    #          impuesto (10.465,20 − 1.370 − 523,26 − 1.800) × 0,5 × 0,30 = 1.015,79
    #   año 3: renta 900 × 1,02² = 936,36 → operativo 8.770,78
    anos = yearly_cashflows(INV, RENT, TAX, Decimal("0.03"), 25, 3, rent_growth=Decimal("0.02"))
    assert anos[0].annual_operating_cashflow.value == Decimal("8377.00")  # el año 1 no cambia
    assert anos[1].annual_operating_cashflow.value == Decimal("8571.94")
    assert anos[1].annual_tax.value == Decimal("1015.79")
    assert anos[2].annual_operating_cashflow.value == Decimal("8770.78")


def test_tir_con_la_renta_subiendo_valor_conocido():
    # Mismos flujos que test_compra_al_contado_valor_conocido, con la renta subiendo un 2 % desde
    # el año 2 (7.556,15 el año 2, 7.725,16 el 3…) y la misma venta neta (168.632,43):
    # TIR por Newton 0,050860… → 0,0509 (sin subida, 0,0466)
    subida = SourceRef("dataset", "ipc-alquiler-de-prueba")
    res = _irr(rent_growth=Decimal("0.02"), rent_growth_sources=(subida,))
    assert res.net_sale_proceeds.value == Decimal("168632.43")
    assert res.irr.value == Decimal("0.0509")
    assert subida in res.irr.sources
    assert "renta" in res.irr.formula


def test_sin_subida_la_renta_es_constante():
    assert _irr(rent_growth=Decimal(0)).irr.value == _irr().irr.value == Decimal("0.0466")
