from datetime import date
from decimal import Decimal

import pytest

from housefinder.core.figures import Figure, SourceRef
from housefinder.engines.cashflow import InvestmentInputs, RentalAssumptions, compute_cashflow
from housefinder.planning.scenarios import compare_figures, compare_with_pending
from housefinder.regulation.kinds import RentalFacts
from housefinder.regulation.resolvers import tax_params
from housefinder.regulation.rules import RuleBook, default_rules_dir

MADRID = "ES-13-28079"
A = SourceRef("user_input", "a")
B = SourceRef("rule", "b", provisional=True)


# --- compare_figures ------------------------------------------------------------


def test_diferencia_por_clave():
    base = [Figure("x.uno", Decimal("10.00"), "EUR", "f", (A,))]
    escenario = [Figure("x.uno", Decimal("12.50"), "EUR", "f", (A, B))]
    res = compare_figures("prueba", base, escenario)
    (change,) = res.changes
    assert change.delta.value == Decimal("2.50")
    assert change.delta.key == "scenario.prueba.x.uno.delta"
    assert change.delta.unit == "EUR"
    assert set(change.delta.sources) == {A, B}
    assert change.changed
    assert res.new_rules == (B,)


def test_cifras_iguales_no_cambian():
    fig = Figure("x.uno", Decimal(1), "EUR", "f")
    res = compare_figures("prueba", [fig], [fig])
    assert not res.changes[0].changed
    assert res.changed == ()


def test_claves_solo_en_un_lado():
    res = compare_figures(
        "prueba",
        [Figure("x.uno", Decimal(1), "EUR", "f")],
        [Figure("x.dos", Decimal(1), "EUR", "f")],
    )
    assert res.only_in_base == ("x.uno",)
    assert res.only_in_scenario == ("x.dos",)
    assert res.changes == ()


def test_unidades_distintas_son_un_error():
    with pytest.raises(ValueError, match="unidad"):
        compare_figures(
            "prueba",
            [Figure("x.uno", Decimal(1), "EUR", "f")],
            [Figure("x.uno", Decimal(1), "ratio", "f")],
        )


def test_clave_repetida_es_un_error():
    fig = Figure("x.uno", Decimal(1), "EUR", "f")
    with pytest.raises(ValueError, match="repetida"):
        compare_figures("prueba", [fig, fig], [fig])


def test_nombre_de_escenario_invalido():
    with pytest.raises(ValueError):
        compare_figures("Con RDL", [], [])


# --- Con / sin normativa pendiente -----------------------------------------------

INV = InvestmentInputs(
    price=Decimal(150000), purchase_costs=Decimal(15000), renovation=Decimal(0),
    loan=Decimal(105000), monthly_mortgage_payment=Decimal("442.68"),
    first_year_interest=Decimal(3100), construction_value=Decimal(60000),
)
RENT = RentalAssumptions(
    monthly_rent=Decimal(900), vacancy_rate=Decimal("0.05"), community_fees_monthly=Decimal(60),
    ibi_annual=Decimal(300), insurance_annual=Decimal(350), management_fee_rate=Decimal(0),
    maintenance_reserve_rate=Decimal("0.05"),
)
# Primer alquiler en zona tensionada, arrendatario adulto, contrato de enero de 2027.
SITUACION = RentalFacts(contract="primer-alquiler", large_holder=False, stressed_zone=True)


def test_con_y_sin_el_rdl_29_2026_valor_conocido():
    book = RuleBook.from_dir(default_rules_dir())

    def build(include_pending: bool) -> list[Figure]:
        tax = tax_params(
            book, MADRID, date(2027, 1, 15), SITUACION, Decimal("0.30"),
            include_pending=include_pending, allow_unverified=True,
        )
        res = compute_cashflow(INV, RENT, tax)
        return [res.annual_tax, res.monthly_cashflow_after_tax, res.cash_invested]

    res = compare_with_pending("rdl-29-2026", build)
    # Calculado a mano: rendimiento antes de reducción = 10.260 − 1.883 − 3.100 − 1.800 = 3.477
    #   sin RDL (50 %): impuesto 3.477 × 0,5 × 0,30 = 521,55
    #                   cash flow (3.064,84 − 521,55) / 12 = 211,94
    #   con RDL (90 %): impuesto 3.477 × 0,1 × 0,30 = 104,31
    #                   cash flow (3.064,84 − 104,31) / 12 = 246,71
    deltas = {c.key: c.delta.value for c in res.changed}
    assert deltas == {
        "cashflow.annual_tax": Decimal("-417.24"),
        "cashflow.monthly_after_tax": Decimal("34.77"),
    }
    assert [ref.id for ref in res.new_rules] == ["irpf-reduccion-alquiler-rdl-29-2026"]
    assert not any(c.key == "cashflow.cash_invested" for c in res.changed)


def test_normativa_pendiente_aplicable():
    book = RuleBook.from_dir(default_rules_dir())
    lau = {
        "alquiler-habitual-rdl-29-2026",
        "alquiler-temporada-rdl-29-2026",
        "alquiler-habitaciones-rdl-29-2026",
    }
    # En noviembre de 2026 ya rigen (pendientes) los cambios de la LAU del RDL 29/2026…
    noviembre = book.pending(MADRID, date(2026, 11, 15), allow_unverified=True)
    assert {r.id for r in noviembre} == lau
    # …y desde el 1 de diciembre, también la nueva reducción del IRPF y los coeficientes
    # máximos de la plusvalía.
    enero = book.pending(MADRID, date(2027, 1, 15), allow_unverified=True)
    assert {r.id for r in enero} == lau | {
        "irpf-reduccion-alquiler-rdl-29-2026",
        "plusvalia-coeficientes-maximos-rdl-29-2026",
    }
    # Antes del RDL 29/2026 no hay nada pendiente.
    assert book.pending(MADRID, date(2026, 9, 1), allow_unverified=True) == []
