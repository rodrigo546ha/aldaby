"""Resolutores de normativa: de reglas a entradas de los motores (F2.7).

Usan las reglas del repositorio. Mientras estén sin verificar, solo se resuelven con
allow_unverified=True y todas las cifras salen provisionales.
"""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines.cashflow import InvestmentInputs, RentalAssumptions, compute_cashflow
from housefinder.regulation.resolvers import ibi_annual, purchase_tax, tax_params
from housefinder.regulation.rules import RuleBook, default_rules_dir

MADRID = "ES-13-28079"
PRECIO = SourceRef("user_input", "precio-de-prueba")
TIPO_MARGINAL = SourceRef("user_input", "tipo-marginal-de-prueba")


@pytest.fixture(scope="module")
def book() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


# --- Impuesto de compra -------------------------------------------------------


def test_itp_valor_conocido(book: RuleBook):
    # 150.000 € × 6 % (DL 1/2010 de Madrid, art. 28) = 9.000,00 €
    fig = purchase_tax(
        book, Decimal(150000), MADRID, date(2026, 11, 1), new_build=False,
        price_sources=(PRECIO,), allow_unverified=True,
    )
    assert fig.value == Decimal("9000.00")
    assert fig.key == "purchase_costs.transfer_tax"
    assert SourceRef("rule", "madrid-itp-inmuebles-2014", provisional=True) in fig.sources
    assert PRECIO in fig.sources
    assert fig.provisional  # regla sin verificar


def test_sin_verificar_no_se_resuelve(book: RuleBook):
    with pytest.raises(LookupError, match="impuesto_compra_segunda_mano"):
        purchase_tax(book, Decimal(150000), MADRID, date(2026, 11, 1), new_build=False)


def test_vivienda_nueva_aun_no_disponible(book: RuleBook):
    with pytest.raises(LookupError, match="nueva"):
        purchase_tax(
            book, Decimal(150000), MADRID, date(2026, 11, 1), new_build=True,
            allow_unverified=True,
        )


# --- IBI ----------------------------------------------------------------------


def test_ibi_valor_conocido(book: RuleBook):
    # 85.000 € de valor catastral × 0,414 % (Ordenanza 9/2025) = 351,90 €
    fig = ibi_annual(book, Decimal(85000), MADRID, date(2026, 6, 1), allow_unverified=True)
    assert fig.value == Decimal("351.90")
    assert fig.key == "holding_costs.ibi_annual"
    assert SourceRef("rule", "madrid-ibi-urbana-2026", provisional=True) in fig.sources


def test_ibi_sin_regla_para_el_ano(book: RuleBook):
    with pytest.raises(LookupError, match="tipo_ibi"):
        ibi_annual(book, Decimal(85000), MADRID, date(2025, 6, 1), allow_unverified=True)


# --- TaxParams ----------------------------------------------------------------


def test_tax_params_contrato_de_2026(book: RuleBook):
    tax = tax_params(
        book, MADRID, contract_date=date(2026, 11, 15), reduction_case="general",
        marginal_rate=Decimal("0.30"), marginal_rate_sources=(TIPO_MARGINAL,),
        allow_unverified=True,
    )
    assert tax.rental_income_reduction == Decimal("0.50")
    assert tax.depreciation_rate == Decimal("0.03")
    assert tax.marginal_rate == Decimal("0.30")
    assert tax.rule_ids == ("irpf-reduccion-alquiler-ley-12-2023", "irpf-amortizacion-inmueble")
    assert TIPO_MARGINAL in tax.sources


def test_tax_params_escenario_rdl_29_2026(book: RuleBook):
    tax = tax_params(
        book, MADRID, contract_date=date(2027, 1, 15),
        reduction_case="primer-alquiler-zona-tensionada", marginal_rate=Decimal("0.30"),
        include_pending=True, allow_unverified=True,
    )
    assert tax.rental_income_reduction == Decimal("0.90")
    assert "irpf-reduccion-alquiler-rdl-29-2026" in tax.rule_ids


def test_caso_que_no_existe_en_la_regla(book: RuleBook):
    # El régimen del RDL 29/2026 no tiene caso «general»: el error lista los disponibles.
    with pytest.raises(ValueError, match="primer-alquiler-sobre-indice"):
        tax_params(
            book, MADRID, contract_date=date(2027, 1, 15), reduction_case="general",
            marginal_rate=Decimal("0.30"), include_pending=True, allow_unverified=True,
        )


def test_las_cifras_del_cash_flow_citan_las_reglas(book: RuleBook):
    tax = tax_params(
        book, MADRID, contract_date=date(2026, 11, 15), reduction_case="general",
        marginal_rate=Decimal("0.30"), allow_unverified=True,
    )
    inv = InvestmentInputs(
        price=Decimal(150000), purchase_costs=Decimal(15000), renovation=Decimal(0),
        loan=Decimal(105000), monthly_mortgage_payment=Decimal("442.68"),
        first_year_interest=Decimal(3100), construction_value=Decimal(60000),
    )
    rent = RentalAssumptions(
        monthly_rent=Decimal(900), vacancy_rate=Decimal("0.05"),
        community_fees_monthly=Decimal(60), ibi_annual=Decimal(300),
        insurance_annual=Decimal(350), management_fee_rate=Decimal(0),
        maintenance_reserve_rate=Decimal("0.05"),
    )
    res = compute_cashflow(inv, rent, tax)
    ids = {ref.id for ref in res.annual_tax.sources if ref.kind == "rule"}
    assert ids == {"irpf-reduccion-alquiler-ley-12-2023", "irpf-amortizacion-inmueble"}
    assert res.annual_tax.provisional
