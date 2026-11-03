"""Motor de hipoteca: cuota, cuadro de amortización, capacidad de compra, estrés y
comparación de hipotecas fija, variable y mixta.

Determinista y sin dependencias externas. Los criterios bancarios (LTV, ratio de
endeudamiento, edad máxima) no viven en el código: llegan como `BankCriteria` resueltos
desde data/params por `housefinder.params.bank` (ADR-0005), con su `SourceRef`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money
from housefinder.engines.rates import MortgageTerms, RatePath, RateSegment, rate_segments

TWELVE = Decimal(12)


def monthly_payment(principal: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    """Cuota mensual por el sistema francés.

    annual_rate en tanto por uno (0.03 = 3 %).
    """
    if years <= 0:
        raise ValueError("El plazo debe ser positivo")
    return payment_for_months(principal, annual_rate, years * 12)


def payment_for_months(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    """Cuota francesa para un plazo en meses (lo que queda tras una revisión de tipo)."""
    if principal <= 0:
        return Decimal(0)
    if months <= 0:
        raise ValueError("El plazo debe ser positivo")
    r = annual_rate / TWELVE
    if r == 0:
        return money(principal / months)
    factor = (1 + r) ** months
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
    """Cuadro de amortización mensual a tipo fijo. La última cuota absorbe el redondeo."""
    if years <= 0:
        raise ValueError("El plazo debe ser positivo")
    return amortization_schedule_segments(principal, years * 12, (RateSegment(0, annual_rate),))


def amortization_schedule_segments(
    principal: Decimal, months: int, segments: tuple[RateSegment, ...]
) -> list[AmortizationRow]:
    """Cuadro mensual con tipo por tramos (variable o mixta).

    Al empezar cada tramo se recalcula la cuota francesa con el capital pendiente y los
    meses que quedan. La última cuota absorbe el redondeo.
    """
    if not segments or segments[0].start_month != 0:
        raise ValueError("El primer tramo de tipo debe empezar en el mes 0")
    rate_from = {s.start_month: s.annual_rate for s in segments}
    balance = principal
    payment = Decimal(0)
    r = Decimal(0)
    rows: list[AmortizationRow] = []
    n = months
    for month in range(1, n + 1):
        if month - 1 in rate_from:
            r = rate_from[month - 1] / TWELVE
            payment = payment_for_months(balance, rate_from[month - 1], n - month + 1)
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


@dataclass(frozen=True)
class AmortizationYear:
    year: int
    interest: Decimal
    principal: Decimal
    balance: Decimal  # capital pendiente al acabar el año


def yearly_amortization(rows: list[AmortizationRow]) -> list[AmortizationYear]:
    """El cuadro mensual resumido por años: intereses y capital pagados y lo que queda."""
    years = []
    for start in range(0, len(rows), 12):
        chunk = rows[start:start + 12]
        years.append(AmortizationYear(
            year=start // 12 + 1,
            interest=money(sum((r.interest for r in chunk), Decimal(0))),
            principal=money(sum((r.principal for r in chunk), Decimal(0))),
            balance=chunk[-1].balance,
        ))
    return years


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


@dataclass(frozen=True)
class MortgageCost:
    label: str
    first_payment: Figure
    expected_total_interest: Figure  # coste total esperado con la trayectoria del índice
    stressed_max_payment: Figure  # peor cuota con la trayectoria + choque de tipos


@dataclass(frozen=True)
class MortgageComparison:
    options: tuple[MortgageCost, ...]  # en el orden recibido
    cheapest_expected: str  # etiqueta con menos intereses esperados
    lowest_stressed_payment: str  # etiqueta con la peor cuota más baja en estrés


def compare_mortgages(
    principal: Decimal,
    years: int,
    options: tuple[MortgageTerms, ...],
    expected_path: RatePath,
    rate_shock: Decimal,
    principal_sources: tuple[SourceRef, ...] = (),
) -> MortgageComparison:
    """Compara ofertas fija, variable y mixta: coste esperado y peor cuota en estrés (F1.6).

    El estrés suma `rate_shock` al índice en todas las revisiones; el tramo inicial de
    cada oferta no cambia. A igualdad gana la primera opción recibida.
    """
    if not options:
        raise ValueError("No hay ofertas que comparar")
    labels = [terms.label for terms in options]
    if len(set(labels)) != len(labels):
        raise ValueError(f"Etiquetas repetidas en la comparación: {labels}")
    months = years * 12
    stressed_path = expected_path.shifted(rate_shock, STRESS_SCENARIO)
    costs = tuple(
        _mortgage_cost(principal, months, terms, expected_path, stressed_path, principal_sources)
        for terms in options
    )
    cheapest = min(costs, key=lambda c: c.expected_total_interest.value)
    safest = min(costs, key=lambda c: c.stressed_max_payment.value)
    return MortgageComparison(costs, cheapest.label, safest.label)


def _mortgage_cost(
    principal: Decimal,
    months: int,
    terms: MortgageTerms,
    expected_path: RatePath,
    stressed_path: RatePath,
    principal_sources: tuple[SourceRef, ...],
) -> MortgageCost:
    expected = amortization_schedule_segments(
        principal, months, rate_segments(terms, expected_path, months)
    )
    stressed_segments = rate_segments(terms, stressed_path, months)
    stressed = amortization_schedule_segments(principal, months, stressed_segments)
    # Cuota pactada al empezar cada tramo; la última fila no cuenta como «peor cuota»
    # por absorber el céntimo de redondeo.
    starts = {segment.start_month for segment in stressed_segments}
    stressed_installments = [row.payment for row in stressed if row.month - 1 in starts]
    base_sources = combine_sources(principal_sources, terms.sources)
    if terms.is_indexed_within(months):
        expected_sources = combine_sources(base_sources, expected_path.sources)
        stressed_sources = combine_sources(base_sources, stressed_path.sources)
    else:
        expected_sources = base_sources
        stressed_sources = combine_sources(base_sources, (STRESS_SCENARIO,))
    key = f"mortgage_comparison.{terms.label}"
    return MortgageCost(
        label=terms.label,
        first_payment=Figure(
            f"{key}.first_payment",
            expected[0].payment,
            "EUR/mes",
            "cuota francesa del primer mes con el tipo inicial",
            base_sources,
        ),
        expected_total_interest=Figure(
            f"{key}.expected_total_interest",
            money(sum((row.interest for row in expected), Decimal(0))),
            "EUR",
            "suma de intereses del cuadro con la trayectoria esperada del índice",
            expected_sources,
        ),
        stressed_max_payment=Figure(
            f"{key}.stressed_max_payment",
            max(stressed_installments),
            "EUR/mes",
            "cuota pactada más alta de los tramos con la trayectoria del índice + choque de estrés",
            stressed_sources,
        ),
    )
