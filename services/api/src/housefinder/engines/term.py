"""Plazo recomendado: el más corto que mantiene el cash flow en el escenario de estrés (F1.8).

Un plazo más corto paga menos intereses en total, pero sube la cuota. Se busca el
menor plazo, en años enteros, cuyo cash flow mensual tras impuestos con el tipo de
estrés (tipo + choque, aplicado a todo el plazo) no baja de un mínimo.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources
from housefinder.engines.cashflow import (
    InvestmentInputs,
    RentalAssumptions,
    TaxParams,
    compute_cashflow,
)
from housefinder.engines.mortgage import STRESS_SCENARIO, first_year_interest, monthly_payment


@dataclass(frozen=True)
class TermRecommendation:
    feasible: bool  # False: ni el plazo máximo alcanza el cash flow mínimo
    years: Figure  # plazo recomendado; si no es viable, el plazo máximo evaluado
    stressed_monthly_payment: Figure
    stressed_monthly_cashflow: Figure


def recommended_term(
    investment: InvestmentInputs,
    rent: RentalAssumptions,
    tax: TaxParams,
    annual_rate: Decimal,
    rate_shock: Decimal,
    max_years: int,
    min_monthly_cashflow: Decimal = Decimal(0),
    rate_sources: tuple[SourceRef, ...] = (),
    max_years_sources: tuple[SourceRef, ...] = (),
) -> TermRecommendation:
    """Menor plazo con cash flow mensual tras impuestos en estrés ≥ `min_monthly_cashflow`.

    `investment.loan` es el préstamo; su cuota y sus intereses del primer año se
    recalculan para cada plazo con el tipo de estrés. `max_years` llega de la capacidad
    de compra (plazo máximo por edad y criterios bancarios).

    Recorre todos los plazos de 1 a `max_years` en lugar de suponer que el cash flow
    crece con el plazo: son como mucho unas decenas de cálculos.
    """
    if max_years <= 0:
        raise ValueError("El plazo máximo debe ser positivo")
    stressed_rate = annual_rate + rate_shock
    sources = combine_sources(
        investment.sources,
        rent.sources,
        tax.sources,
        rate_sources,
        max_years_sources,
        (STRESS_SCENARIO,),
    )

    years = 1
    payment = cashflow = Decimal(0)
    for years in range(1, max_years + 1):
        payment = monthly_payment(investment.loan, stressed_rate, years)
        inputs = replace(
            investment,
            monthly_mortgage_payment=payment,
            first_year_interest=first_year_interest(investment.loan, stressed_rate, years),
        )
        cashflow = compute_cashflow(inputs, rent, tax).monthly_cashflow_after_tax.value
        if cashflow >= min_monthly_cashflow:
            return _result(True, years, payment, cashflow, stressed_rate, sources)
    return _result(False, years, payment, cashflow, stressed_rate, sources)


def _result(
    feasible: bool,
    years: int,
    payment: Decimal,
    cashflow: Decimal,
    stressed_rate: Decimal,
    sources: tuple[SourceRef, ...],
) -> TermRecommendation:
    years_formula = (
        "menor plazo con cash flow tras impuestos en estrés ≥ mínimo"
        if feasible
        else "plazo máximo evaluado: ningún plazo alcanza el cash flow mínimo en estrés"
    )
    return TermRecommendation(
        feasible=feasible,
        years=Figure("term.recommended_years", Decimal(years), "años", years_formula, sources),
        stressed_monthly_payment=Figure(
            "term.stressed_monthly_payment",
            payment,
            "EUR/mes",
            f"cuota francesa a {years} años con tipo de estrés {stressed_rate}",
            sources,
        ),
        stressed_monthly_cashflow=Figure(
            "term.stressed_monthly_cashflow",
            cashflow,
            "EUR/mes",
            f"cash flow mensual tras impuestos a {years} años con tipo de estrés",
            sources,
        ),
    )
