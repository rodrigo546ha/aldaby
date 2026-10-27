from decimal import Decimal

from housefinder.engines.cashflow import (
    InvestmentInputs,
    RentalAssumptions,
    TaxParams,
    compute_cashflow,
)

INV = InvestmentInputs(
    price=Decimal(150000),
    purchase_costs=Decimal(15000),
    renovation=Decimal(0),
    loan=Decimal(105000),
    monthly_mortgage_payment=Decimal("442.68"),
    first_year_interest=Decimal(3100),
    construction_value=Decimal(60000),
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
# Valores de prueba, NO normativa real: la real llega del motor de normativa.
TAX = TaxParams(
    marginal_rate=Decimal("0.30"),
    rental_income_reduction=Decimal("0.50"),
    depreciation_rate=Decimal("0.03"),
    rule_ids=("regla-de-prueba",),
)


def test_rentabilidad_bruta():
    res = compute_cashflow(INV, RENT, TAX)
    assert res.gross_yield.value == Decimal("7.20")


def test_dinero_aportado():
    res = compute_cashflow(INV, RENT, TAX)
    assert res.cash_invested.value == Decimal("60000.00")


def test_cifras_fiscales_citan_su_regla():
    res = compute_cashflow(INV, RENT, TAX)
    assert "regla-de-prueba" in res.annual_tax.sources
    assert "regla-de-prueba" in res.monthly_cashflow_after_tax.sources


def test_gestion_pasiva_reduce_el_cash_flow():
    activa = compute_cashflow(INV, RENT, TAX)
    pasiva_rent = RentalAssumptions(**{**RENT.__dict__, "management_fee_rate": Decimal("0.08")})
    pasiva = compute_cashflow(INV, pasiva_rent, TAX)
    assert pasiva.monthly_cashflow_after_tax.value < activa.monthly_cashflow_after_tax.value


def test_sin_impuesto_si_rendimiento_negativo():
    cara = InvestmentInputs(**{**INV.__dict__, "first_year_interest": Decimal(20000)})
    res = compute_cashflow(cara, RENT, TAX)
    assert res.annual_tax.value == Decimal("0.00")
