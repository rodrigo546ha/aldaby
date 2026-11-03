"""Simuladores (F1): capacidad de compra e inversión de punta a punta.

La API solo traduce: valida la petición, llama a `planning` (D4) y devuelve las `Figure`
tal cual. Los importes viajan como texto para no perder precisión (D11).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from housefinder.core.figures import Figure, SourceRef
from housefinder.db.connection import DatabaseUnavailable
from housefinder.engines import mortgage
from housefinder.engines.rates import MortgageTerms
from housefinder.params.bank import bank_criteria
from housefinder.planning.scenarios import compare_with_pending
from housefinder.planning.simulate import (
    FINANCING,
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
from housefinder.regulation.kinds import RentalFacts
from housefinder.valuation.scenarios import NoScenarios

from .deps import ParamBookDep, RuleBookDep, ScenarioFinderDep
from .figures import FigureOut, SeriesOut, SourceOut, figure_out, series_out

router = APIRouter(prefix="/simulate", tags=["simuladores"])

# La capacidad de compra aún no depende de la ubicación: criterios de ámbito nacional.
AFFORDABILITY_TERRITORY = "ES"
# Ninguna regla está verificada todavía (F2.3): se usan y las cifras salen PROVISIONALES.
ALLOW_UNVERIFIED = True
PENDING_SCENARIO = "normativa-pendiente"

Rate = Field(ge=0, le=1)


# --- Capacidad de compra -----------------------------------------------------------------


class AffordabilityRequest(BaseModel):
    net_monthly_income: Decimal = Field(gt=0)
    existing_monthly_debt: Decimal = Field(ge=0, default=Decimal(0))
    available_savings: Decimal = Field(ge=0)
    age: int = Field(ge=18, le=90)
    annual_rate: Decimal = Field(ge=0, le=Decimal("0.2"))
    # Tasa de gastos de compra enviada por el cliente: la simulación de inversión la resuelve.
    purchase_cost_rate: Decimal = Field(ge=0, le=Decimal("0.3"))


class AffordabilityResponse(BaseModel):
    max_price: FigureOut
    max_loan: FigureOut
    max_payment: FigureOut
    years: FigureOut
    binding_constraint: str


@router.post("/affordability")
def simulate_affordability(
    req: AffordabilityRequest, params: ParamBookDep
) -> AffordabilityResponse:
    try:
        criteria = bank_criteria(params, AFFORDABILITY_TERRITORY, date.today())
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        result = mortgage.affordability(
            mortgage.BuyerFinances(
                net_monthly_income=req.net_monthly_income,
                existing_monthly_debt=req.existing_monthly_debt,
                available_savings=req.available_savings,
                age=req.age,
            ),
            annual_rate=req.annual_rate,
            purchase_cost_rate=req.purchase_cost_rate,
            criteria=criteria,
            rate_sources=(SourceRef("user_input", "tipo-de-interes"),),
            purchase_cost_sources=(
                SourceRef("user_input", "tasa-de-gastos-de-compra", provisional=True),
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AffordabilityResponse(
        max_price=figure_out(result.max_price),
        max_loan=figure_out(result.max_loan),
        max_payment=figure_out(result.max_payment),
        years=figure_out(result.years),
        binding_constraint=result.binding_constraint,
    )


# --- Inversión ---------------------------------------------------------------------------


class BuyerRequest(BaseModel):
    net_monthly_income: Decimal = Field(gt=0)
    existing_monthly_debt: Decimal = Field(ge=0, default=Decimal(0))
    available_savings: Decimal = Field(ge=0)
    age: int = Field(ge=18, le=90)
    residence: str = Field(
        pattern=r"^ES-\d{2}(-\d{2})?$",
        description="Comunidad de residencia (ES-13); en el País Vasco, el territorio "
        "histórico (ES-16-48)",
    )
    taxable_base: Decimal | None = Field(
        default=None, ge=0, description="Base liquidable general sin el alquiler"
    )
    descendant_ages: list[int] = Field(default_factory=list)
    marginal_rate: Decimal | None = Field(
        default=None, ge=0, le=1, description="Supuesto si no se conoce la base"
    )
    savings_base: Decimal = Field(
        default=Decimal(0), ge=0, description="Base del ahorro del año de la venta, sin ella"
    )


class PropertyRequest(BaseModel):
    price: Decimal = Field(gt=0)
    territory: str = Field(pattern=r"^ES-\d{2}-\d{5}$", description="Municipio (ES-13-28079)")
    construction_value: Decimal = Field(ge=0, description="Base de la amortización fiscal")
    other_purchase_cost_rate: Decimal = Field(
        ge=0, le=Decimal("0.3"), description="Gestoría, tasación y copias"
    )
    community_fees_monthly: Decimal = Field(ge=0)
    insurance_annual: Decimal = Field(ge=0)
    renovation: Decimal = Field(ge=0, default=Decimal(0))
    new_build: bool = False
    cadastral_value: Decimal | None = Field(default=None, ge=0)
    ibi_annual: Decimal | None = Field(default=None, ge=0)
    cadastral_land_value: Decimal | None = Field(
        default=None, ge=0, description="Valor catastral del suelo, para la plusvalía"
    )
    deed_agreement: Literal["ley", "comprador", "vendedor"] = Field(
        default="ley", description="Quién paga la escritura de compra; «ley»: Código Civil"
    )


class OfferRequest(BaseModel):
    label: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    initial_rate: Decimal = Field(ge=0, le=Decimal("0.2"))
    initial_months: int = Field(ge=0, description="Meses a tipo inicial; ≥ plazo = fija")
    spread: Decimal = Field(default=Decimal(0), ge=0, le=Decimal("0.1"))
    revision_months: int = Field(default=12, gt=0)


class FinancingRequest(BaseModel):
    annual_rate: Decimal = Field(ge=0, le=Decimal("0.2"))
    rate_shock: Decimal = Field(ge=0, le=Decimal("0.1"))
    loan: Decimal | None = Field(default=None, ge=0)
    years: int | None = Field(default=None, gt=0, le=50)
    alternatives: list[OfferRequest] = Field(default_factory=list)


class RentalRequest(BaseModel):
    monthly_rent: Decimal = Field(gt=0)
    vacancy_rate: Decimal = Rate
    management_fee_rate: Decimal = Rate
    maintenance_reserve_rate: Decimal = Rate
    situation: RentalFacts
    contract_date: date


class ExitRequest(BaseModel):
    appreciation_rate: Decimal | None = Field(
        default=None, ge=Decimal("-0.2"), le=Decimal("0.2"),
        description="Revalorización anual supuesta. Vacía: escenarios del municipio (F5.5)")
    sale_cost_rate: Decimal = Field(
        ge=0, le=Decimal("0.2"), description="Agencia y otros gastos de venta de mercado"
    )
    horizon_years: int = Field(default=10, ge=1, le=40)


class InvestmentRequest(BaseModel):
    buyer: BuyerRequest
    property: PropertyRequest
    financing: FinancingRequest
    rental: RentalRequest
    exit: ExitRequest
    purchase_date: date | None = Field(default=None, description="Por defecto, hoy")

    def to_input(self) -> SimulationInput:
        b, p, f, r, e = self.buyer, self.property, self.financing, self.rental, self.exit
        return SimulationInput(
            buyer=BuyerInput(
                net_monthly_income=b.net_monthly_income,
                existing_monthly_debt=b.existing_monthly_debt,
                available_savings=b.available_savings,
                age=b.age,
                residence=b.residence,
                taxable_base=b.taxable_base,
                descendant_ages=tuple(b.descendant_ages),
                marginal_rate=b.marginal_rate,
            ),
            property=PropertyInput(**p.model_dump()),
            financing=FinancingInput(
                annual_rate=f.annual_rate,
                rate_shock=f.rate_shock,
                loan=f.loan,
                years=f.years,
                alternatives=tuple(
                    MortgageTerms(**o.model_dump(), sources=(FINANCING,))
                    for o in f.alternatives
                ),
            ),
            rental=RentalInput(**{**r.model_dump(exclude={"situation"}),
                                  "situation": r.situation}),
            exit=ExitInput(appreciation_rate=e.appreciation_rate or Decimal(0),
                           sale_cost_rate=e.sale_cost_rate, horizon_years=e.horizon_years),
            purchase_date=self.purchase_date or date.today(),
        )


class ComparisonOut(BaseModel):
    labels: list[str]
    cheapest_expected: str
    lowest_stressed_payment: str


class ScenarioChangeOut(BaseModel):
    key: str
    base: FigureOut
    scenario: FigureOut
    delta: FigureOut


class ScenarioOut(BaseModel):
    name: str
    changes: list[ScenarioChangeOut]  # solo las cifras que cambian
    new_rules: list[SourceOut]


class InvestmentResponse(BaseModel):
    figures: dict[str, FigureOut]
    within_budget: bool
    binding_constraint: str
    term_feasible: bool
    no_irr_reason: str
    comparison: ComparisonOut | None
    pending_scenario: ScenarioOut
    warnings: list[str]
    appreciation_notes: list[str] = []  # de dónde salen los escenarios, si se usaron
    # Para las gráficas (ADR-0050): año a año y el primer año por partes, en €/año
    series: list[SeriesOut] = []
    breakdown: list[FigureOut] = []


def _with_scenarios(inp: SimulationInput, find: ScenarioFinderDep,
                    new_build: bool) -> tuple[SimulationInput, list[Figure], list[str]]:
    """Revalorización vacía: escenario base al plan y TIR de los otros dos (F5.5)."""
    code = inp.property.territory.rsplit("-", 1)[-1]
    if not (code.isdigit() and len(code) == 5):
        raise HTTPException(status_code=422, detail="Indica la revalorización o un municipio "
                                                     "con su código INE (ES-13-28079)")
    try:
        report = find(code, inp.exit.horizon_years, new_build)
    except NoScenarios as exc:
        raise HTTPException(status_code=422, detail=f"{exc}: indica la revalorización") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    base = report.scenarios["base"]
    exit_ = replace(inp.exit, appreciation_rate=base.rate, appreciation_sources=base.sources,
                    alternatives=tuple(AppreciationAlternative(name, s.rate, s.sources)
                                       for name, s in report.scenarios.items()
                                       if name != "base"))
    return replace(inp, exit=exit_), report.figures, report.notes


@router.post("/investment")
def simulate_investment(
    req: InvestmentRequest, rules: RuleBookDep, params: ParamBookDep,
    find_scenarios: ScenarioFinderDep,
) -> InvestmentResponse:
    extra: list[Figure] = []
    notes: list[str] = []
    try:
        inp = req.to_input()
        if req.exit.appreciation_rate is None:
            inp, extra, notes = _with_scenarios(inp, find_scenarios, req.property.new_build)

        def run(pending: bool) -> InvestmentSimulation:
            return simulate(inp, rules, params, pending, ALLOW_UNVERIFIED)

        sim = run(False)
        scenario = compare_with_pending(PENDING_SCENARIO, lambda p: run(p).figures())
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    comparison = sim.comparison
    return InvestmentResponse(
        figures={f.key: figure_out(f) for f in (*sim.figures(), *extra)},
        series=[series_out(x) for x in sim.series],
        breakdown=[figure_out(f) for f in sim.cashflow.breakdown],
        within_budget=sim.within_budget,
        binding_constraint=sim.affordability.binding_constraint,
        term_feasible=sim.term.feasible,
        no_irr_reason=sim.irr.no_irr_reason,
        comparison=ComparisonOut(
            labels=[o.label for o in comparison.options],
            cheapest_expected=comparison.cheapest_expected,
            lowest_stressed_payment=comparison.lowest_stressed_payment,
        )
        if comparison is not None
        else None,
        pending_scenario=ScenarioOut(
            name=scenario.name,
            changes=[
                ScenarioChangeOut(key=c.key, base=figure_out(c.base),
                                  scenario=figure_out(c.scenario), delta=figure_out(c.delta))
                for c in scenario.changed
            ],
            new_rules=[SourceOut(**r.to_dict()) for r in scenario.new_rules],
        ),
        warnings=list(sim.warnings),
        appreciation_notes=notes,
    )
