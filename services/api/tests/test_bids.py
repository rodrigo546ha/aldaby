"""Simulador de puja de una subasta (ADR-0047).

Las partes legales son las del repositorio (LEC, arts. 669.1 y 670, texto del BOE): depósito del
20 % con un mínimo de 1.000 €; remate aprobado desde el 70 %; mejora del deudor hasta el 60 %;
aprobación desde el 50 %, o desde el 40 % si paga al ejecutante.
"""

from datetime import date
from decimal import Decimal

import pytest

from housefinder.planning.bids import judicial_auction, judicial_deposit, legal_stage, max_bid
from housefinder.regulation.rules import RuleBook, default_rules_dir

D = Decimal
TODAY = date(2026, 11, 3)


@pytest.fixture(scope="module")
def lec():
    return judicial_auction(RuleBook.from_dir(default_rules_dir()), TODAY,
                            allow_unverified=True)[0]


def test_puja_maxima_por_biseccion():
    calls = []

    def passes(p: Decimal) -> bool:
        calls.append(p)
        return p <= D(123456)

    assert max_bid(passes, D(100), D(400000), D(100)) == D(123400)
    assert len(calls) < 25  # bisección, no un barrido
    assert max_bid(lambda p: False, D(100), D(400000), D(100)) is None
    assert max_bid(lambda p: True, D(100), D(400000), D(100)) == D(400000)


def test_deposito_judicial(lec):
    assert judicial_deposit(D(200000), lec) == D("40000.00")  # 20 %
    assert judicial_deposit(D(3000), lec) == D("1000.00")  # el mínimo


@pytest.mark.parametrize("share, expected", [
    (D("0.80"), "Se aprueba el remate al día siguiente"),
    (D("0.70"), "en 20 días"),
    (D("0.65"), "mejore la puja hasta el 60 %"),
    (D("0.50"), "si no, se aprueba"),
    (D("0.45"), "Solo se aprueba si basta para pagar"),
    (D("0.30"), "Por debajo del 40 %"),
])
def test_fase_legal_de_cada_puja(lec, share, expected):
    assert expected in legal_stage(share, lec)


def test_vivienda_habitual_del_deudor_por_debajo_del_70(lec):
    assert "vivienda habitual del deudor" in legal_stage(D("0.60"), lec)
    assert "vivienda habitual" not in legal_stage(D("0.75"), lec)


# --- El plan a cada puja ------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")
from test_offer_valuation import database  # noqa: E402, F401
from test_plan_assumptions import references  # noqa: E402, F401
from test_reverse_search import book, org, profile, rules, searchable  # noqa: E402, F401


@pytest.mark.db
def test_simulador_de_puja_de_una_subasta_judicial(searchable, org):  # noqa: F811
    from test_offer_valuation import confirmed_offer

    from housefinder.plans.bids import bid_simulation

    offer = confirmed_offer(searchable, org, "venta", "150000")
    with psycopg.connect(searchable) as conn:
        sim = bid_simulation(conn, book(), rules(), profile(), org, offer, D(150000),
                             charges=D(3000), judicial=True, today=TODAY)
    assert sim.auction_value.value == D("150000.00")
    assert sim.deposit is not None and sim.deposit.value == D("30000.00")
    assert [lv.price.value for lv in sim.levels] == [
        D("60000.00"), D("75000.00"), D("90000.00"), D("105000.00"), D("120000.00"),
        D("135000.00"), D("150000.00")]
    assert all(lv.stage for lv in sim.levels)
    # Pujar más nunca mejora el plan: el cash flow baja con la puja
    flows = [lv.cashflow.value for lv in sim.levels]
    assert flows == sorted(flows, reverse=True)
    if sim.max_bid is not None:
        # Las pujas de la tabla por debajo de la máxima cumplen; las de encima, no
        for lv in sim.levels:
            assert lv.verdict.passes == (lv.price.value <= sim.max_bid.value)
        assert "cargas-que-subsisten" in {s.id for s in sim.max_bid.sources}
    assert any("cargas anteriores" in n for n in sim.notes)


@pytest.mark.db
def test_sin_valor_de_subasta_no_hay_simulacion(searchable, org):  # noqa: F811
    from test_offer_valuation import confirmed_offer

    from housefinder.plans.bids import bid_simulation
    from housefinder.plans.service import PlanUnavailable

    offer = confirmed_offer(searchable, org, "venta", "150000")
    with psycopg.connect(searchable) as conn, pytest.raises(PlanUnavailable,
                                                            match="valor de subasta"):
        bid_simulation(conn, book(), rules(), profile(), org, offer, today=TODAY)
