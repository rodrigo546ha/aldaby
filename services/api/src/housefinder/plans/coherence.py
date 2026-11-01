"""Coherencia del plan completo: reglas que sus cifras tienen que cumplir (F6.9, ADR-0027).

Las cifras salen de motores distintos (capacidad, simulador, valoración, argumentos, hoja de ruta).
Estas reglas cruzan unas con otras: sumas que cuadran, órdenes que se cumplen y argumentos y pasos
que cuadran con sus cifras. Un fallo es un error del programa, no del usuario: el plan lo avisa.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING

from housefinder.core.figures import Figure

if TYPE_CHECKING:  # service.py usa estas reglas en cada plan
    from housefinder.plans.service import FullPlan

CENT = Decimal("0.01")
TWELVE = Decimal(12)


def check_plan(plan: FullPlan) -> list[str]:
    """Las reglas que no se cumplen, en palabras; vacía si el plan es coherente."""
    fig = {f.key: f for f in plan.figures()}
    problems: list[str] = []

    def value(key: str) -> Decimal | None:
        f = fig.get(key)
        return f.value if f is not None else None

    def rule(text: str, *keys: str, holds: Callable[..., bool]) -> None:
        values = [value(k) for k in keys]
        if all(v is not None for v in values) and not holds(*values):
            problems.append(text)

    rule("Los gastos de compra no suman sus partes", "purchase_costs.total",
         "purchase_costs.regulated", "purchase_costs.other",
         holds=lambda t, r, o: abs(t - r - o) <= CENT)
    rule("El dinero aportado no cubre precio + gastos − préstamo", "cashflow.cash_invested",
         "offer.price", "purchase_costs.total", "financing.loan",
         holds=lambda c, p, g, loan: c - (p + g - loan) >= -CENT)
    rule("El cash flow mensual no cuadra con el anual y el impuesto",
         "cashflow.monthly_after_tax", "cashflow.annual_operating", "cashflow.annual_tax",
         holds=lambda m, a, t: abs(m - (a - t) / TWELVE) <= CENT)
    rule("La cuota con la subida de tipos es menor que la cuota", "mortgage.stressed_payment",
         "mortgage.monthly_payment", holds=lambda s, m: s >= m)
    rule("La primera cuota de la fija no coincide con la cuota del plan",
         "mortgage_comparison.fija.first_payment", "mortgage.monthly_payment",
         holds=lambda f, m: abs(f - m) <= CENT)
    rule("El préstamo máximo pasa del precio máximo", "affordability.max_loan",
         "affordability.max_price", holds=lambda loan, price: loan <= price)
    rule("La TIR conservadora pasa de la base", "irr.rate_conservative", "irr.rate",
         holds=lambda c, b: c <= b)
    rule("La TIR optimista no llega a la base", "irr.rate_optimistic", "irr.rate",
         holds=lambda o, b: o >= b)
    rule("Con la renta baja de la zona el cash flow sale mayor", "plan.low_rent_cashflow",
         "cashflow.monthly_after_tax", holds=lambda low, base: low <= base)
    price, max_price = value("offer.price"), value("affordability.max_price")
    if price is not None and max_price is not None and price <= max_price:
        rule("Con el precio dentro de la capacidad, el préstamo pasa del máximo",
             "financing.loan", "affordability.max_loan", holds=lambda loan, m: loan <= m + CENT)
    _in_range(fig.get("valuation.rent_monthly"), problems)

    codes = {a.code for a in plan.arguments}
    cash = value("cashflow.monthly_after_tax")
    if cash is not None and (cash < 0) != ("cash-flow-negativo" in codes):
        problems.append("El argumento del cash flow negativo no cuadra con el cash flow")
    if price is not None and max_price is not None and \
            (price > max_price) != ("precio-sobre-capacidad" in codes):
        problems.append("El argumento del precio sobre la capacidad no cuadra con las cifras")
    if plan.auction != ("subasta" in codes):
        problems.append("El argumento de la subasta no cuadra con el canal")

    steps = {s.id for s in plan.roadmap}
    if plan.kind == "lote" and "arras" in steps:
        problems.append("La hoja de ruta de una subasta lleva arras")
    if plan.kind == "enlace" and any(s.startswith("subasta-") for s in steps):
        problems.append("La hoja de ruta de un anuncio lleva pasos de subasta")
    loan = value("financing.loan")
    if loan is not None and (loan > 0) != ("fein" in steps):
        problems.append("La hoja de ruta no cuadra con la hipoteca")

    if plan.advice is not None:
        advice = plan.advice.advice
        chosen = advice.chosen()
        if chosen is not None and not chosen.option.allowed:
            problems.append("Se recomienda un tipo de alquiler que no se puede ejercer")
        for t in advice.types:
            if t.delegation_cost is not None and t.delegation_cost.value < 0:
                problems.append(f"Delegar el alquiler {t.option.rental_type} sale más barato "
                                "que gestionarlo")
    return problems


def _in_range(f: Figure | None, problems: list[str]) -> None:
    if f is None or f.low is None or f.high is None:
        return
    if not f.low <= f.value <= f.high:
        problems.append(f"La cifra {f.key} queda fuera de su rango")
