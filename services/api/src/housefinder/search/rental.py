"""Tipo de alquiler y gestión de una oferta: la normativa de cada tipo y su plan (F6.6, ADR-0024).

Para cada tipo de `RENTAL_TYPES`: su régimen en el municipio (F2.4), la renta (SERPAVI para el
habitual; para los demás, la que espera el usuario, si la ha escrito) y el plan con gestión activa
y pasiva por `planning.simulate` (D4). `planning.rental_advice` decide. Debajo, lo que cambiaría
si se convalidan las reglas pendientes, y si el municipio es zona tensionada.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, money, ratio
from housefinder.params.book import ParamBook
from housefinder.planning.rental_advice import LABELS, RentalAdvice, TypeOption, advise
from housefinder.planning.simulate import SimulationInput, simulate
from housefinder.profiles.model import UserProfile
from housefinder.regulation.kinds import RENTAL_TYPES
from housefinder.regulation.resolvers import RentalRegimeResult, rental_regime, stressed_zone
from housefinder.regulation.rules import RuleBook

EXPECTED_INCOME = ("Lo que el usuario espera sacar al mes de media a lo largo del año, con los "
                   "meses vacíos y sin limpieza, suministros ni comisiones de las plataformas")


@dataclass(frozen=True)
class OfferRentalAdvice:
    advice: RentalAdvice
    scenario: tuple[str, ...]  # lo que cambiaría con las reglas pendientes
    notes: tuple[str, ...]  # zona tensionada, notas fiscales

    def figures(self) -> tuple[Figure, ...]:
        return self.advice.figures()


def rental_advice(inp: SimulationInput, rent: Figure, maintenance_annual: Decimal,
                  rules: RuleBook, book: ParamBook, profile: UserProfile,
                  expectations: dict[str, Decimal], today: date) -> OfferRentalAdvice:
    """`inp` es el plan de la búsqueda (habitual, gestión del usuario) y `rent` la renta del
    SERPAVI; `expectations`, lo que el usuario espera sacar con los demás tipos."""
    territory = inp.property.territory
    options: list[TypeOption] = []
    notes: list[str] = []
    scenario: list[str] = []
    for rental_type in RENTAL_TYPES:
        try:
            regime = rental_regime(rules, rental_type, territory, today, allow_unverified=True)
        except LookupError:
            notes.append(f"No hay normativa cargada del alquiler {LABELS[rental_type]} para el "
                         "municipio.")
            continue
        income, vacancy = _income(rental_type, rent, expectations, inp)
        active = passive = None
        if income is not None:
            active = _cashflow(inp, rules, book, income.value, vacancy, Decimal(0),
                               maintenance_annual, regime)
            if profile.management_fee_rate is not None:
                passive = _cashflow(inp, rules, book, income.value, vacancy,
                                    profile.management_fee_rate, maintenance_annual, regime)
        options.append(TypeOption(
            rental_type, regime.allowed, regime.regime, regime.requirements,
            regime.irpf_reduction, regime.tax_notes, tuple(r.id for r in regime.rules),
            income, active, passive))
        if income is not None:
            notes += [f"Alquiler {LABELS[rental_type]}: {n}" for n in regime.tax_notes]
        scenario += _changes(rules, rental_type, territory, today, regime)
    region = territory.rsplit("-", 1)[0]
    away = region != profile.residence
    advice = advise(options, profile.risk_tolerance, profile.management, away)
    return OfferRentalAdvice(advice, tuple(scenario), (*_zone(rules, territory, today), *notes))


def _income(rental_type: str, rent: Figure, expectations: dict[str, Decimal],
            inp: SimulationInput) -> tuple[Figure | None, Decimal]:
    key = f"rental.{rental_type}.income"
    if rental_type == "habitual":
        return replace(rent, key=key), inp.rental.vacancy_rate
    expected = expectations.get(rental_type)
    if expected is None:
        return None, Decimal(0)
    # El ingreso medio ya lleva los meses vacíos: sin vacío aparte
    return Figure(key, money(expected), "EUR/mes", EXPECTED_INCOME,
                  (SourceRef("assumption", f"renta-esperada-{rental_type}",
                             provisional=True),)), Decimal(0)


def _cashflow(inp: SimulationInput, rules: RuleBook, book: ParamBook, income: Decimal,
              vacancy: Decimal, fee: Decimal, maintenance_annual: Decimal,
              regime: RentalRegimeResult) -> Figure:
    rental = replace(
        inp.rental, monthly_rent=income, vacancy_rate=vacancy, management_fee_rate=fee,
        maintenance_reserve_rate=ratio(maintenance_annual / (income * 12)),
        housing_lease=regime.irpf_reduction is True,
        housing_lease_sources=tuple(r.ref for r in regime.rules))
    plan = simulate(replace(inp, rental=rental), rules, book, allow_unverified=True)
    return plan.cashflow.monthly_cashflow_after_tax


def _changes(rules: RuleBook, rental_type: str, territory: str, today: date,
             base: RentalRegimeResult) -> list[str]:
    """Lo que cambiaría en un tipo si se convalidan las reglas pendientes (F2.5)."""
    try:
        pending = rental_regime(rules, rental_type, territory, today, include_pending=True,
                                allow_unverified=True)
    except LookupError:
        return []
    label = f"Alquiler {LABELS[rental_type]}"
    changes = []
    if pending.regime != base.regime:
        changes.append(f"{label}: pasaría a «{pending.regime}».")
    if pending.allowed != base.allowed:
        changes.append(f"{label}: {'se podría' if pending.allowed else 'no se podría'} ejercer.")
    if pending.irpf_reduction != base.irpf_reduction:
        changes.append(f"{label}: " + {True: "tendría la reducción del IRPF.",
                                       False: "no tendría la reducción del IRPF.",
                                       None: "su reducción del IRPF quedaría por confirmar."}
                       [pending.irpf_reduction])
    before = {r.code for r in base.requirements}
    changes += [f"{label}, requisito nuevo: {r.description}." for r in pending.requirements
                if r.code not in before]
    after = {r.code for r in pending.requirements}
    changes += [f"{label}, deja de exigirse: {r.description}." for r in base.requirements
                if r.code not in after]
    return changes


def _zone(rules: RuleBook, territory: str, today: date) -> list[str]:
    try:
        zone = stressed_zone(rules, territory, today, allow_unverified=True)
    except LookupError:
        return ["No consta revisado si el municipio es zona de mercado residencial tensionado."]
    if zone.declared:
        return ["El municipio es zona de mercado residencial tensionado: los límites a la renta "
                "del alquiler habitual no se modelan."]
    return [f"El municipio no está declarado zona tensionada (revisadas las resoluciones hasta "
            f"el {zone.checked_through.isoformat()})."]
