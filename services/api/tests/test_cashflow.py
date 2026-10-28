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
from housefinder.engines.irpf import Bracket, IncomeTaxProfile, IrpfPart

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
    interest_repair_carryforward_years=4,
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



# --- Límite de intereses y reparación (LIRPF art. 23.1.a.1.º; RIRPF art. 13.a) -------------
# Rendimientos íntegros = renta cobrada = 10.260. Intereses + reparación (reserva) = 3.100 + 513.


def test_sin_exceso_no_hay_arrastre():
    assert compute_cashflow(INV, RENT, TAX).pending_excess == ()


def test_intereses_por_encima_de_los_ingresos_se_arrastran():
    cara = replace(INV, first_year_interest=Decimal(20000))
    res = compute_cashflow(cara, RENT, TAX)
    # Deducible = 10.260; exceso = 20.000 + 513 − 10.260 = 10.253, cuatro años por delante.
    assert res.pending_excess == (PendingExcess(Decimal("10253.00"), 4),)


def test_el_arrastre_se_usa_antes_que_los_gastos_del_ano():
    pendiente = (PendingExcess(Decimal("10253.00"), 4),)
    res = compute_cashflow(INV, RENT, TAX, pending_excess=pendiente)
    # Tope 10.260: entra el arrastre entero (10.253) y 7 € de los 3.613 del año.
    # El resto del año (3.606) empieza su propio arrastre de cuatro años.
    assert res.pending_excess == (PendingExcess(Decimal("3606.00"), 4),)


def test_el_arrastre_caduca_a_los_cuatro_anos():
    # 20.000 € en su último año: entran 10.260 (todo el tope) y los 9.740 restantes caducan.
    # Los 3.613 del año no caben y empiezan su propio arrastre.
    res = compute_cashflow(INV, RENT, TAX, pending_excess=(PendingExcess(Decimal(20000), 1),))
    assert res.pending_excess == (PendingExcess(Decimal("3613.00"), 4),)


# --- Cuota incremental (ADR-0007) ---------------------------------------------------------

ESTATAL = (
    Bracket(Decimal(0), Decimal("0.095")),
    Bracket(Decimal(12450), Decimal("0.12")),
    Bracket(Decimal(20200), Decimal("0.15")),
    Bracket(Decimal(35200), Decimal("0.185")),
    Bracket(Decimal(60000), Decimal("0.225")),
    Bracket(Decimal(300000), Decimal("0.245")),
)
MADRID = (
    Bracket(Decimal(0), Decimal("0.085")),
    Bracket(Decimal("13362.22"), Decimal("0.107")),
    Bracket(Decimal("19004.63"), Decimal("0.128")),
    Bracket(Decimal("35425.68"), Decimal("0.174")),
    Bracket(Decimal("57320.40"), Decimal("0.205")),
)
BASE = SourceRef("user_input", "base-liquidable-de-prueba")
PERFIL = IncomeTaxProfile(
    other_base=Decimal(30000),
    state=IrpfPart(ESTATAL, Decimal(5550)),
    regional=IrpfPart(MADRID, Decimal("5956.65")),
    sources=(BASE,),
)
TAX_INCREMENTAL = replace(TAX, marginal_rate=None, income_tax=PERFIL)


def test_impuesto_por_cuota_incremental():
    # Rendimiento 3.477 × (1 − 0,5) = 1.738,50 sobre una base de 30.000 en Madrid:
    #   estatal 260,78 + autonómica 222,53 = 483,31 (calculado a mano, céntimos por parte)
    res = compute_cashflow(INV, RENT, TAX_INCREMENTAL)
    assert res.annual_tax.value == Decimal("483.31")
    assert BASE in res.annual_tax.sources


def test_rendimiento_negativo_da_ahorro_fiscal():
    # Con intereses de 20.000: rendimiento = 10.260 − 1.370 − 10.260 − 1.800 = −3.170, sin
    # reducción (solo se reduce el positivo): −3.170 × (15 % + 12,8 %) = −881,26
    cara = replace(INV, first_year_interest=Decimal(20000))
    res = compute_cashflow(cara, RENT, TAX_INCREMENTAL)
    assert res.annual_tax.value == Decimal("-881.26")


def test_un_solo_modo_de_impuesto():
    with pytest.raises(ValueError):
        replace(TAX, income_tax=PERFIL)  # marginal e incremental a la vez
    with pytest.raises(ValueError):
        replace(TAX, marginal_rate=None)  # ninguno
