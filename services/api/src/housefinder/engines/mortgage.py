"""Motor de hipoteca: cuota, cuadro de amortización, capacidad de compra y estrés.

Determinista y sin dependencias externas. Los criterios bancarios (LTV, ratio de
endeudamiento, edad máxima) no viven en el código: llegan como `BankCriteria` resueltos
desde data/params por `housefinder.params.bank` (ADR-0005), con su `SourceRef`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money

TWELVE = Decimal(12)


def monthly_payment(principal: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    """Cuota mensual por el sistema francés.

    annual_rate en tanto por uno (0.03 = 3 %).
    """
    if principal <= 0:
        return Decimal(0)
    if years <= 0:
        raise ValueError("El plazo debe ser positivo")
    n = years * 12
    r = annual_rate / TWELVE
    if r == 0:
        return money(principal / n)
    factor = (1 + r) ** n
    return money(principal * r * factor / (factor - 1))


def principal_for_payment(payment: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    """Capital máximo que se amortiza con una cuota dada (inversa de monthly_payment)."""
    if payment <= 0:
        return Decimal(0)
    n = years * 12
    r = annual_rate / TWELVE
    if r == 0:
        return money(payment * n)
    factor = (1 + r) ** n
    return money(payment * (factor - 1) / (r * factor))


@dataclass(frozen=True)
class AmortizationRow:
    month: int
    payment: Decimal
    interest: Decimal
    principal: Decimal
    balance: Decimal


def amortization_schedule(
    principal: Decimal, annual_rate: Decimal, years: int
) -> list[AmortizationRow]:
    """Cuadro de amortización mensual. La última cuota absorbe el redondeo."""
    payment = monthly_payment(principal, annual_rate, years)
    r = annual_rate / TWELVE
    balance = principal
    rows: list[AmortizationRow] = []
    n = years * 12
    for month in range(1, n + 1):
        interest = money(balance * r)
        amort = payment - interest
        if month == n:
            amort = balance
            payment_m = amort + interest
        else:
            payment_m = payment
        balance = money(balance - amort)
        rows.append(AmortizationRow(month, payment_m, interest, amort, balance))
    return rows


def first_year_interest(principal: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    """Intereses pagados en los 12 primeros meses (gasto deducible del alquiler)."""
    rows = amortization_schedule(principal, annual_rate, years)[:12]
    return money(sum((row.interest for row in rows), Decimal(0)))


@dataclass(frozen=True)
class BankCriteria:
    """Criterios de concesión, resueltos desde data/params (sin valores por defecto)."""

    max_ltv: Decimal  # financiación máxima sobre el precio (inversión)
    max_dti: Decimal  # cuota total / ingresos netos mensuales
    max_age_at_end: int
    max_years: int
    source: SourceRef


@dataclass(frozen=True)
class BuyerFinances:
    net_monthly_income: Decimal
    existing_monthly_debt: Decimal  # cuotas de otros préstamos
    available_savings: Decimal  # ahorro que el usuario está dispuesto a invertir
    age: int
    sources: tuple[SourceRef, ...] = (SourceRef("user_input", "finanzas-del-comprador"),)


@dataclass(frozen=True)
class AffordabilityResult:
    max_price: Figure
    max_loan: Figure
    max_payment: Figure
    years: Figure
    binding_constraint: str  # "ahorro" o "ingresos"


def max_term_years(age: int, criteria: BankCriteria) -> int:
    return max(0, min(criteria.max_years, criteria.max_age_at_end - age))


def affordability(
    finances: BuyerFinances,
    annual_rate: Decimal,
    purchase_cost_rate: Decimal,
    criteria: BankCriteria,
    rate_sources: tuple[SourceRef, ...] = (),
    purchase_cost_sources: tuple[SourceRef, ...] = (),
) -> AffordabilityResult:
    """Precio máximo de compra según ahorro e ingresos.

    purchase_cost_rate: gastos e impuestos de compra sobre el precio (tanto por uno),
    resueltos por el motor de normativa/fiscalidad según la comunidad autónoma.

    Restricciones:
      - Ahorro: entrada (1 - LTV) + gastos de compra <= ahorro disponible.
      - Ingresos: cuota <= ingresos * DTI - otras deudas, y préstamo = precio * LTV.
    """
    c = criteria
    years = max_term_years(finances.age, c)
    if years <= 0:
        raise ValueError("Por edad, no hay plazo hipotecario posible con estos criterios")

    max_payment = money(finances.net_monthly_income * c.max_dti - finances.existing_monthly_debt)
    max_payment = max(max_payment, Decimal(0))
    max_loan_by_income = principal_for_payment(max_payment, annual_rate, years)

    price_by_savings = money(finances.available_savings / (1 - c.max_ltv + purchase_cost_rate))
    price_by_income = money(max_loan_by_income / c.max_ltv)

    if price_by_savings <= price_by_income:
        max_price, binding = price_by_savings, "ahorro"
    else:
        max_price, binding = price_by_income, "ingresos"

    payment_sources = combine_sources(finances.sources, (c.source,))
    price_sources = combine_sources(payment_sources, rate_sources, purchase_cost_sources)
    return AffordabilityResult(
        max_price=Figure(
            "affordability.max_price",
            max_price,
            "EUR",
            "mín(ahorro / (1 − LTV + gastos de compra), préstamo máximo por ingresos / LTV)",
            price_sources,
        ),
        max_loan=Figure(
            "affordability.max_loan",
            money(max_price * c.max_ltv),
            "EUR",
            "precio máximo × LTV",
            price_sources,
        ),
        max_payment=Figure(
            "affordability.max_payment",
            max_payment,
            "EUR/mes",
            "ingresos netos × ratio de endeudamiento − otras deudas",
            payment_sources,
        ),
        years=Figure(
            "affordability.years",
            Decimal(years),
            "años",
            "mín(plazo máximo, edad máxima al final − edad)",
            payment_sources,
        ),
        binding_constraint=binding,
    )


STRESS_SCENARIO = SourceRef("assumption", "escenario-estres")


def stressed_payment(
    principal: Decimal,
    annual_rate: Decimal,
    years: int,
    rate_shock: Decimal,
    sources: tuple[SourceRef, ...] = (),
) -> Figure:
    """Cuota si el tipo sube `rate_shock` (p. ej. 0.02 = +2 puntos).

    `sources`: procedencia del capital y del tipo, para que la cifra la herede.
    """
    value = monthly_payment(principal, annual_rate + rate_shock, years)
    return Figure(
        "mortgage.stressed_payment",
        value,
        "EUR/mes",
        f"cuota francesa con tipo {annual_rate} + {rate_shock}",
        combine_sources(sources, (STRESS_SCENARIO,)),
    )
