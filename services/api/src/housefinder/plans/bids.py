"""Simulador de puja de una subasta (ADR-0047): el plan del usuario a cada precio.

El valor de subasta es el precio de salida, no el final. Para cada puja se rehace el plan de la
oferta (los mismos supuestos de la búsqueda inversa, con el precio de la puja, las cargas que
subsisten y el coste de recuperar la posesión) y se juzga con las restricciones del usuario. La
puja máxima es la mayor con la que las cumple; la tabla dice qué pasa a cada porcentaje del valor
de subasta, también ante la ley si la subasta es judicial.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from uuid import UUID

from housefinder.core.figures import Figure, SourceRef, combine_sources, money
from housefinder.db.connection import Connection
from housefinder.db.offers import search_candidate
from housefinder.params.book import ParamBook
from housefinder.planning.bids import judicial_auction, judicial_deposit, legal_stage, max_bid
from housefinder.planning.ranking import Verdict
from housefinder.planning.simulate import InvestmentSimulation, SimulationInput, simulate
from housefinder.plans.service import PlanUnavailable
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook
from housefinder.search.service import (
    AUCTION,
    Prepared,
    SearchUnavailable,
    Unscorable,
    judge_plan,
    missing_inputs,
    prepare,
)
from housefinder.valuation.assumptions import MissingData, market_assumptions
from housefinder.valuation.service import OutsideCoverage

LEVELS = tuple(Decimal(p) / 100 for p in (40, 50, 60, 70, 80, 90, 100))  # del valor de subasta
STEP = Decimal(100)  # la puja máxima, en múltiplos de 100 €
CEILING = Decimal(2)  # se busca hasta el doble del valor de subasta
USER_VALUE = SourceRef("user_input", "valor-de-subasta")
CHARGES = SourceRef("user_input", "cargas-que-subsisten")
POSSESSION = SourceRef("assumption", "coste-de-posesion", provisional=True)
CASH = SourceRef("user_input", "pago-al-contado")


@dataclass(frozen=True)
class BidLevel:
    share: Decimal  # del valor de subasta
    price: Figure
    cashflow: Figure  # mensual tras impuestos
    stressed: Figure | None
    irr: Figure | None
    verdict: Verdict
    stage: str | None  # qué pasa ante la ley (solo subasta judicial)


@dataclass(frozen=True)
class BidSimulation:
    offer_id: UUID
    title: str | None
    url: str | None
    auction_value: Figure
    deposit: Figure | None
    max_bid: Figure | None  # None: ni con la puja más baja cumple
    levels: tuple[BidLevel, ...]
    notes: tuple[str, ...]


def bid_simulation(
    conn: Connection,
    book: ParamBook,
    rules: RuleBook,
    profile: UserProfile,
    org_id: UUID,
    offer_id: UUID,
    auction_value: Decimal | None = None,
    charges: Decimal = Decimal(0),
    possession: Decimal = Decimal(0),
    cash: bool = False,
    judicial: bool = False,
    today: date | None = None,
) -> BidSimulation:
    """El plan del usuario a cada puja de una subasta.

    `auction_value`: el valor de subasta si no lo trae la oferta (o para corregirlo). `charges`:
    cargas anteriores que subsisten y asume quien puja (LEC, art. 669.2). `possession`: coste
    supuesto de recuperar la posesión. `cash`: sin hipoteca (el resto del precio se paga en pocos
    días). `judicial`: subasta judicial, con el depósito y las fases de la LEC.
    """
    today = today or date.today()
    missing = missing_inputs(profile)
    if missing:
        raise SearchUnavailable(missing)
    candidate = search_candidate(conn, org_id, offer_id)
    if candidate is None:
        raise PlanUnavailable("No existe esa oferta en tu búsqueda (confirmada y ubicada)")
    value = auction_value or candidate.auction_min_bid
    if value is None or value <= 0:
        raise PlanUnavailable("Falta el valor de subasta: indícalo para simular las pujas")
    try:
        market = market_assumptions(conn)
        prepared = prepare(conn, book, rules, profile, market, candidate, today)
    except MissingData as exc:
        raise SearchUnavailable([str(exc)]) from exc
    except (Unscorable, OutsideCoverage) as exc:
        raise PlanUnavailable(str(exc)) from exc

    value_figure = Figure(
        "bids.auction_value", money(value), "EUR",
        "valor de subasta indicado" if auction_value else "tipo de la subasta del anuncio",
        (USER_VALUE,) if auction_value else (AUCTION,))
    extra = _extra_sources(charges, possession, cash)
    notes: list[str] = list(prepared.notes)
    deposit: Figure | None = None
    stage_rules = None
    if judicial:
        stage_rules, rule_ref = judicial_auction(rules, today, allow_unverified=True)
        deposit = Figure(
            "bids.deposit", judicial_deposit(value, stage_rules), "EUR",
            f"{stage_rules.deposit_rate} × valor de subasta, con un mínimo de "
            f"{stage_rules.deposit_min} €; el letrado puede subirlo o bajarlo",
            (*value_figure.sources, rule_ref))
        notes.append("Si es la vivienda habitual del deudor, las fases cambian: el aviso de cada "
                     "puja lo dice. Sin el expediente no se sabe.")
    elif candidate.deposit_required:
        deposit = Figure("bids.deposit", money(candidate.deposit_required), "EUR",
                         "depósito que pide el anuncio", (AUCTION,))
    if charges:
        notes.append("Las cargas anteriores subsisten y las paga quien se adjudica (LEC, art. "
                     "669.2): se suman al coste de compra.")
    else:
        notes.append("Sin cargas que subsistan indicadas: compruébalas en la certificación de "
                     "cargas del expediente antes de pujar.")
    if cash:
        notes.append("Al contado: sin hipoteca.")
    else:
        notes.append("Con hipoteca: el resto del precio se paga a los pocos días de aprobarse el "
                     "remate, y conseguir el préstamo a tiempo no es seguro.")

    def plan_at(price: Decimal) -> tuple[InvestmentSimulation, Verdict, Figure | None]:
        inp = _input_at(prepared, price, charges + possession, cash)
        plan = simulate(inp, rules, book, allow_unverified=True)
        verdict, stressed = judge_plan(plan, inp, prepared.rent, rules, book, profile)
        return plan, verdict, stressed

    levels = []
    for share in LEVELS:
        price = money(value * share)
        plan, verdict, stressed = plan_at(price)
        levels.append(BidLevel(
            share,
            Figure(f"bids.price_{int(share * 100)}", price, "EUR",
                   f"{share} × valor de subasta", value_figure.sources),
            _with(plan.cashflow.monthly_cashflow_after_tax, extra), stressed,
            plan.irr.irr, verdict,
            legal_stage(share, stage_rules) if stage_rules is not None else None))

    best = max_bid(lambda p: plan_at(p)[1].passes, STEP, value * CEILING, STEP)
    best_figure: Figure | None = None
    if best is not None:
        plan, _, _ = plan_at(best)
        best_figure = Figure(
            "bids.max_bid", best, "EUR",
            f"mayor puja, en múltiplos de {STEP} €, con la que el plan cumple tus restricciones "
            f"(capacidad, ahorro y cash flow mínimo en tu escenario de riesgo), buscada hasta "
            f"{CEILING} × valor de subasta",
            combine_sources(plan.cashflow.monthly_cashflow_after_tax.sources, extra))
        if best >= money(value * CEILING):
            notes.append("Cumple incluso al doble del valor de subasta: el límite lo pone la "
                         "competencia, no tu plan.")
    else:
        notes.append("Ni con la puja más baja cumple tus restricciones: el problema no es el "
                     "precio (renta, gastos o tu ahorro).")
    return BidSimulation(candidate.offer_id, candidate.title, candidate.url, value_figure,
                         deposit, best_figure, tuple(levels), tuple(notes))


def _input_at(p: Prepared, price: Decimal, extra_costs: Decimal, cash: bool) -> SimulationInput:
    """Las entradas del plan con el precio de la puja; la construcción, en la misma proporción."""
    prop = p.inp.property
    share = prop.construction_value / prop.price
    financing = replace(p.inp.financing, loan=Decimal(0)) if cash else p.inp.financing
    return replace(p.inp, financing=financing, property=replace(
        prop, price=price, construction_value=money(price * share),
        renovation=prop.renovation + extra_costs))


def _extra_sources(charges: Decimal, possession: Decimal, cash: bool) -> tuple[SourceRef, ...]:
    return ((CHARGES,) if charges else ()) + ((POSSESSION,) if possession else ()) + \
        ((CASH,) if cash else ())


def _with(figure: Figure, extra: tuple[SourceRef, ...]) -> Figure:
    return replace(figure, sources=combine_sources(figure.sources, extra)) if extra else figure
