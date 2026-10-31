"""Simulación de punta a punta (G3): un solo camino de cálculo para el simulador y el plan.

Caso sintético calculado a mano, sin el motor: fórmulas cerradas en coma flotante (cuota
francesa, intereses del primer año = 12 × cuota − capital amortizado, escalas del IRPF
tramo a tramo). Detalle en tests/fixtures/planes/sintetico-01.yaml.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from housefinder.core.figures import SourceRef
from housefinder.engines.rates import MortgageTerms
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.planning.scenarios import compare_with_pending
from housefinder.planning.simulate import (
    AppreciationAlternative,
    BuyerInput,
    ExitInput,
    FinancingInput,
    PropertyInput,
    RentalInput,
    SimulationInput,
    simulate,
)
from housefinder.regulation.kinds import RentalFacts
from housefinder.regulation.rules import RuleBook, default_rules_dir

D = Decimal


@pytest.fixture(scope="module")
def rules() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


@pytest.fixture(scope="module")
def params() -> ParamBook:
    return ParamBook.from_dir(default_params_dir())


def caso(**changes) -> SimulationInput:
    base = SimulationInput(
        buyer=BuyerInput(
            net_monthly_income=D(4000),
            existing_monthly_debt=D(0),
            available_savings=D(90000),
            age=40,
            residence="ES-13",
            taxable_base=D(25000),
        ),
        property=PropertyInput(
            price=D(200000),
            territory="ES-13-28079",
            construction_value=D(80000),
            other_purchase_cost_rate=D("0.005"),
            community_fees_monthly=D(60),
            insurance_annual=D(250),
            renovation=D(10000),
            cadastral_value=D(100000),
            cadastral_land_value=D(40000),
        ),
        financing=FinancingInput(annual_rate=D("0.03"), rate_shock=D("0.02"), years=25),
        rental=RentalInput(
            monthly_rent=D(1000),
            vacancy_rate=D("0.05"),
            management_fee_rate=D(0),
            maintenance_reserve_rate=D("0.05"),
            situation=RentalFacts(contract="primer-alquiler", large_holder=False),
            contract_date=date(2026, 11, 15),
        ),
        exit=ExitInput(
            appreciation_rate=D("0.02"),
            sale_cost_rate=D("0.03"),
        ),
        purchase_date=date(2026, 10, 28),
    )
    return replace(base, **changes)


def by_key(sim) -> dict[str, Decimal]:
    return {f.key: f.value for f in sim.figures()}


def test_caso_sintetico_calculado_a_mano(rules, params):
    v = by_key(simulate(caso(), rules, params, allow_unverified=True))
    # Gastos de compra: ITP de Madrid 6 %, registro 176,90 + IVA (la escritura la paga el
    # vendedor) y 0,5 % de gestoría, tasación y copias.
    assert v["purchase_costs.transfer_tax"] == D("12000.00")
    assert v["purchase_costs.registry"] == D("214.05")
    assert "purchase_costs.notary" not in v
    assert v["purchase_costs.total"] == D("13214.05")
    # Capacidad: manda el ahorro, 90.000 / (1 − 0,70 + 0,0661) = 245.834,47.
    assert v["affordability.max_price"] == D("245834.47")
    # Préstamo = 70 % del precio; cuota a 3 % y 25 años = 663,8958; a 5 %, 818,4261.
    assert v["financing.loan"] == D("140000.00")
    assert v["mortgage.monthly_payment"] == D("663.90")
    assert v["mortgage.stressed_payment"] == D("818.43")
    # IBI: 100.000 × 0,414 %.
    assert v["holding_costs.ibi_annual"] == D("414.00")
    # Primer año: 11.400 cobrados − 1.954 de gastos − 7.966,75 de cuotas = 1.479,25.
    assert abs(v["cashflow.annual_operating"] - D("1479.25")) < 1
    # Rendimiento reducido 1.449,11 (reducción general 50 %) × (15 % + 12,8 %) = 402,85.
    assert abs(v["cashflow.annual_tax"] - D("402.85")) < 1
    assert abs(v["cashflow.monthly_after_tax"] - D("89.70")) < 1
    assert v["cashflow.cash_invested"] == D("83214.05")
    # Con +2 puntos, el plazo más corto con cash flow ≥ 0 es 28 años (775,00 €/mes).
    assert v["term.recommended_years"] == D(28)
    assert abs(v["term.stressed_monthly_payment"] - D("775.00")) < 1
    # Venta a 10 años: 200.000 × 1,02^10; escritura 361,32 + IVA; plusvalía 40.000 × 0,12 ×
    # 29 %; ganancia 35.441,66 por la escala del ahorro estatal + autonómica.
    assert v["irr.sale_price"] == D("243798.88")
    assert v["sale_costs.notary"] == D("437.20")
    assert v["sale_costs.municipal_gains_tax"] == D("1392.00")
    assert v["irr.capital_gains_tax"] == D("7322.74")


def test_cada_cifra_tiene_clave_unica_y_fuentes(rules, params):
    figures = simulate(caso(), rules, params, allow_unverified=True).figures()
    keys = [f.key for f in figures]
    assert len(keys) == len(set(keys))
    assert all(f.sources for f in figures)


def test_reglas_sin_verificar_dan_cifras_provisionales_y_aviso(rules, params):
    sim = simulate(caso(), rules, params, allow_unverified=True)
    assert sim.regulated_costs.tax.provisional
    assert any("PROVISIONALES" in w and "madrid-itp-inmuebles-2014" in w for w in sim.warnings)


def test_sin_permitir_reglas_sin_verificar_es_un_error(rules, params):
    with pytest.raises(LookupError, match="verificada"):
        simulate(caso(), rules, params)


def test_avisos_de_plan_incoherente(rules, params):
    inp = caso(buyer=replace(caso().buyer, available_savings=D(50000)))
    sim = simulate(inp, rules, params, allow_unverified=True)
    assert not sim.within_budget
    assert any("supera el precio máximo" in w for w in sim.warnings)
    assert any("supera el ahorro disponible" in w for w in sim.warnings)


def test_prestamo_y_plazo_por_defecto(rules, params):
    inp = caso(financing=FinancingInput(annual_rate=D("0.03"), rate_shock=D("0.02")))
    sim = simulate(inp, rules, params, allow_unverified=True)
    assert sim.loan.value == D("140000.00")
    assert sim.loan_years.value == D(30)  # mín(30, 75 − 40)
    assert any(ref.kind == "param" for ref in sim.loan.sources)


def test_ibi_del_recibo(rules, params):
    prop = replace(caso().property, cadastral_value=None, ibi_annual=D(380))
    sim = simulate(caso(property=prop), rules, params, allow_unverified=True)
    assert sim.ibi_annual.value == D("380.00")
    assert not any(ref.kind == "rule" for ref in sim.ibi_annual.sources)


def test_tipo_marginal_supuesto(rules, params):
    buyer = replace(caso().buyer, taxable_base=None, marginal_rate=D("0.30"))
    sim = simulate(caso(buyer=buyer), rules, params, allow_unverified=True)
    # 1.449,11 × 0,30 = 434,73.
    assert abs(sim.cashflow.annual_tax.value - D("434.73")) < 1
    assert any(ref.id == "tipo-marginal" for ref in sim.cashflow.annual_tax.sources)


def test_comparacion_de_ofertas_con_el_euribor(rules, params):
    offers = (
        MortgageTerms.fixed("fija", D("0.03")),
        MortgageTerms("variable", D("0.025"), 12, spread=D("0.008")),
    )
    fin = replace(caso().financing, alternatives=offers)
    sim = simulate(caso(financing=fin), rules, params, allow_unverified=True)
    assert sim.comparison is not None
    assert [o.label for o in sim.comparison.options] == ["fija", "variable"]
    keys = by_key(sim)
    assert "mortgage_comparison.variable.expected_total_interest" in keys


def test_vivienda_nueva_paga_iva_y_ajd(rules, params):
    prop = replace(caso().property, new_build=True)
    v = by_key(simulate(caso(property=prop), rules, params, allow_unverified=True))
    assert v["purchase_costs.vat"] == D("20000.00")  # 10 %
    assert v["purchase_costs.stamp_duty"] == D("1500.00")  # 0,75 % (más de 180.000 €)
    assert "purchase_costs.transfer_tax" not in v


def test_escritura_pagada_por_el_comprador(rules, params):
    prop = replace(caso().property, deed_agreement="comprador")
    v = by_key(simulate(caso(property=prop), rules, params, allow_unverified=True))
    assert v["purchase_costs.notary"] == D("412.02")  # 340,51 + 21 % IVA


def test_sin_suelo_catastral_no_hay_plusvalia_y_se_avisa(rules, params):
    prop = replace(caso().property, cadastral_land_value=None)
    sim = simulate(caso(property=prop), rules, params, allow_unverified=True)
    assert sim.municipal_gains is None
    assert any("plusvalía" in w for w in sim.warnings)


def test_escenario_con_reglas_pendientes(rules, params):
    # Primer alquiler a un joven desde el 01/12/2026: 50 % con la Ley 12/2023 (sin zona
    # tensionada), 85 % con el RDL 29/2026.
    situation = RentalFacts(contract="primer-alquiler", large_holder=False, young_tenant=True)
    rental = replace(caso().rental, contract_date=date(2026, 12, 15), situation=situation)
    inp = caso(rental=rental)
    comp = compare_with_pending(
        "rdl-29-2026",
        lambda pending: simulate(inp, rules, params, pending, allow_unverified=True).figures(),
    )
    assert "irpf-reduccion-alquiler-rdl-29-2026" in {r.id for r in comp.new_rules}
    assert "cashflow.annual_tax" in {c.key for c in comp.changed}
    # La venta (2036) usa los coeficientes máximos del RDL: a 10 años, 0,22 en vez de 0,12.
    assert "plusvalia-coeficientes-maximos-rdl-29-2026" in {r.id for r in comp.new_rules}
    plusvalia = next(c for c in comp.changed if c.key == "sale_costs.municipal_gains_tax")
    assert plusvalia.scenario.value == D("2552.00")  # 40.000 × 0,22 × 29 %


def test_escenarios_de_revalorizacion_dan_tres_tir(rules, params):
    # F5.5: la base va al plan con sus fuentes; los otros escenarios repiten venta y TIR
    base_sources = (SourceRef("dataset", "ine-ipv-80270@2026T2"),
                    SourceRef("model", "escenarios-revalorizacion-v1"))
    other = (SourceRef("dataset", "ine-ipv-80270@2026T2"),)
    exit_ = replace(caso().exit, appreciation_sources=base_sources, alternatives=(
        AppreciationAlternative("conservative", D("-0.0009"), other),
        AppreciationAlternative("optimistic", D("0.0599"), other)))
    sim = simulate(caso(exit=exit_), rules, params, allow_unverified=True)
    v = by_key(sim)
    assert v["irr.rate_conservative"] < v["irr.rate"] < v["irr.rate_optimistic"]
    # el plan principal no cambia: sigue con el 2 % de la base
    assert v["irr.rate"] == by_key(simulate(caso(), rules, params, allow_unverified=True))[
        "irr.rate"]
    sale = next(f for f in sim.figures() if f.key == "irr.sale_price")
    assert base_sources[1] in sale.sources
    assert not any(s.id == "revalorizacion" for s in sale.sources)  # ya no es un supuesto


def test_alquiler_que_no_es_de_vivienda_va_sin_reduccion(rules, params):
    regime = SourceRef("rule", "alquiler-turistico-estatal", provisional=True)
    sim = simulate(caso(rental=replace(caso().rental, housing_lease=False,
                                       housing_lease_sources=(regime,))),
                   rules, params, allow_unverified=True)
    v = by_key(sim)
    # Sin la reducción del 50 %: 2.898,22 de rendimiento × (15 % + 12,8 %) = 805,70, y
    # (1.479,25 − 805,70) / 12 = 56,13 al mes.
    assert abs(v["cashflow.annual_tax"] - D("805.70")) < 1
    assert abs(v["cashflow.monthly_after_tax"] - D("56.13")) < 1
    ids = {s.id for s in sim.cashflow.annual_tax.sources}
    assert "alquiler-turistico-estatal" in ids
    assert not any(i.startswith("irpf-reduccion") for i in ids)
