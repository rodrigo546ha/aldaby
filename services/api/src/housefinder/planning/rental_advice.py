"""Recomendación de tipo de alquiler y de gestión (F6.6, ADR-0024).

Puro y determinista: recibe, por cada tipo de alquiler, su normativa en el municipio y el cash
flow del plan con gestión activa y pasiva, y decide. El agente solo lo explica.

- **Gestión:** pasiva si el tipo exige mucha dedicación (temporada y turístico) o si la vivienda
  está fuera de la comunidad del usuario; si no, la que él eligió, o activa si no lo dijo.
- **Tipo:** entre los que se pueden ejercer y tienen cifras, el de mayor cash flow mensual tras
  impuestos con su gestión recomendada; si empatan, el primero de `RENTAL_TYPES`. Con riesgo
  bajo, el habitual siempre que se pueda.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from housefinder.core.figures import Figure, combine_sources, money
from housefinder.regulation.kinds import RENTAL_TYPES
from housefinder.regulation.resolvers import RegimeRequirement

Management = Literal["activa", "pasiva"]
# Tipos con rotación de inquilinos: anuncios, entradas, limpieza y cambios cada pocas semanas
HIGH_DEDICATION = ("temporada", "turistico")
LABELS = {"habitual": "habitual", "temporada": "de temporada",
          "habitaciones": "por habitaciones", "turistico": "turístico"}


@dataclass(frozen=True)
class TypeOption:
    """Lo que se sabe de un tipo de alquiler en una oferta."""

    rental_type: str
    allowed: bool
    regime: str
    requirements: tuple[RegimeRequirement, ...]
    irpf_reduction: bool | None  # None: por confirmar, el plan va sin reducción
    tax_notes: tuple[str, ...]
    rule_ids: tuple[str, ...]
    income: Figure | None  # renta mensual: SERPAVI (habitual) o la que espera el usuario
    active: Figure | None  # cash flow mensual tras impuestos con gestión activa
    passive: Figure | None  # con gestión pasiva; None sin lo que cobra la gestión


@dataclass(frozen=True)
class TypeAdvice:
    option: TypeOption
    management: Management
    management_reason: str
    cashflow: Figure | None  # con la gestión recomendada (o activa si falta lo que cobra)
    delegation_cost: Figure | None  # activa − pasiva, al mes
    notes: tuple[str, ...] = ()

    def figures(self) -> tuple[Figure, ...]:
        found = (self.option.income, self.cashflow, self.delegation_cost)
        return tuple(f for f in found if f is not None)


@dataclass(frozen=True)
class RentalAdvice:
    types: tuple[TypeAdvice, ...]  # en el orden de RENTAL_TYPES
    recommended: str | None
    reasons: tuple[str, ...]

    def figures(self) -> tuple[Figure, ...]:
        return tuple(f for t in self.types for f in t.figures())

    def chosen(self) -> TypeAdvice | None:
        return next((t for t in self.types if t.option.rental_type == self.recommended), None)


def management_for(rental_type: str, away: bool,
                   chosen: Management | None) -> tuple[Management, str]:
    """Gestión recomendada para un tipo y por qué, en palabras."""
    if rental_type in HIGH_DEDICATION:
        return "pasiva", (f"Pasiva: el alquiler {LABELS[rental_type]} exige mucha dedicación "
                          "(anuncios, entradas, limpieza y cambios de inquilino).")
    if away:
        return "pasiva", "Pasiva: la vivienda está fuera de tu comunidad."
    if chosen is not None:
        return chosen, f"{chosen.capitalize()}: es la que elegiste."
    return "activa", "Activa: te ahorras lo que cuesta delegar."


def advise(options: list[TypeOption], risk: str | None, chosen: Management | None,
           away: bool) -> RentalAdvice:
    types = tuple(_type_advice(o, away, chosen) for o in options)
    candidates = [t for t in types if t.option.allowed and t.cashflow is not None]
    reasons = [f"El alquiler {LABELS[t.option.rental_type]} no se puede ejercer en este "
               "municipio." for t in types if not t.option.allowed]
    if not candidates:
        return RentalAdvice(types, None, (*reasons, "Ningún tipo que se pueda ejercer tiene "
                                          "cifras para compararlo."))
    habitual = next((t for t in candidates if t.option.rental_type == "habitual"), None)
    order = {name: i for i, name in enumerate(RENTAL_TYPES)}
    best = max(candidates, key=lambda t: (_value(t), -order[t.option.rental_type]))
    if len(candidates) == 1 and habitual is not None:
        reasons.append("El alquiler habitual es el único con renta pública (SERPAVI). Para "
                       "compararlo con otro tipo, escribe lo que esperas sacar con él.")
        best = habitual
    elif risk == "baja" and habitual is not None:
        reasons.append("Con tu riesgo bajo, el alquiler habitual: los otros dependen de una "
                       "renta supuesta y de normas que cambian.")
        best = habitual
    else:
        reasons.append("Es el de mayor cash flow mensual tras impuestos, cada tipo con su "
                       "gestión recomendada.")
    return RentalAdvice(types, best.option.rental_type, tuple(reasons))


def _value(t: TypeAdvice) -> object:
    assert t.cashflow is not None
    return t.cashflow.value


def _type_advice(o: TypeOption, away: bool, chosen: Management | None) -> TypeAdvice:
    management, reason = management_for(o.rental_type, away, chosen)
    notes: list[str] = []
    if o.irpf_reduction is None:
        notes.append(f"Por confirmar si el alquiler {LABELS[o.rental_type]} tiene la reducción "
                     "del IRPF: se calcula sin ella.")
    if o.active is None:
        if o.income is None and o.rental_type != "habitual":
            notes.append(f"Sin renta pública para el alquiler {LABELS[o.rental_type]}: escribe "
                         "lo que esperas sacar al mes para ver sus cifras.")
        return TypeAdvice(o, management, reason, None, None, tuple(notes))
    picked = o.active
    if management == "pasiva":
        if o.passive is None:
            notes.append(f"Falta lo que cobra la gestión: el cash flow del alquiler "
                         f"{LABELS[o.rental_type]} va con gestión activa.")
        else:
            picked = o.passive
    cashflow = replace(picked, key=f"rental.{o.rental_type}.cashflow",
                       formula=f"{picked.formula} (alquiler {LABELS[o.rental_type]}, gestión "
                               f"{'pasiva' if picked is o.passive else 'activa'})")
    cost = None
    if o.passive is not None:
        cost = Figure(f"management.{o.rental_type}.delegation_cost",
                      money(o.active.value - o.passive.value), "EUR/mes",
                      "Cash flow mensual tras impuestos con gestión activa − con gestión pasiva",
                      combine_sources(o.active.sources, o.passive.sources))
    return TypeAdvice(o, management, reason, cashflow, cost, tuple(notes))
