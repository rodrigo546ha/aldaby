"""Simulador de puja de una subasta (ADR-0047): lo puro.

La puja máxima es la mayor puja, en múltiplos de `step`, con la que el plan del usuario sigue
cumpliendo sus restricciones; se busca por bisección, porque pujar más nunca mejora el plan.
La fase legal de cada puja sale de las reglas de la subasta judicial (LEC, arts. 670 y 671),
como datos.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal

from housefinder.core.figures import SourceRef, money
from housefinder.regulation.kinds import JudicialAuctionRules, parse_params
from housefinder.regulation.rules import RuleBook


@dataclass(frozen=True)
class JudicialAuction:
    """Reglas de la subasta judicial de inmuebles, resueltas de `subasta_judicial_inmuebles`."""

    deposit_rate: Decimal
    deposit_min: Decimal
    approval_share: Decimal
    improvement_share: Decimal
    floor_share: Decimal
    satisfaction_share: Decimal
    debtor_home_min_share: Decimal
    payment_days: int


def judicial_auction(book: RuleBook, on: date,
                     allow_unverified: bool = False) -> tuple[JudicialAuction, SourceRef]:
    """Las reglas de la subasta judicial vigentes en `on`; LookupError si no hay."""
    rule = book.resolve("subasta_judicial_inmuebles", "ES", on, False, allow_unverified)
    if rule is None:
        raise LookupError(f"No hay regla de subasta_judicial_inmuebles el {on}")
    p = parse_params(rule.kind, rule.params)
    if not isinstance(p, JudicialAuctionRules):
        raise TypeError(f"{rule.id}: se esperaban las reglas de la subasta judicial")
    return JudicialAuction(p.deposit_rate, p.deposit_min, p.approval_share, p.improvement_share,
                           p.floor_share, p.satisfaction_share, p.debtor_home_min_share,
                           p.payment_days), rule.ref


def judicial_deposit(auction_value: Decimal, rules: JudicialAuction) -> Decimal:
    """Depósito para pujar: una parte del valor de subasta, con un mínimo (LEC, art. 669.1)."""
    return money(max(auction_value * rules.deposit_rate, rules.deposit_min))


def legal_stage(share: Decimal, rules: JudicialAuction) -> str:
    """Qué pasa con una puja que es `share` del valor de subasta (LEC, arts. 670.1 y 670.3)."""
    home = (f" Si es la vivienda habitual del deudor, no se aprueba por menos del "
            f"{_pct(rules.approval_share)} salvo por lo que se le debe al ejecutante, y nunca "
            f"por menos del {_pct(rules.debtor_home_min_share)}.")
    if share >= rules.approval_share:
        return (f"Se aprueba el remate al día siguiente del cierre; el resto del precio se paga "
                f"en {rules.payment_days} días.")
    if share >= rules.floor_share:
        return (f"El deudor tiene diez días para presentar a alguien que mejore la puja hasta el "
                f"{_pct(rules.improvement_share)} (o lo que pague la deuda); si no, se aprueba."
                + home)
    if share >= rules.satisfaction_share:
        return ("Solo se aprueba si basta para pagar lo que se debe al ejecutante; si no, "
                "decide el letrado de la Administración de Justicia según las circunstancias."
                + home)
    return (f"Por debajo del {_pct(rules.satisfaction_share)} decide el letrado de la "
            "Administración de Justicia según las circunstancias del caso." + home)


def max_bid(passes: Callable[[Decimal], bool], low: Decimal, high: Decimal,
            step: Decimal) -> Decimal | None:
    """Mayor puja entre `low` y `high`, en múltiplos de `step`, con la que `passes` se cumple.

    None si no se cumple ni con `low`; `high` si se cumple incluso con él.
    """
    lo = _floor(low, step)
    if lo <= 0 or not passes(lo):
        return None
    hi = _floor(high, step)
    if passes(hi):
        return hi
    while hi - lo > step:  # passes(lo) y no passes(hi)
        mid = _floor((lo + hi) / 2, step)
        if passes(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _floor(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step


def _pct(share: Decimal) -> str:
    return f"{(share * 100).normalize():f} %"
