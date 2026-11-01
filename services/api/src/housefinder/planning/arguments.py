"""Argumentos para no comprar (F6.7, ADR-0025).

Puro y determinista: comparaciones con las cifras del plan, sin umbrales inventados. Cada
argumento lleva las cifras en que se basa; el texto no lleva números, para que el agente pueda
explicarlo con marcadores (ADR-0012).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from housefinder.core.figures import Figure


@dataclass(frozen=True)
class Argument:
    code: str
    text: str
    figures: tuple[Figure, ...]


@dataclass(frozen=True)
class ArgumentInputs:
    price: Figure  # offer.price
    max_price: Figure  # affordability.max_price
    within_budget: bool
    cash_invested: Figure
    savings_ok: bool
    cashflow: Figure  # mensual tras impuestos, escenario base
    min_cashflow: Decimal  # el mínimo del usuario (cero si no lo dijo)
    stressed: Figure | None  # con la subida de tipos en el escenario de su riesgo
    low_rent_cashflow: Figure | None  # con la renta baja de la zona (P25)
    term_feasible: bool
    stressed_payment: Figure
    irr: Figure | None
    mortgage_rate: Figure
    estimated_price: Figure | None  # valuation.price_total, con su rango
    pending_delta: Figure | None  # cambio del cash flow con las reglas pendientes
    auction: bool
    provisional: bool


def arguments(i: ArgumentInputs) -> tuple[Argument, ...]:
    found: list[Argument] = []

    def add(code: str, text: str, *figures: Figure | None) -> None:
        found.append(Argument(code, text, tuple(f for f in figures if f is not None)))

    if not i.within_budget:
        add("precio-sobre-capacidad", "El precio pasa de tu capacidad de compra: el banco no te "
            "financiaría lo que hace falta con tus ingresos y tu ahorro.", i.price, i.max_price)
    if not i.savings_ok:
        add("ahorro-insuficiente", "No te llega el ahorro para la entrada, los gastos de compra y "
            "la reforma.", i.cash_invested)
    if i.cashflow.value < 0:
        add("cash-flow-negativo", "El cash flow es negativo: tendrías que poner dinero cada mes.",
            i.cashflow)
    elif i.cashflow.value < i.min_cashflow:
        add("cash-flow-bajo-minimo", "El cash flow no llega al mínimo que pediste.", i.cashflow)
    if i.stressed is not None and i.stressed.value < 0 <= i.cashflow.value:
        add("estres-negativo", "Con la subida de tipos de la prueba de estrés el cash flow pasa a "
            "negativo.", i.stressed, i.stressed_payment)
    if i.low_rent_cashflow is not None and i.low_rent_cashflow.value < 0 <= i.cashflow.value:
        add("renta-baja-negativo", "Si alquilas por la renta baja de la zona, el cash flow es "
            "negativo.", i.low_rent_cashflow)
    if not i.term_feasible:
        add("ningun-plazo-sostenible", "Ningún plazo de hipoteca mantiene el cash flow positivo "
            "con la subida de tipos.", i.stressed_payment)
    if i.irr is not None and i.irr.value < i.mortgage_rate.value:
        add("tir-bajo-tipo", "La rentabilidad de tu dinero queda por debajo del tipo de la "
            "hipoteca: te sale más caro el préstamo de lo que rinde la inversión.", i.irr,
            i.mortgage_rate)
    if (i.estimated_price is not None and i.estimated_price.high is not None
            and i.price.value > i.estimated_price.high):
        add("precio-sobre-estimado", "Lo que piden pasa de lo alto del rango del precio "
            "estimado para la zona.", i.price, i.estimated_price)
    if i.pending_delta is not None and i.pending_delta.value < 0:
        add("normas-pendientes", "Si se convalidan las normas pendientes, el cash flow baja.",
            i.pending_delta)
    if i.auction:
        add("subasta", "Es una subasta: el precio final puede ser otro, y las cargas que "
            "subsisten y si está ocupada hay que comprobarlas antes de pujar.", i.price)
    if i.provisional:
        add("cifras-provisionales", "Hay cifras provisionales: dependen de normas sin verificar o "
            "de supuestos estimados.")
    return tuple(found)
