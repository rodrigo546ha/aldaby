"""Búsqueda inversa: qué ofertas pasan las restricciones del usuario y en qué orden (F6.5).

Puro y determinista: recibe el resultado del plan de cada oferta y decide. El agente solo explica
el orden (ADR-0023).

- **Restricciones:** el precio cabe en su capacidad de compra, le llega el ahorro y el cash flow
  mensual tras impuestos llega a su mínimo (cero si no lo ha dicho) en el escenario de su riesgo:
  bajo, con la subida de tipos y la renta baja de la zona (P25); medio o sin decir, con la subida
  de tipos y la renta mediana; alto, en el escenario base.
- **Orden:** según su objetivo. Renta (o sin decir): cash flow mensual tras impuestos. Patrimonio o
  mixto: TIR al horizonte con el escenario base de revalorización (mixto incluye el cash flow).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from housefinder.core.figures import Figure

Goal = Literal["renta", "patrimonio", "mixto"]
Risk = Literal["baja", "media", "alta"]
StressRent = Literal["p25", "mediana"]


@dataclass(frozen=True)
class Outcome:
    """Lo que el plan de una oferta dice para la búsqueda."""

    cashflow: Figure  # mensual tras impuestos, renta mediana, escenario base
    stressed_cashflow: Figure | None  # con la subida de tipos y la renta del riesgo; None si alto
    irr: Figure | None
    within_budget: bool
    savings_ok: bool


@dataclass(frozen=True)
class Verdict:
    passes: bool
    reasons: tuple[str, ...]  # por qué no pasa, en palabras y sin cifras
    metric: Figure | None  # por lo que se ordena


def stress_rent(risk: Risk | None) -> StressRent | None:
    """Con qué renta se hace la prueba de estrés; None: sin prueba (riesgo alto)."""
    return {"baja": "p25", "alta": None}.get(risk or "media", "mediana")


def judge(outcome: Outcome, risk: Risk | None, goal: Goal | None,
          min_cashflow: Decimal) -> Verdict:
    reasons = []
    if not outcome.within_budget:
        reasons.append("El precio pasa de tu capacidad de compra")
    if not outcome.savings_ok:
        reasons.append("No te llega el ahorro para la entrada y los gastos")
    if outcome.cashflow.value < min_cashflow:
        reasons.append("El cash flow no llega a tu mínimo")
    stressed = outcome.stressed_cashflow
    if stressed is not None and stressed.value < min_cashflow:
        reasons.append("Con la subida de tipos el cash flow no llega a tu mínimo" if
                       stress_rent(risk) == "mediana" else
                       "Con la subida de tipos y la renta baja de la zona el cash flow no llega a "
                       "tu mínimo")
    return Verdict(not reasons, tuple(reasons), metric_for(goal, outcome))


def metric_for(goal: Goal | None, outcome: Outcome) -> Figure | None:
    return outcome.irr if goal in ("patrimonio", "mixto") else outcome.cashflow


def rank(verdicts: dict[str, Verdict]) -> list[str]:
    """Primero las que pasan, de mayor a menor; después las demás. Sin métrica, al final."""
    def key(item: tuple[str, Verdict]) -> tuple[bool, bool, Decimal]:
        verdict = item[1]
        metric = verdict.metric.value if verdict.metric is not None else Decimal(0)
        return (not verdict.passes, verdict.metric is None, -metric)

    return [offer for offer, _ in sorted(verdicts.items(), key=key)]
