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


# --- Regímenes forales (ADR-0046) ---------------------------------------------------------


def test_regimen_vasco_bonificacion_sobre_ingresos_y_solo_intereses():
    # Bizkaia y Álava, art. 32.2: (10.260 × (1 − 0,30) − 3.100) = 4.082; ni IBI, ni comunidad,
    # ni reparación, ni amortización. Con un tipo del 20 %: 816,40.
    vasco = replace(TAX, marginal_rate=Decimal("0.20"), rental_income_reduction=Decimal(0),
                    rental_base="ahorro", gross_bonus=Decimal("0.30"),
                    deductible_expenses="intereses", expense_cap="sin_negativo")
    res = compute_cashflow(INV, RENT, vasco)
    assert res.annual_tax.value == Decimal("816.40")
    assert "base del ahorro" in res.annual_tax.formula
    # Si los intereses pasan de los ingresos bonificados, el neto es cero y no se arrastra nada
    caro = replace(INV, first_year_interest=Decimal(9000))
    res = compute_cashflow(caro, RENT, vasco)
    assert res.annual_tax.value == Decimal("0.00") and res.pending_excess == ()


def test_regimen_navarro_todos_los_gastos_hasta_los_ingresos():
    # Art. 25.1: gastos 1.883 + 3.100 + 1.800 = 6.783 < 10.260: neto 3.477, sin reducción
    # fuera de zona tensionada; al 30 %: 1.043,10.
    navarro = replace(TAX, rental_income_reduction=Decimal(0), expense_cap="todos")
    assert compute_cashflow(INV, RENT, navarro).annual_tax.value == Decimal("1043.10")
    # Con intereses de 9.000: gastos 12.683 > 10.260; neto 0 y 2.423 pendientes cuatro años
    res = compute_cashflow(replace(INV, first_year_interest=Decimal(9000)), RENT, navarro)
    assert res.annual_tax.value == Decimal("0.00")
    assert res.pending_excess == (PendingExcess(Decimal("2423.00"), 4),)


def test_desglose_del_primer_ano_calculado_a_mano():
    # ADR-0050. Con los mismos datos que el cash-on-cash, en €/año y los gastos en negativo:
    #   renta 900 × 12 = 10.800; vacío 5 % = −540; comunidad 60 × 12 = −720; IBI −300;
    #   seguros −350; gestión 0; mantenimiento 5 % de 10.260 cobrados = −513;
    #   intereses −3.100; capital 442,68 × 12 − 3.100 = −2.212,16; IRPF −521,55
    #   total = 3.064,84 de cash flow operativo − 521,55 de impuesto = 2.543,29
    res = compute_cashflow(INV, RENT, TAX)
    by = {f.key: f.value for f in res.breakdown}
    assert by == {
        "cashflow.breakdown.rent": Decimal("10800.00"),
        "cashflow.breakdown.vacancy": Decimal("-540.00"),
        "cashflow.breakdown.management": Decimal("0.00"),
        "cashflow.breakdown.community": Decimal("-720.00"),
        "cashflow.breakdown.ibi": Decimal("-300.00"),
        "cashflow.breakdown.insurance": Decimal("-350.00"),
        "cashflow.breakdown.maintenance": Decimal("-513.00"),
        "cashflow.breakdown.interest": Decimal("-3100.00"),
        "cashflow.breakdown.principal": Decimal("-2212.16"),
        "cashflow.breakdown.tax": Decimal("-521.55"),
    }
    assert res.annual_after_tax.key == "cashflow.annual_after_tax"
    assert res.annual_after_tax.value == Decimal("2543.29")
    assert sum(by.values()) == res.annual_after_tax.value
    assert all(f.unit == "EUR/año" for f in (*res.breakdown, res.annual_after_tax))


def test_el_desglose_cita_las_fuentes_de_cada_parte():
    res = compute_cashflow(INV, RENT, TAX)
    by = {f.key: f for f in res.breakdown}
    assert RENTA in by["cashflow.breakdown.rent"].sources
    assert OFERTA in by["cashflow.breakdown.interest"].sources
    assert REGLA in by["cashflow.breakdown.tax"].sources
    assert REGLA in res.annual_after_tax.sources


def test_un_ahorro_fiscal_suma_en_el_desglose():
    # Rendimiento negativo con cuota incremental: el impuesto es negativo y en el desglose suma
    cara = replace(INV, first_year_interest=Decimal(9000))
    res = compute_cashflow(cara, RENT, TAX_INCREMENTAL)
    tax = next(f for f in res.breakdown if f.key == "cashflow.breakdown.tax")
    assert tax.value == -res.annual_tax.value
    assert res.annual_after_tax.value == (res.annual_operating_cashflow.value
                                          - res.annual_tax.value)
