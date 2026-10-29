"""Simulación de una inversión de punta a punta (G3, F1.10).

Un solo camino de cálculo (D4): el endpoint del simulador, el plan completo y el agente
llaman a `simulate`. Compone, en este orden:

1. Capacidad de compra con los criterios bancarios del `ParamBook` y la tasa de gastos de
   compra (impuesto de la normativa + otros gastos como supuesto).
2. Gastos de compra del inmueble: impuesto resuelto por el `RuleBook`; notaría, registro,
   gestoría y tasación como tasa supuesta (PROVISIONAL hasta cargar sus reglas, F2.3).
3. Hipoteca a tipo fijo: cuota y cuota en estrés.
4. Cash flow del primer año con los intereses reales del cuadro y la fiscalidad resuelta:
   cuota incremental si se conoce la base del usuario (ADR-0007), tipo marginal si no.
5. Plazo recomendado en estrés y TIR al horizonte.
6. Si hay ofertas alternativas, comparación con la trayectoria del Euríbor (ADR-0006).

Las incoherencias del plan (precio por encima del máximo, falta de ahorro…) no paran el
cálculo: salen como avisos, porque el usuario puede querer ver el plan igualmente.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money
from housefinder.engines.cashflow import CashflowResult, InvestmentInputs, RentalAssumptions
from housefinder.engines.irr import IrrResult, investment_irr, yearly_cashflows
from housefinder.engines.mortgage import (
    AffordabilityResult,
    BuyerFinances,
    MortgageComparison,
    affordability,
    compare_mortgages,
    first_year_interest,
    monthly_payment,
    stressed_payment,
)
from housefinder.engines.rates import MortgageTerms
from housefinder.engines.term import TermRecommendation, recommended_term
from housefinder.params.bank import bank_criteria
from housefinder.params.book import ParamBook
from housefinder.params.euribor import euribor_12m_path
from housefinder.regulation.kinds import RentalFacts
from housefinder.regulation.resolvers import (
    ibi_annual,
    income_tax_profile,
    purchase_tax,
    purchase_tax_rate,
    tax_params,
)
from housefinder.regulation.rules import RuleBook

# Los criterios bancarios aún no dependen de la ubicación: ámbito nacional.
BANK_TERRITORY = "ES"

BUYER = SourceRef("user_input", "comprador")
PROPERTY = SourceRef("user_input", "inmueble")
FINANCING = SourceRef("user_input", "financiacion")
RENT = SourceRef("user_input", "alquiler")
# Notaría, registro, gestoría y tasación: sin reglas cargadas todavía (inventario, fila 1.4).
OTHER_PURCHASE_COSTS = SourceRef("assumption", "otros-gastos-de-compra", provisional=True)
MARGINAL_RATE = SourceRef("assumption", "tipo-marginal")
APPRECIATION = SourceRef("assumption", "revalorizacion")
# Gastos de venta e impuesto sobre la ganancia: la escala del ahorro y la plusvalía municipal
# no están cargadas (inventario, filas 3.x).
SALE = SourceRef("assumption", "venta", provisional=True)


@dataclass(frozen=True)
class BuyerInput:
    net_monthly_income: Decimal
    existing_monthly_debt: Decimal
    available_savings: Decimal
    age: int
    residence: str  # comunidad autónoma de residencia (ES-13), para el IRPF
    taxable_base: Decimal | None = None  # base liquidable general sin el alquiler
    descendant_ages: tuple[int, ...] = ()  # descendientes con derecho a mínimo, en orden
    marginal_rate: Decimal | None = None  # supuesto, si no se conoce la base

    def __post_init__(self) -> None:
        if (self.taxable_base is None) == (self.marginal_rate is None):
            raise ValueError("Indica la base liquidable o el tipo marginal, uno de los dos")


@dataclass(frozen=True)
class PropertyInput:
    price: Decimal
    territory: str  # municipio con código INE (ES-13-28079)
    construction_value: Decimal  # base de la amortización fiscal
    other_purchase_cost_rate: Decimal  # notaría, registro, gestoría y tasación sobre el precio
    community_fees_monthly: Decimal
    insurance_annual: Decimal  # hogar + impago
    renovation: Decimal = Decimal(0)
    new_build: bool = False
    cadastral_value: Decimal | None = None  # para resolver el IBI con la normativa
    ibi_annual: Decimal | None = None  # si el usuario conoce el recibo

    def __post_init__(self) -> None:
        if (self.cadastral_value is None) == (self.ibi_annual is None):
            raise ValueError("Indica el valor catastral o el IBI anual, uno de los dos")


@dataclass(frozen=True)
class FinancingInput:
    annual_rate: Decimal  # tipo fijo de la hipoteca simulada
    rate_shock: Decimal  # subida de tipos del escenario de estrés
    loan: Decimal | None = None  # None: precio × financiación máxima
    years: int | None = None  # None: plazo máximo por edad y criterios bancarios
    alternatives: tuple[MortgageTerms, ...] = ()  # ofertas a comparar con el Euríbor


@dataclass(frozen=True)
class RentalInput:
    monthly_rent: Decimal
    vacancy_rate: Decimal
    management_fee_rate: Decimal
    maintenance_reserve_rate: Decimal
    situation: RentalFacts  # hechos del contrato para la reducción del IRPF
    contract_date: date  # fecha de celebración: fija la reducción y el ejercicio fiscal


@dataclass(frozen=True)
class ExitInput:
    appreciation_rate: Decimal
    sale_cost_rate: Decimal
    capital_gains_tax_rate: Decimal
    horizon_years: int = 10


@dataclass(frozen=True)
class SimulationInput:
    buyer: BuyerInput
    property: PropertyInput
    financing: FinancingInput
    rental: RentalInput
    exit: ExitInput
    purchase_date: date  # fija los criterios bancarios, el impuesto de compra y el IBI


@dataclass(frozen=True)
class InvestmentSimulation:
    affordability: AffordabilityResult
    within_budget: bool  # precio ≤ precio máximo
    transfer_tax: Figure
    other_purchase_costs: Figure
    purchase_costs: Figure
    loan: Figure
    loan_years: Figure
    monthly_payment: Figure
    stressed_payment: Figure
    ibi_annual: Figure
    cashflow: CashflowResult  # primer año
    term: TermRecommendation
    irr: IrrResult
    comparison: MortgageComparison | None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def figures(self) -> tuple[Figure, ...]:
        """Todas las cifras del plan, cada clave una vez."""
        a, c, t = self.affordability, self.cashflow, self.term
        result = [
            a.max_price, a.max_loan, a.max_payment, a.years,
            self.transfer_tax, self.other_purchase_costs, self.purchase_costs,
            self.loan, self.loan_years, self.monthly_payment, self.stressed_payment,
            self.ibi_annual,
            c.gross_yield, c.annual_operating_cashflow, c.annual_tax,
            c.monthly_cashflow_after_tax, c.cash_invested, c.cash_on_cash,
            t.years, t.stressed_monthly_payment, t.stressed_monthly_cashflow,
            self.irr.sale_price, self.irr.net_sale_proceeds,
        ]
        if self.irr.irr is not None:
            result.append(self.irr.irr)
        if self.comparison is not None:
            for option in self.comparison.options:
                result += [option.first_payment, option.expected_total_interest,
                           option.stressed_max_payment]
        return tuple(result)


def simulate(
    inp: SimulationInput,
    rules: RuleBook,
    params: ParamBook,
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> InvestmentSimulation:
    """Plan de inversión de un inmueble para un comprador.

    `include_pending`: aplica las reglas pendientes de convalidación (escenario, F2.5).
    `allow_unverified`: usa reglas sin verificar; las cifras que dependan de ellas salen
    PROVISIONALES.
    """
    buyer, prop, fin, rental = inp.buyer, inp.property, inp.financing, inp.rental
    on = inp.purchase_date
    criteria = bank_criteria(params, BANK_TERRITORY, on)

    # 1. Capacidad de compra.
    tax_rate = purchase_tax_rate(rules, prop.territory, on, prop.new_build, include_pending,
                                 allow_unverified)
    aff = affordability(
        BuyerFinances(
            net_monthly_income=buyer.net_monthly_income,
            existing_monthly_debt=buyer.existing_monthly_debt,
            available_savings=buyer.available_savings,
            age=buyer.age,
            sources=(BUYER,),
        ),
        annual_rate=fin.annual_rate,
        purchase_cost_rate=tax_rate.value + prop.other_purchase_cost_rate,
        criteria=criteria,
        rate_sources=(FINANCING,),
        purchase_cost_sources=combine_sources(tax_rate.sources, (OTHER_PURCHASE_COSTS,)),
    )
    max_years = int(aff.years.value)

    # 2. Gastos de compra.
    transfer_tax = purchase_tax(rules, prop.price, prop.territory, on, prop.new_build,
                                (PROPERTY,), include_pending, allow_unverified)
    other_costs = Figure(
        "purchase_costs.other",
        money(prop.price * prop.other_purchase_cost_rate),
        "EUR",
        "precio × tasa de notaría, registro, gestoría y tasación",
        (PROPERTY, OTHER_PURCHASE_COSTS),
    )
    purchase_costs = Figure(
        "purchase_costs.total",
        transfer_tax.value + other_costs.value,
        "EUR",
        "impuesto de compra + otros gastos de compra",
        combine_sources(transfer_tax.sources, other_costs.sources),
    )

    # 3. Hipoteca.
    if fin.loan is None:
        loan = Figure("financing.loan", money(prop.price * criteria.max_ltv), "EUR",
                      "precio × financiación máxima", (PROPERTY, criteria.source))
    else:
        loan = Figure("financing.loan", fin.loan, "EUR", "importe indicado", (FINANCING,))
    if fin.years is None:
        loan_years = Figure("financing.years", Decimal(max_years), "años",
                            "plazo máximo por edad y criterios bancarios", aff.years.sources)
    else:
        loan_years = Figure("financing.years", Decimal(fin.years), "años", "plazo indicado",
                            (FINANCING,))
    years = int(loan_years.value)
    loan_sources = combine_sources(loan.sources, loan_years.sources, (FINANCING,))
    payment = Figure(
        "mortgage.monthly_payment",
        monthly_payment(loan.value, fin.annual_rate, years),
        "EUR/mes",
        f"cuota francesa con tipo {fin.annual_rate} a {years} años",
        loan_sources,
    )
    stressed = stressed_payment(loan.value, fin.annual_rate, years, fin.rate_shock,
                                loan_sources)

    # 4. Cash flow del primer año.
    ibi = _ibi(rules, prop, on, allow_unverified)
    rent = RentalAssumptions(
        monthly_rent=rental.monthly_rent,
        vacancy_rate=rental.vacancy_rate,
        community_fees_monthly=prop.community_fees_monthly,
        ibi_annual=ibi.value,
        insurance_annual=prop.insurance_annual,
        management_fee_rate=rental.management_fee_rate,
        maintenance_reserve_rate=rental.maintenance_reserve_rate,
        sources=combine_sources((RENT, PROPERTY), ibi.sources),
    )
    income = (
        income_tax_profile(rules, buyer.residence, rental.contract_date, buyer.taxable_base,
                           buyer.age, buyer.descendant_ages, (BUYER,), allow_unverified)
        if buyer.taxable_base is not None
        else None
    )
    tax = tax_params(
        rules,
        prop.territory,
        rental.contract_date,
        rental.situation,
        marginal_rate=buyer.marginal_rate,
        marginal_rate_sources=(MARGINAL_RATE,) if buyer.marginal_rate is not None else (),
        include_pending=include_pending,
        allow_unverified=allow_unverified,
        income=income,
    )
    investment = InvestmentInputs(
        price=prop.price,
        purchase_costs=purchase_costs.value,
        renovation=prop.renovation,
        loan=loan.value,
        monthly_mortgage_payment=payment.value,
        first_year_interest=(
            first_year_interest(loan.value, fin.annual_rate, years)
            if loan.value > 0
            else Decimal(0)
        ),
        construction_value=prop.construction_value,
        sources=combine_sources((PROPERTY,), purchase_costs.sources, loan_sources),
    )
    cashflow = yearly_cashflows(investment, rent, tax, fin.annual_rate, years, 1)[0]

    # 5. Plazo recomendado y TIR.
    term = recommended_term(investment, rent, tax, fin.annual_rate, fin.rate_shock, max_years,
                            rate_sources=(FINANCING,), max_years_sources=aff.years.sources)
    exit_ = inp.exit
    irr = investment_irr(
        investment, rent, tax, fin.annual_rate, years,
        appreciation_rate=exit_.appreciation_rate,
        sale_cost_rate=exit_.sale_cost_rate,
        capital_gains_tax_rate=exit_.capital_gains_tax_rate,
        horizon_years=exit_.horizon_years,
        rate_sources=(FINANCING,),
        appreciation_sources=(APPRECIATION,),
        sale_sources=(SALE,),
    )

    # 6. Comparación de ofertas.
    comparison = None
    if fin.alternatives:
        path = euribor_12m_path(params, on).rate_path(on)
        comparison = compare_mortgages(loan.value, years, fin.alternatives, path,
                                       fin.rate_shock, loan.sources)

    within_budget = prop.price <= aff.max_price.value
    sim = InvestmentSimulation(
        affordability=aff,
        within_budget=within_budget,
        transfer_tax=transfer_tax,
        other_purchase_costs=other_costs,
        purchase_costs=purchase_costs,
        loan=loan,
        loan_years=loan_years,
        monthly_payment=payment,
        stressed_payment=stressed,
        ibi_annual=ibi,
        cashflow=cashflow,
        term=term,
        irr=irr,
        comparison=comparison,
    )
    return replace(sim, warnings=_warnings(sim, inp, criteria.max_ltv, max_years))


def _ibi(rules: RuleBook, prop: PropertyInput, on: date, allow_unverified: bool) -> Figure:
    if prop.ibi_annual is not None:
        return Figure("holding_costs.ibi_annual", money(prop.ibi_annual), "EUR/año",
                      "recibo del IBI indicado", (PROPERTY,))
    if prop.cadastral_value is None:  # PropertyInput lo impide; se deja explícito
        raise ValueError("Falta el valor catastral o el IBI anual")
    return ibi_annual(rules, prop.cadastral_value, prop.territory, on, (PROPERTY,),
                      allow_unverified)


def _warnings(
    sim: InvestmentSimulation, inp: SimulationInput, max_ltv: Decimal, max_years: int
) -> tuple[str, ...]:
    prop, fin = inp.property, inp.financing
    result: list[str] = []
    if not sim.within_budget:
        result.append(
            f"El precio ({prop.price} €) supera el precio máximo por "
            f"{sim.affordability.binding_constraint} ({sim.affordability.max_price.value} €)."
        )
    if sim.loan.value > money(prop.price * max_ltv):
        result.append(
            f"El préstamo ({sim.loan.value} €) supera la financiación máxima de los criterios "
            f"bancarios ({max_ltv} del precio)."
        )
    if int(sim.loan_years.value) > max_years:
        result.append(
            f"El plazo ({sim.loan_years.value} años) supera el máximo por edad y criterios "
            f"bancarios ({max_years} años)."
        )
    if sim.cashflow.cash_invested.value > inp.buyer.available_savings:
        result.append(
            f"El dinero aportado ({sim.cashflow.cash_invested.value} €) supera el ahorro "
            f"disponible ({inp.buyer.available_savings} €)."
        )
    if not sim.term.feasible:
        result.append(
            f"Ningún plazo hasta {max_years} años mantiene el cash flow positivo con el tipo "
            f"de estrés (+{fin.rate_shock})."
        )
    if sim.irr.irr is None:
        result.append(f"Sin TIR: {sim.irr.no_irr_reason}.")
    provisional = combine_sources(
        *([ref for ref in f.sources if ref.provisional] for f in sim.figures())
    )
    if provisional:
        ids = ", ".join(ref.id for ref in provisional)
        result.append(f"Hay cifras PROVISIONALES porque dependen de: {ids}.")
    return tuple(result)
