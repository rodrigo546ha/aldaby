from dataclasses import replace
from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines.cashflow import InvestmentInputs, RentalAssumptions, TaxParams
from housefinder.engines.term import recommended_term

OFERTA = SourceRef("user_input", "oferta-de-prueba")
RENTA = SourceRef("assumption", "renta-de-prueba", provisional=True)
REGLA = SourceRef("rule", "regla-de-prueba")
TIPO = SourceRef("user_input", "tipo-de-interes")
CRITERIOS = SourceRef("param", "criterios-de-prueba")

# Misma inversión que tests/test_cashflow.py. La cuota y los intereses del primer año
# se recalculan para cada plazo, así que aquí su valor no importa.
INV = InvestmentInputs(
    price=Decimal(150000),
    purchase_costs=Decimal(15000),
    renovation=Decimal(0),
    loan=Decimal(105000),
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
    sources=(RENTA,),
)
# Valores de prueba, NO normativa real.
TAX = TaxParams(
    marginal_rate=Decimal("0.30"),
    rental_income_reduction=Decimal("0.50"),
    depreciation_rate=Decimal("0.03"),
    interest_repair_carryforward_years=4,
    sources=(REGLA,),
)


def _term(**overrides):
    args = dict(
        investment=INV,
        rent=RENT,
        tax=TAX,
        annual_rate=Decimal("0.03"),
        rate_shock=Decimal("0.02"),
        max_years=30,
        rate_sources=(TIPO,),
        max_years_sources=(CRITERIOS,),
    )
    args.update(overrides)
    return recommended_term(**args)


def test_plazo_recomendado_valor_conocido():
    # Calculado a mano con la fórmula francesa cerrada, 105.000 € al 3 % + 2 de estrés (5 %):
    #   cash flow mensual = (8.377 − 12 × cuota − 0,15 × (6.577 − intereses del año 1)) / 12
    #   20 años: cuota 692,95, intereses 5.178,77 → −12,34 €/mes (no vale)
    #   21 años: cuota 673,80, intereses 5.184,12 →  +6,87 €/mes → plazo recomendado
    # Los intereses del año 1 son la suma de los 12 intereses mensuales redondeados a
    # céntimos, como en el cuadro del banco. Con la suma sin redondear el impuesto a 20 años
    # cae justo en medio céntimo y el cash flow saldría −12,35.
    res = _term()
    assert res.feasible
    assert res.years.value == Decimal(21)
    assert res.stressed_monthly_payment.value == Decimal("673.80")
    assert res.stressed_monthly_cashflow.value == Decimal("6.87")


def test_cash_flow_minimo_alarga_el_plazo():
    # 22 años: +24,19 €/mes, primer plazo que supera 20 €/mes.
    res = _term(min_monthly_cashflow=Decimal(20))
    assert res.years.value == Decimal(22)


def test_sin_estres_el_plazo_no_es_mas_largo():
    con_estres = _term()
    sin_estres = _term(rate_shock=Decimal(0))
    assert sin_estres.years.value <= con_estres.years.value


def test_renta_alta_da_el_plazo_minimo():
    res = _term(rent=replace(RENT, monthly_rent=Decimal(20000)))
    assert res.feasible
    assert res.years.value == Decimal(1)


def test_ningun_plazo_vale_se_dice_explicitamente():
    res = _term(rent=replace(RENT, monthly_rent=Decimal(300)))
    assert not res.feasible
    # Devuelve el mejor caso evaluado (el plazo máximo) para mostrar cuánto falta.
    assert res.years.value == Decimal(30)
    assert res.stressed_monthly_cashflow.value < 0


def test_el_plazo_maximo_limita_la_busqueda():
    res = _term(max_years=20)
    assert not res.feasible
    assert res.years.value == Decimal(20)
    assert res.stressed_monthly_cashflow.value == Decimal("-12.34")


def test_plazo_maximo_invalido():
    with pytest.raises(ValueError):
        _term(max_years=0)


def test_cita_todas_sus_fuentes_y_el_escenario():
    res = _term()
    sources = set(res.years.sources)
    assert {OFERTA, RENTA, REGLA, TIPO, CRITERIOS} <= sources
    assert SourceRef("assumption", "escenario-estres") in sources
    assert res.years.provisional  # la renta de prueba es provisional
    assert res.years.key == "term.recommended_years"
