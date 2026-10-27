"""TIR de la inversión a un horizonte (10 años por defecto) con la revalorización como
parámetro (F1.9).

Flujos anuales: año 0, el dinero aportado (con signo negativo); años 1..H, el cash flow
tras impuestos de cada año, con los intereses reales de ese año en el cuadro; año H,
además, la venta neta.

Supuestos explícitos:
- Renta y gastos constantes en euros corrientes; solo se revaloriza el precio.
- La venta resta gastos de venta, el capital pendiente del préstamo y un impuesto sobre la
  ganancia = venta − gastos − (precio + gastos de compra + reforma − amortizaciones
  fiscales acumuladas). El tipo llega como parámetro con sus fuentes; la forma exacta de
  la base y de la escala del impuesto es normativa y se revisa en F2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money, ratio
from housefinder.engines.cashflow import (
    InvestmentInputs,
    RentalAssumptions,
    TaxParams,
    compute_cashflow,
)
from housefinder.engines.mortgage import AmortizationRow, amortization_schedule

LOW_RATE = Decimal("-0.99")
TOLERANCE = Decimal("1e-10")
MAX_ITERATIONS = 200


def irr(cashflows: Sequence[Decimal]) -> Decimal | None:
    """TIR por bisección, en tanto por uno y redondeada con `ratio()`. None si no existe."""
    return _solve_irr(cashflows)[0]


def _solve_irr(cashflows: Sequence[Decimal]) -> tuple[Decimal | None, str]:
    if not any(cf > 0 for cf in cashflows) or not any(cf < 0 for cf in cashflows):
        return None, "los flujos no cambian de signo: nunca se recupera lo invertido"

    def npv(rate: Decimal) -> Decimal:
        return sum((cf / (1 + rate) ** t for t, cf in enumerate(cashflows)), Decimal(0))

    low, high = LOW_RATE, Decimal(1)
    npv_low = npv(low)
    while (npv_low > 0) == (npv(high) > 0) and high < 1000:
        high *= 2
    if (npv_low > 0) == (npv(high) > 0):
        return None, "la TIR queda fuera del intervalo calculable (−99 % a +1.000 %)"

    for _ in range(MAX_ITERATIONS):
        mid = (low + high) / 2
        npv_mid = npv(mid)
        if npv_mid == 0 or high - low < TOLERANCE:
            break
        if (npv_mid > 0) == (npv_low > 0):
            low, npv_low = mid, npv_mid
        else:
            high = mid
    return ratio((low + high) / 2), ""


@dataclass(frozen=True)
class IrrResult:
    irr: Figure | None  # None si no hay TIR; el motivo, en no_irr_reason
    no_irr_reason: str
    sale_price: Figure
    net_sale_proceeds: Figure  # venta − gastos − préstamo pendiente − impuesto


def investment_irr(
    investment: InvestmentInputs,
    rent: RentalAssumptions,
    tax: TaxParams,
    annual_rate: Decimal,
    loan_years: int,
    appreciation_rate: Decimal,
    sale_cost_rate: Decimal,
    capital_gains_tax_rate: Decimal,
    horizon_years: int = 10,
    rate_sources: tuple[SourceRef, ...] = (),
    appreciation_sources: tuple[SourceRef, ...] = (),
    sale_sources: tuple[SourceRef, ...] = (),
) -> IrrResult:
    """TIR a `horizon_years` años.

    `investment.loan` se amortiza a `annual_rate` y `loan_years`; la cuota y los intereses
    de `investment` se ignoran y se toman del cuadro año a año.
    `appreciation_rate`: revalorización anual del precio (escenario de F5).
    `sale_cost_rate` y `capital_gains_tax_rate`: tanto por uno; llegan con `sale_sources`.
    """
    if horizon_years <= 0:
        raise ValueError("El horizonte debe ser positivo")

    rows = (
        amortization_schedule(investment.loan, annual_rate, loan_years)
        if investment.loan > 0
        else []
    )
    acquisition = investment.price + investment.purchase_costs + investment.renovation
    flows = [-money(acquisition - investment.loan)]  # dinero aportado
    for year in range(1, horizon_years + 1):
        flows.append(_after_tax_cashflow(investment, rent, tax, rows, year))

    sale_price = money(investment.price * (1 + appreciation_rate) ** horizon_years)
    sale_costs = money(sale_price * sale_cost_rate)
    depreciated = investment.construction_value * tax.depreciation_rate * horizon_years
    gain = sale_price - sale_costs - (acquisition - depreciated)
    gains_tax = money(max(gain, Decimal(0)) * capital_gains_tax_rate)
    months = horizon_years * 12
    pending_loan = rows[months - 1].balance if months <= len(rows) else Decimal(0)
    net_sale = money(sale_price - sale_costs - pending_loan - gains_tax)
    flows[-1] += net_sale

    sources = combine_sources(
        investment.sources,
        rent.sources,
        tax.sources,
        rate_sources,
        appreciation_sources,
        sale_sources,
    )
    sale_sources_all = combine_sources(investment.sources, appreciation_sources)
    value, reason = _solve_irr(flows)
    return IrrResult(
        irr=Figure(
            "irr.rate",
            value,
            "ratio",
            f"TIR anual a {horizon_years} años: aportación, cash flow tras impuestos de cada "
            "año y venta neta al final",
            sources,
        )
        if value is not None
        else None,
        no_irr_reason=reason,
        sale_price=Figure(
            "irr.sale_price",
            sale_price,
            "EUR",
            f"precio × (1 + revalorización)^{horizon_years}",
            sale_sources_all,
        ),
        net_sale_proceeds=Figure(
            "irr.net_sale_proceeds",
            net_sale,
            "EUR",
            "venta − gastos de venta − préstamo pendiente − impuesto sobre la ganancia",
            sources,
        ),
    )


def _after_tax_cashflow(
    investment: InvestmentInputs,
    rent: RentalAssumptions,
    tax: TaxParams,
    rows: list[AmortizationRow],
    year: int,
) -> Decimal:
    """Cash flow tras impuestos del año `year`, con las cuotas e intereses de ese año."""
    year_rows = rows[12 * (year - 1) : 12 * year]
    payments = sum((r.payment for r in year_rows), Decimal(0))
    interest = sum((r.interest for r in year_rows), Decimal(0))
    inputs = replace(
        investment,
        monthly_mortgage_payment=payments / 12,
        first_year_interest=interest,  # en compute_cashflow, los intereses del año evaluado
    )
    result = compute_cashflow(inputs, rent, tax)
    return result.annual_operating_cashflow.value - result.annual_tax.value
