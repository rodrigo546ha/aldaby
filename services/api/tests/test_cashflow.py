from decimal import Decimal

from housefinder.core.figures import SourceRef
from housefinder.engines.cashflow import (
    InvestmentInputs,
    RentalAssumptions,
    TaxParams,
    compute_cashflow,
)

OFERTA = SourceRef("user_input", "oferta-de-prueba")
RENTA = SourceRef("assumption", "renta-de-prueba", provisional=True)
REGLA = SourceRef("rule", "regla-de-prueba")

INV = InvestmentInputs(
    price=Decimal(150000),
    purchase_costs=Decimal(15000),
    renovation=Decimal(0),
    loan=Decimal(105000),
    monthly_mortgage_payment=Decimal("442.68"),
    first_year_interest=Decimal(3100),
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
# Valores de prueba, NO normativa real: la real llega del motor de normativa.
TAX = TaxParams(
    marginal_rate=Decimal("0.30"),
    rental_income_reduction=Decimal("0.50"),
    depreciation_rate=Decimal("0.03"),
    sources=(REGLA,),
)


def test_rentabilidad_bruta_en_tanto_por_uno():
    # 900 × 12 / 150.000 = 0,072
    res = compute_cashflow(INV, RENT, TAX)
    assert res.gross_yield.value == Decimal("0.0720")
    assert res.gross_yield.unit == "ratio"


def test_cash_on_cash_valor_conocido():
    # Calculado a mano:
    #   renta cobrada      = 900 × 12 × 0,95                      = 10.260,00
    #   gastos explotación = 720 + 300 + 350 + 0 + 513            =  1.883,00
    #   cash flow operativo= 10.260 − 1.883 − 442,68 × 12         =  3.064,84
    #   base imponible     = (10.260 − 1.883 − 3.100 − 1.800) × 0,5 = 1.738,50
    #   impuesto           = 1.738,50 × 0,30                       =    521,55
    #   cash-on-cash       = (3.064,84 − 521,55) / 60.000          = 0,042388 → 0,0424
    res = compute_cashflow(INV, RENT, TAX)
    assert res.annual_tax.value == Decimal("521.55")
    assert res.monthly_cashflow_after_tax.value == Decimal("211.94")
    assert res.cash_on_cash.value == Decimal("0.0424")
    assert res.cash_on_cash.unit == "ratio"


def test_dinero_aportado():
    res = compute_cashflow(INV, RENT, TAX)
    assert res.cash_invested.value == Decimal("60000.00")


def test_cifras_fiscales_citan_su_regla():
    res = compute_cashflow(INV, RENT, TAX)
    assert REGLA in res.annual_tax.sources
    assert REGLA in res.monthly_cashflow_after_tax.sources
    assert TAX.rule_ids == ("regla-de-prueba",)


def test_las_fuentes_de_las_entradas_se_propagan():
    res = compute_cashflow(INV, RENT, TAX)
    assert set(res.monthly_cashflow_after_tax.sources) == {OFERTA, RENTA, REGLA}
    assert res.monthly_cashflow_after_tax.provisional  # la renta es un supuesto provisional
    assert res.cash_invested.sources == (OFERTA,)
    assert not res.cash_invested.provisional


def test_claves_estables():
    res = compute_cashflow(INV, RENT, TAX)
    assert res.monthly_cashflow_after_tax.key == "cashflow.monthly_after_tax"


def test_gestion_pasiva_reduce_el_cash_flow():
    activa = compute_cashflow(INV, RENT, TAX)
    pasiva_rent = RentalAssumptions(**{**RENT.__dict__, "management_fee_rate": Decimal("0.08")})
    pasiva = compute_cashflow(INV, pasiva_rent, TAX)
    assert pasiva.monthly_cashflow_after_tax.value < activa.monthly_cashflow_after_tax.value


def test_sin_impuesto_si_rendimiento_negativo():
    cara = InvestmentInputs(**{**INV.__dict__, "first_year_interest": Decimal(20000)})
    res = compute_cashflow(cara, RENT, TAX)
    assert res.annual_tax.value == Decimal("0.00")
