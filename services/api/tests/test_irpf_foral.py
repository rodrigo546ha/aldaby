"""IRPF foral, alquiler por régimen y reglas de Navarra y el País Vasco (ADR-0046).

Cifras a mano con las reglas del repositorio, todas sin verificar: ITP de Navarra 6 % (DFLeg
129/1999, art. 8.1.a) y de Bizkaia 4 % (NF 1/2011, art. 13.b); contribución territorial de Pamplona
0,25 % y plusvalía 17,35 % (Ley Foral 2/1995, art. 175.2 para los coeficientes máximos).
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from test_simulate import by_key, caso

from housefinder.engines.irpf import income_tax
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.planning.simulate import simulate
from housefinder.regulation.resolvers import income_tax_profile
from housefinder.regulation.rules import RuleBook, default_rules_dir

D = Decimal


@pytest.fixture(scope="module")
def rules() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


@pytest.fixture(scope="module")
def params() -> ParamBook:
    return ParamBook.from_dir(default_params_dir())


def en(residence: str, territory: str, **property_changes):
    base = caso()
    return replace(base, buyer=replace(base.buyer, residence=residence),
                   property=replace(base.property, territory=territory, **property_changes))


def test_cuota_foral_de_bizkaia_y_navarra(rules):
    hoy = date(2026, 11, 3)
    bizkaia = income_tax_profile(rules, "ES-16-48", hoy, D(30000), 40, (), allow_unverified=True)
    # 18.080 × 23 % + 11.920 × 28 % = 7.496,00 − 1.615 de minoración = 5.881,00
    assert income_tax(D(30000), bizkaia) == D("5881.00")
    navarra = income_tax_profile(rules, "ES-15", hoy, D(30000), 40, (), allow_unverified=True)
    # 4.591,63 + 8.825 × 28 % = 7.062,63 − 1.084 − 150 (mínimo por renta a 30.000) = 5.828,63
    assert income_tax(D(30000), navarra) == D("5828.63")


def test_residente_en_navarra_con_piso_en_pamplona(rules, params):
    sim = simulate(en("ES-15", "ES-15-31201"), rules, params, allow_unverified=True)
    v = by_key(sim)
    assert v["purchase_costs.transfer_tax"] == D("12000.00")  # 200.000 × 6 %
    assert v["holding_costs.ibi_annual"] == D("250.00")  # 100.000 × 0,25 %
    # Base objetiva 40.000 × 0,58 = 23.200 > incremento real (243.798,88 − 200.000) × 0,4 =
    # 17.519,55, que es la base: × 17,35 % = 3.039,64
    assert v["sale_costs.municipal_gains_tax"] == D("3039.64")
    figures = {f.key: f for f in sim.figures()}
    assert "todos, hasta los ingresos" in figures["cashflow.annual_tax"].formula
    assert "navarra-rendimiento-alquiler" in {s.id for s in figures["cashflow.annual_tax"].sources}


def test_residente_en_bizkaia_con_piso_en_bilbao(rules, params):
    # Bilbao: sin ordenanzas leídas, así que IBI del recibo y sin plusvalía
    sim = simulate(en("ES-16-48", "ES-16-48020", ibi_annual=D(300), cadastral_land_value=None),
                   rules, params, allow_unverified=True)
    v = by_key(sim)
    assert v["purchase_costs.transfer_tax"] == D("8000.00")  # 200.000 × 4 %
    figures = {f.key: f for f in sim.figures()}
    formula = figures["cashflow.annual_tax"].formula
    assert "base del ahorro" in formula and "bonificación 0.3)" in formula
    # Ingresos 11.400 × 0,70 − intereses del primer año, a la escala del ahorro (19 % al principio)
    assert 0 < v["cashflow.annual_tax"] < D("11400") * D("0.70") * D("0.19")


def test_madrileno_que_compra_en_bilbao_tributa_por_el_irpf_comun(rules, params):
    sim = simulate(en("ES-13", "ES-16-48020", ibi_annual=D(300), cadastral_land_value=None),
                   rules, params, allow_unverified=True)
    figures = {f.key: f for f in sim.figures()}
    assert figures["purchase_costs.transfer_tax"].value == D("8000.00")  # el ITP va por el inmueble
    assert "base del ahorro" not in figures["cashflow.annual_tax"].formula


def test_gipuzkoa_sin_irpf_leido_no_tiene_plan(rules, params):
    with pytest.raises(LookupError, match="ES-16-20"):
        simulate(en("ES-16-20", "ES-13-28079"), rules, params, allow_unverified=True)


def test_residente_foral_sin_regla_propia_no_usa_la_estatal(rules):
    from housefinder.regulation.kinds import RentalFacts
    from housefinder.regulation.resolvers import tax_params

    situation = RentalFacts(contract="primer-alquiler", large_holder=False)
    with pytest.raises(LookupError, match="rendimiento_alquiler_irpf"):
        tax_params(rules, "ES-13-28079", date(2026, 11, 3), situation, marginal_rate=D("0.3"),
                   allow_unverified=True, residence="ES-16-20")
