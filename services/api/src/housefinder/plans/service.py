"""Plan completo de una oferta para el perfil del usuario (F6.7, ADR-0025).

Sale del mismo camino que la búsqueda (`search.service.prepare`) y añade la comparación de
hipoteca fija y variable, el estrés con la renta baja de la zona, el plan con las reglas
pendientes, los argumentos para no comprar y la hoja de ruta. No se guarda: se calcula al abrirlo.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from uuid import UUID

from housefinder.core.figures import Figure, Series
from housefinder.db.connection import Connection
from housefinder.db.offers import rent_expectations, search_candidate
from housefinder.engines.rates import MortgageTerms
from housefinder.params.book import ParamBook
from housefinder.planning.arguments import Argument, ArgumentInputs, arguments
from housefinder.planning.ranking import Verdict
from housefinder.planning.scenarios import ScenarioComparison, compare_with_pending
from housefinder.planning.simulate import simulate
from housefinder.plans.coherence import check_plan
from housefinder.plans.roadmap import Step, roadmap
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook
from housefinder.search.rental import OfferRentalAdvice
from housefinder.search.service import (
    ContentCache,
    SearchUnavailable,
    Unscorable,
    cache_context,
    digest,
    evaluate,
    missing_inputs,
    prepare,
)
from housefinder.valuation.assumptions import MissingData, market_assumptions, variable_mortgage
from housefinder.valuation.service import OutsideCoverage

PENDING = "normas-pendientes"


class PlanUnavailable(ValueError):
    """No se puede hacer el plan de esa oferta; el mensaje dice por qué."""


@dataclass(frozen=True)
class PlanSection:
    id: str
    title: str
    figures: tuple[Figure, ...]


@dataclass(frozen=True)
class FullPlan:
    offer_id: UUID
    kind: str  # 'enlace' o 'lote'
    title: str | None
    url: str | None
    auction: bool
    verdict: Verdict
    sections: tuple[PlanSection, ...]
    advice: OfferRentalAdvice | None
    arguments: tuple[Argument, ...]
    roadmap: tuple[Step, ...]
    pending: ScenarioComparison | None
    cheapest_mortgage: str | None  # etiqueta con menos intereses esperados
    safest_mortgage: str | None  # etiqueta con la menor cuota máxima en estrés
    notes: tuple[str, ...]
    # Para las gráficas (ADR-0050); fuera de las secciones y del agente
    series: tuple[Series, ...] = ()
    breakdown: tuple[Figure, ...] = ()

    def figures(self) -> tuple[Figure, ...]:
        """Todas las cifras del plan, cada clave una vez (las del agente y la web)."""
        found: dict[str, Figure] = {}
        groups = [f for s in self.sections for f in s.figures]
        groups += list(self.advice.figures()) if self.advice else []
        groups += [f for a in self.arguments for f in a.figures]
        for figure in groups:
            found.setdefault(figure.key, figure)
        return tuple(found.values())


# Sección de cada cifra por el principio de su clave; las que no están aquí no se muestran
SECTIONS = (
    ("capacidad", "Capacidad de compra", ("affordability.",)),
    ("compra", "Compra", ("offer.price", "valuation.price_total", "purchase_costs.",
                          "cashflow.cash_invested")),
    ("hipoteca", "Hipoteca", ("financing.", "mortgage.monthly_payment",
                              "assumption.mortgage_rate", "assumption.variable_",
                              "mortgage_comparison.")),
    ("explotacion", "Alquiler y cash flow", ("valuation.rent_monthly", "cashflow.gross_yield",
                                             "holding_costs.", "assumption.community_",
                                             "assumption.insurance_", "assumption.maintenance_",
                                             "cashflow.annual_", "cashflow.monthly_after_tax",
                                             "cashflow.cash_on_cash")),
    ("estres", "Prueba de estrés", ("assumption.rate_shock", "mortgage.stressed_payment",
                                    "search.stressed_cashflow", "plan.low_rent_cashflow",
                                    "term.")),
    ("venta", "Venta y rentabilidad", ("irr.", "sale_costs.", "valuation.appreciation_")),
    ("supuestos", "Supuestos del inmueble", ("assumption.cadastral_",
                                             "assumption.construction_")),
)


def full_plan(conn: Connection, book: ParamBook, rules: RuleBook, profile: UserProfile,
              org_id: UUID, offer_id: UUID, today: date | None = None,
              cache: ContentCache[FullPlan] | None = None) -> FullPlan:
    """El plan completo de una oferta. Con `cache`, se reutiliza mientras no cambie nada de lo que
    lo decide (ver `ContentCache`)."""
    today = today or date.today()
    if cache is None or missing_inputs(profile):
        return _full_plan(conn, book, rules, profile, org_id, offer_id, today)
    candidate = search_candidate(conn, org_id, offer_id)
    try:
        market = market_assumptions(conn)
    except MissingData:
        return _full_plan(conn, book, rules, profile, org_id, offer_id, today)
    if candidate is None:
        return _full_plan(conn, book, rules, profile, org_id, offer_id, today)
    expected = rent_expectations(conn, org_id).get(offer_id, {})
    key = (*cache_context(conn, book, rules, profile, market, today), digest(candidate),
           digest(sorted(expected.items())))
    if (hit := cache.get(key)) is not None:
        return hit
    plan = _full_plan(conn, book, rules, profile, org_id, offer_id, today)
    cache.put(key, plan)
    return plan


def _full_plan(conn: Connection, book: ParamBook, rules: RuleBook, profile: UserProfile,
               org_id: UUID, offer_id: UUID, today: date) -> FullPlan:
    missing = missing_inputs(profile)
    if missing:
        raise SearchUnavailable(missing)
    candidate = search_candidate(conn, org_id, offer_id)
    if candidate is None:
        raise PlanUnavailable("No existe esa oferta en tu búsqueda (confirmada y ubicada)")
    notes: list[str] = []
    try:
        market = market_assumptions(conn)
    except MissingData as exc:
        raise SearchUnavailable([str(exc)]) from exc
    alternatives: tuple[MortgageTerms, ...] = ()
    extra: list[Figure] = []
    try:
        variable = variable_mortgage(conn, book, today)
        fixed = MortgageTerms.fixed("fija", market.mortgage_rate.value,
                                    market.mortgage_rate.sources)
        alternatives, extra = (fixed, variable.terms), list(variable.figures())
    except (MissingData, LookupError) as exc:
        notes.append(f"Sin comparación de fija y variable: {exc}")
    try:
        prepared = prepare(conn, book, rules, profile, market, candidate, today, alternatives)
    except (Unscorable, MissingData, OutsideCoverage) as exc:
        raise PlanUnavailable(str(exc)) from exc
    expected = rent_expectations(conn, org_id).get(offer_id, {})
    scored = evaluate(prepared, rules, book, profile, today, expected)
    plan, inp, rent = prepared.plan, prepared.inp, prepared.rent

    low_rent: Figure | None = None
    if rent.low is not None:
        low = simulate(replace(inp, rental=replace(inp.rental, monthly_rent=rent.low)),
                       rules, book, allow_unverified=True)
        base = low.cashflow.monthly_cashflow_after_tax
        low_rent = replace(base, key="plan.low_rent_cashflow",
                           formula=f"{base.formula}, con la renta baja de la zona (P25)")
    pending = compare_with_pending(PENDING, lambda p: simulate(
        inp, rules, book, include_pending=p, allow_unverified=True).figures())
    cash_change = next((c.delta for c in pending.changed
                        if c.key == "cashflow.monthly_after_tax"), None)

    by_key = {f.key: f for f in scored.figures}
    figures = {f.key: f for f in (*plan.figures(), *prepared.valuation_figures,
                                  *prepared.assumed.figures(), prepared.price, rent, *extra,
                                  market.mortgage_rate, market.rate_shock)}
    figures.update({k: v for k, v in by_key.items() if k not in figures})
    if low_rent is not None:
        figures[low_rent.key] = low_rent
    estimated = figures.get("valuation.price_total")
    provisional = any(s.provisional for f in figures.values() for s in f.sources)
    found = arguments(ArgumentInputs(
        price=prepared.price, max_price=plan.affordability.max_price,
        within_budget=plan.within_budget, cash_invested=plan.cashflow.cash_invested,
        savings_ok=plan.cashflow.cash_invested.value <= profile.available_savings,
        cashflow=plan.cashflow.monthly_cashflow_after_tax,
        min_cashflow=profile.min_monthly_cashflow or Decimal(0),
        stressed=by_key.get("search.stressed_cashflow"), low_rent_cashflow=low_rent,
        term_feasible=plan.term.feasible, stressed_payment=plan.stressed_payment,
        irr=plan.irr.irr, mortgage_rate=market.mortgage_rate, estimated_price=estimated,
        pending_delta=cash_change, auction=scored.auction, provisional=provisional))
    advice = scored.advice
    chosen = advice.advice.chosen() if advice else None
    # Un anuncio de un feed de agencia (ADR-0038) es una venta entre particulares, como un enlace.
    steps = roadmap("lote" if candidate.kind == "lote" else "enlace", plan.loan.value > 0,
                    chosen.option.rental_type if chosen else "habitual")
    comparison = plan.comparison
    result = FullPlan(
        candidate.offer_id, candidate.kind, candidate.title, candidate.url, scored.auction,
        scored.verdict, _sections(figures), advice, found, steps, pending,
        comparison.cheapest_expected if comparison else None,
        comparison.lowest_stressed_payment if comparison else None,
        (*scored.notes, *notes), plan.series, plan.cashflow.breakdown)
    # Un fallo de coherencia es un error del programa: el plan lo avisa (ADR-0027)
    issues = check_plan(result)
    if issues:
        result = replace(result, notes=(*result.notes, *(f"Incoherencia del plan (avísanos): "
                                                         f"{i}." for i in issues)))
    return result


def _sections(figures: dict[str, Figure]) -> tuple[PlanSection, ...]:
    result = []
    for section_id, title, prefixes in SECTIONS:
        chosen = tuple(f for f in figures.values()
                       if any(f.key == p or (p.endswith((".", "_")) and f.key.startswith(p))
                              for p in prefixes))
        if chosen:
            result.append(PlanSection(section_id, title, chosen))
    return tuple(result)
