"""Argumentos para no comprar (F6.7, ADR-0025): reglas fijas sobre las cifras del plan."""

from dataclasses import replace
from decimal import Decimal

from housefinder.core.figures import Figure
from housefinder.planning.arguments import ArgumentInputs, arguments

D = Decimal


def fig(key: str, value: str, low: str | None = None, high: str | None = None) -> Figure:
    return Figure(key, D(value), "EUR", "x", low=D(low) if low else None,
                  high=D(high) if high else None)


def inputs(**changes) -> ArgumentInputs:
    base = ArgumentInputs(
        price=fig("offer.price", "200000"), max_price=fig("affordability.max_price", "250000"),
        within_budget=True, cash_invested=fig("cashflow.cash_invested", "60000"),
        savings_ok=True, cashflow=fig("cashflow.monthly_after_tax", "120"),
        min_cashflow=D(0), stressed=fig("search.stressed_cashflow", "30"),
        low_rent_cashflow=fig("plan.low_rent_cashflow", "10"), term_feasible=True,
        stressed_payment=fig("mortgage.stressed_payment", "900"),
        irr=Figure("irr.rate", D("0.06"), "ratio", "x"),
        mortgage_rate=Figure("assumption.mortgage_rate", D("0.03"), "ratio", "x"),
        estimated_price=fig("valuation.price_total", "210000", low="190000", high="230000"),
        pending_delta=None, auction=False, provisional=False)
    return replace(base, **changes)


def codes(**changes) -> list[str]:
    return [a.code for a in arguments(inputs(**changes))]


def test_un_buen_plan_no_tiene_argumentos_en_contra():
    assert codes() == []


def test_cada_regla_con_sus_cifras():
    found = arguments(inputs(within_budget=False, savings_ok=False,
                             cashflow=fig("cashflow.monthly_after_tax", "-50")))
    assert [a.code for a in found] == ["precio-sobre-capacidad", "ahorro-insuficiente",
                                       "cash-flow-negativo"]
    assert [f.key for f in found[0].figures] == ["offer.price", "affordability.max_price"]
    # Ningún texto lleva números: el agente los explica con marcadores
    assert not any(ch.isdigit() for a in found for ch in a.text)


def test_minimo_del_usuario():
    assert codes(min_cashflow=D(200)) == ["cash-flow-bajo-minimo"]


def test_estres_y_renta_baja_solo_si_el_base_es_positivo():
    assert codes(stressed=fig("search.stressed_cashflow", "-1"),
                 low_rent_cashflow=fig("plan.low_rent_cashflow", "-1")) == [
        "estres-negativo", "renta-baja-negativo"]
    # Con el base negativo ya lo dice «cash-flow-negativo»
    assert codes(cashflow=fig("cashflow.monthly_after_tax", "-5"),
                 stressed=fig("search.stressed_cashflow", "-90")) == ["cash-flow-negativo"]


def test_tir_bajo_el_tipo_y_precio_sobre_el_rango():
    assert codes(irr=Figure("irr.rate", D("0.02"), "ratio", "x"),
                 price=fig("offer.price", "240000")) == ["tir-bajo-tipo",
                                                         "precio-sobre-estimado"]


def test_pendientes_subasta_plazo_y_provisionales():
    assert codes(pending_delta=fig("scenario.x.delta", "-12"), auction=True,
                 term_feasible=False, provisional=True) == [
        "ningun-plazo-sostenible", "normas-pendientes", "subasta", "cifras-provisionales"]
