"""Coherencia del plan completo (F6.9, ADR-0027): reglas que cruzan sus cifras."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from test_offer_valuation import database  # noqa: F401
from test_plan_assumptions import references  # noqa: F401
from test_reverse_search import book, org, profile, rules, searchable  # noqa: F401

psycopg = pytest.importorskip("psycopg")

D = Decimal


@pytest.fixture
def plan(searchable, org):  # noqa: F811
    from test_offer_valuation import confirmed_offer

    from housefinder.plans.service import full_plan

    offer = confirmed_offer(searchable, org, "venta", "150000")
    with psycopg.connect(searchable) as conn:
        return full_plan(conn, book(), rules(), profile(management_fee_rate=D("0.08")), org,
                         offer, date(2026, 10, 31))


def changed(plan, key: str, value: str):
    """El plan con una cifra cambiada, para ver que la regla salta."""
    sections = tuple(replace(s, figures=tuple(replace(f, value=D(value)) if f.key == key else f
                                              for f in s.figures)) for s in plan.sections)
    return replace(plan, sections=sections)


@pytest.mark.db
def test_un_plan_real_es_coherente(plan):
    from housefinder.plans.coherence import check_plan

    assert check_plan(plan) == []
    assert not any("Incoherencia" in n for n in plan.notes)


@pytest.mark.db
def test_cada_regla_salta(plan):
    from housefinder.plans.coherence import check_plan

    assert check_plan(changed(plan, "purchase_costs.total", "1")) == [
        "Los gastos de compra no suman sus partes"]
    assert check_plan(changed(plan, "cashflow.cash_invested", "1")) == [
        "El dinero aportado no cubre precio + gastos − préstamo"]
    assert "La cuota con la subida de tipos es menor que la cuota" in check_plan(
        changed(plan, "mortgage.stressed_payment", "1"))
    assert "El argumento del cash flow negativo no cuadra con el cash flow" in check_plan(
        changed(plan, "cashflow.monthly_after_tax", "-500"))
    auction_step = plan.roadmap[0].model_copy(update={"id": "subasta-deposito"})
    assert "La hoja de ruta de un anuncio lleva pasos de subasta" in check_plan(
        replace(plan, roadmap=(*plan.roadmap, auction_step)))
