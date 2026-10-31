"""Búsqueda inversa: el plan del usuario en cada oferta, y cuáles le encajan (F6.5, ADR-0023).

Para cada oferta ubicada (las del usuario y los lotes del BOE): renta estimada (F5), supuestos
estimados desde fuentes públicas (ADR-0022), revalorización del escenario base (F5.5) y el plan con
`planning.simulate`, el único camino de cálculo (D4). `planning.ranking` decide qué ofertas pasan
las restricciones del usuario y en qué orden. Lo que no se puede puntuar sale con su motivo.

Las cifras dependen de reglas sin verificar (impuestos, IBI): salen PROVISIONALES hasta que se
verifiquen (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from housefinder.core.figures import Figure, SourceRef, money, ratio
from housefinder.db.connection import Connection
from housefinder.db.offers import SearchCandidate, rent_expectations, search_candidates
from housefinder.params.book import ParamBook
from housefinder.planning.ranking import Outcome, Verdict, judge, rank, stress_rent
from housefinder.planning.simulate import (
    AppreciationAlternative,
    BuyerInput,
    ExitInput,
    FinancingInput,
    InvestmentSimulation,
    PropertyInput,
    RentalInput,
    SimulationInput,
    simulate,
)
from housefinder.profiles.model import UserProfile
from housefinder.regulation.kinds import RentalFacts
from housefinder.regulation.rules import RuleBook
from housefinder.search.rental import OfferRentalAdvice, rental_advice
from housefinder.valuation.assumptions import (
    MarketAssumptions,
    MissingData,
    PropertyAssumptions,
    market_assumptions,
    property_assumptions,
)
from housefinder.valuation.scenarios import NoScenarios, appreciation_scenarios
from housefinder.valuation.service import OutsideCoverage, value_property

DEFAULT_HORIZON = 10  # años, si el perfil no dice su horizonte (el de la TIR del simulador)
ASKED = SourceRef("user_input", "anuncio-confirmado")
AUCTION = SourceRef("dataset", "boe-tipo-de-subasta")
NO_SCENARIO = SourceRef("assumption", "sin-escenario-de-revalorizacion", provisional=True)


class SearchUnavailable(ValueError):
    """El perfil no tiene lo necesario para puntuar: `reasons` dice qué falta, sin valores."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass(frozen=True)
class Scored:
    offer_id: UUID
    kind: str  # 'enlace' o 'lote'
    title: str | None
    url: str | None
    auction: bool  # el precio es el tipo de una subasta, no un precio pedido
    verdict: Verdict
    figures: tuple[Figure, ...]  # precio, renta, plan y supuestos de esta oferta
    notes: tuple[str, ...] = ()
    advice: OfferRentalAdvice | None = None  # tipo de alquiler y gestión (F6.6)


@dataclass(frozen=True)
class Skipped:
    offer_id: UUID
    title: str | None
    reason: str


@dataclass(frozen=True)
class SearchReport:
    ranked: list[Scored]  # las que pasan primero, en orden
    skipped: list[Skipped]
    market: tuple[Figure, ...]  # tipo y subida del estrés, comunes a todas
    notes: list[str] = field(default_factory=list)


def search(conn: Connection, book: ParamBook, rules: RuleBook, profile: UserProfile,
           org_id: UUID, today: date | None = None) -> SearchReport:
    today = today or date.today()
    missing = missing_inputs(profile)
    if missing:
        raise SearchUnavailable(missing)
    try:
        market = market_assumptions(conn)
    except MissingData as exc:
        raise SearchUnavailable([str(exc)]) from exc
    scored: dict[str, Scored] = {}
    skipped: list[Skipped] = []
    expected = rent_expectations(conn, org_id)
    for candidate in search_candidates(conn, org_id):
        try:
            result = _score(conn, book, rules, profile, market, candidate, today,
                            expected.get(candidate.offer_id, {}))
        except (_Unscorable, MissingData, OutsideCoverage, LookupError,
                ValueError) as exc:  # una regla que falta (LookupError) solo afecta a esa oferta
            skipped.append(Skipped(candidate.offer_id, candidate.title, str(exc)))
            continue
        scored[str(candidate.offer_id)] = result
    order = rank({k: v.verdict for k, v in scored.items()})
    return SearchReport([scored[k] for k in order], skipped,
                        (market.mortgage_rate, market.rate_shock),
                        ["Las cifras dependen de reglas sin verificar: son provisionales."])


def missing_inputs(profile: UserProfile) -> list[str]:
    """Lo que el perfil necesita para la búsqueda y no tiene, en palabras."""
    reasons = []
    if profile.taxable_base is None:
        reasons.append("Falta tu base liquidable general: sube tu declaración de la renta o "
                       "escríbela en el perfil")
    labels = {"vacancy_rate": "los meses vacío al año",
              "other_purchase_cost_rate": "la gestoría y la tasación",
              "sale_cost_rate": "los gastos de venta",
              "large_holder": "si eres gran tenedor"}
    if profile.management == "pasiva":
        labels["management_fee_rate"] = "lo que cobra la gestión"
    absent = [text for name, text in labels.items() if getattr(profile, name) is None]
    if absent:
        reasons.append("Faltan supuestos de búsqueda en tu perfil: " + ", ".join(absent))
    return reasons


class _Unscorable(Exception):
    """La oferta no se puede puntuar; el mensaje dice por qué."""


def _score(conn: Connection, book: ParamBook, rules: RuleBook, profile: UserProfile,
           market: MarketAssumptions, c: SearchCandidate, today: date,
           expected: dict[str, Decimal] | None = None) -> Scored:
    extracted = c.extracted or {}
    listing = extracted.get("listing") or {}
    property_type = listing.get("property_type") if c.kind == "enlace" \
        else extracted.get("property_type")
    if property_type not in (None, "vivienda") or (c.kind == "lote" and property_type is None):
        raise _Unscorable(f"No es una vivienda ({property_type or 'tipo sin saber'})")
    confirmed = extracted.get("confirmed") or {}
    if c.kind == "enlace" and confirmed.get("operation") != "venta":
        raise _Unscorable("No es una venta")
    price = c.asking_price or c.auction_min_bid
    if price is None or price <= 0:
        raise _Unscorable("No tiene precio")
    if c.built_area_m2 is None or c.built_area_m2 <= 0:
        raise _Unscorable("Falta la superficie construida")
    municipality = c.section_code[:5]
    region = provinces().get(municipality[:2])
    if region is None:
        raise _Unscorable(f"No se sabe la comunidad de la provincia {municipality[:2]}")

    valuation = value_property(conn, book, c.lon, c.lat, c.built_area_m2, on=today)
    rent = next(f for f in valuation.figures if f.key == "valuation.rent_monthly")
    fees = (confirmed.get("fields") or {}).get("community_fees", {}).get("value")
    assumed = property_assumptions(conn, municipality, region, price,
                                   Decimal(str(fees)) if fees else None)
    horizon = profile.horizon_years or DEFAULT_HORIZON
    notes: list[str] = []
    try:
        scenarios = appreciation_scenarios(conn, book, municipality, horizon, on=today)
        base = scenarios.scenarios["base"]
        appreciation, sources = base.rate, base.sources
        alternatives = tuple(AppreciationAlternative(name, s.rate, s.sources)
                             for name, s in scenarios.scenarios.items() if name != "base")
    except NoScenarios:
        # El cash flow no depende de la revalorización; la TIR sí, y se dice
        appreciation, sources, alternatives = Decimal(0), (NO_SCENARIO,), ()
        notes.append("Sin escenarios de revalorización para el municipio: la TIR sale sin "
                     "revalorizar.")
    inp = _input(profile, market, assumed, price, f"ES-{region}-{municipality}", rent.value,
                 today, horizon, appreciation, sources, alternatives)
    try:
        plan = simulate(inp, rules, book, allow_unverified=True)
    except LookupError as exc:
        if "plusvalia" not in str(exc):
            raise
        # Sin regla de la plusvalía municipal del municipio: el plan sin ella, y se dice
        inp = replace(inp, property=replace(inp.property, cadastral_land_value=None))
        plan = simulate(inp, rules, book, allow_unverified=True)
        notes.append("Sin la plusvalía municipal de la venta: no hay regla de su tipo para el "
                     "municipio. La TIR sale algo alta.")

    stressed: Figure | None = None
    which = stress_rent(profile.risk_tolerance)
    if which is not None:
        stress_plan = plan
        if which == "p25" and rent.low is not None:
            stress_plan = simulate(replace(inp, rental=replace(inp.rental,
                                                               monthly_rent=rent.low)),
                                   rules, book, allow_unverified=True)
        stressed = _stressed(stress_plan, which)
    cash = plan.cashflow
    outcome = Outcome(
        cashflow=cash.monthly_cashflow_after_tax, stressed_cashflow=stressed, irr=plan.irr.irr,
        within_budget=plan.within_budget,
        savings_ok=cash.cash_invested.value <= profile.available_savings)
    verdict = judge(outcome, profile.risk_tolerance, profile.goal,
                    profile.min_monthly_cashflow or Decimal(0))
    asked = Figure("offer.price", money(price), "EUR",
                   "Tipo de la subasta del BOE" if c.asking_price is None
                   else "Precio que pide el anuncio, confirmado",
                   (AUCTION if c.asking_price is None else ASKED,))
    figures = [asked, rent, cash.monthly_cashflow_after_tax, cash.cash_invested,
               cash.gross_yield, plan.monthly_payment, plan.loan, plan.ibi_annual]
    if stressed is not None:
        figures.append(stressed)
    if plan.irr.irr is not None:
        figures.append(plan.irr.irr)
    figures += list(assumed.figures())
    warnings = [w for w in plan.warnings
                if not (notes and w.startswith("Falta el valor catastral del suelo"))]
    notes = list(valuation.notes[:1]) + notes + warnings
    if c.asking_price is None:
        notes.append("Es una subasta: el precio es el tipo de salida y el final puede ser otro.")
    try:
        advice = rental_advice(inp, rent, assumed.maintenance_annual.value, rules, book, profile,
                               expected or {}, today)
    except (LookupError, ValueError) as exc:  # sin recomendación, la oferta se puntúa igual
        advice = None
        notes.append(f"Sin recomendación de tipo de alquiler: {exc}")
    return Scored(c.offer_id, c.kind, c.title, c.url, c.asking_price is None, verdict,
                  tuple(figures), tuple(notes), advice)


def _input(profile: UserProfile, market: MarketAssumptions, assumed: PropertyAssumptions,
           price: Decimal, territory: str, rent: Decimal, today: date, horizon: int,
           appreciation: Decimal, appreciation_sources: tuple[SourceRef, ...],
           alternatives: tuple[AppreciationAlternative, ...]) -> SimulationInput:
    management = profile.management_fee_rate if profile.management != "activa" else Decimal(0)
    return SimulationInput(
        buyer=BuyerInput(
            net_monthly_income=profile.net_monthly_income,
            existing_monthly_debt=profile.existing_monthly_debt,
            available_savings=profile.available_savings,
            age=today.year - profile.birth_year, residence=profile.residence,
            taxable_base=profile.taxable_base,
            descendant_ages=tuple(today.year - y for y in profile.descendant_birth_years),
            savings_base=profile.savings_base),
        property=PropertyInput(
            price=price, territory=territory,
            construction_value=assumed.construction_value.value,
            other_purchase_cost_rate=profile.other_purchase_cost_rate or Decimal(0),
            community_fees_monthly=assumed.community_fees_monthly.value,
            insurance_annual=assumed.insurance_annual.value,
            cadastral_value=assumed.cadastral_value.value,
            cadastral_land_value=assumed.cadastral_land_value.value),
        financing=FinancingInput(annual_rate=market.mortgage_rate.value,
                                 rate_shock=market.rate_shock.value),
        rental=RentalInput(
            monthly_rent=rent, vacancy_rate=profile.vacancy_rate or Decimal(0),
            management_fee_rate=management or Decimal(0),
            maintenance_reserve_rate=ratio(assumed.maintenance_annual.value / (rent * 12)),
            situation=RentalFacts(contract="primer-alquiler",
                                  large_holder=bool(profile.large_holder)),
            contract_date=today),
        exit=ExitInput(appreciation_rate=appreciation,
                       sale_cost_rate=profile.sale_cost_rate or Decimal(0),
                       horizon_years=horizon, appreciation_sources=appreciation_sources,
                       alternatives=alternatives),
        purchase_date=today)


def _stressed(plan: InvestmentSimulation, rent: str) -> Figure:
    """Cash flow tras impuestos con la cuota de la subida de tipos (sin recalcular el IRPF)."""
    cash = plan.cashflow.monthly_cashflow_after_tax
    extra = plan.stressed_payment.value - plan.monthly_payment.value
    label = "renta baja de la zona (P25)" if rent == "p25" else "renta mediana"
    return Figure(
        "search.stressed_cashflow", money(cash.value - extra), "EUR/mes",
        f"Cash flow tras impuestos con la {label} − (cuota con la subida de tipos − cuota): sin "
        "recalcular el IRPF, que bajaría algo con más intereses",
        tuple(dict.fromkeys((*cash.sources, *plan.stressed_payment.sources))))


@lru_cache
def provinces() -> dict[str, str]:
    path = Path(__file__).resolve().parents[3] / "data" / "territory" / "provincias.yaml"
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}
