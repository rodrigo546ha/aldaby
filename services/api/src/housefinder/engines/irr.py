"""TIR de la inversión a un horizonte (10 años por defecto) con la revalorización como
parámetro (F1.9).

Flujos anuales: año 0, el dinero aportado (con signo negativo); años 1..H, el cash flow
tras impuestos de cada año, con los intereses reales de ese año en el cuadro; año H,
además, la venta neta.

Supuestos explícitos:
- Renta y gastos constantes en euros corrientes; solo se revaloriza el precio.
- La venta resta gastos de venta, el capital pendiente del préstamo y el impuesto sobre la
  ganancia (Ley del IRPF, art. 35) = venta − gastos y tributos de la venta − (precio +
  gastos de compra + reforma − amortizaciones fiscales acumuladas).
- El impuesto es la cuota incremental de la base del ahorro (como el ADR-0007 para el
  alquiler) o, si no se conoce, la ganancia por un tipo dado como supuesto.
- Los gastos de venta que dependen del precio de venta y de la normativa (plusvalía
  municipal, escritura) llegan ya calculados en `extra_sale_costs`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money, ratio
from housefinder.engines.cashflow import (
    CashflowResult,
    InvestmentInputs,
    PendingExcess,
    RentalAssumptions,
    TaxParams,
    compute_cashflow,
)
from housefinder.engines.irpf import IncomeTaxProfile, incremental_tax
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
    capital_gains_tax: Figure


def projected_sale_price(price: Decimal, appreciation_rate: Decimal, years: int) -> Decimal:
    """Precio de venta con revalorización anual compuesta."""
    return money(price * (1 + appreciation_rate) ** years)


def investment_irr(
    investment: InvestmentInputs,
    rent: RentalAssumptions,
    tax: TaxParams,
    annual_rate: Decimal,
    loan_years: int,
    appreciation_rate: Decimal,
    sale_cost_rate: Decimal,
    capital_gains_tax_rate: Decimal | None = None,
    horizon_years: int = 10,
    rate_sources: tuple[SourceRef, ...] = (),
    appreciation_sources: tuple[SourceRef, ...] = (),
    sale_sources: tuple[SourceRef, ...] = (),
    gains_tax_profile: IncomeTaxProfile | None = None,
    extra_sale_costs: tuple[Figure, ...] = (),
) -> IrrResult:
    """TIR a `horizon_years` años.

    `investment.loan` se amortiza a `annual_rate` y `loan_years`; la cuota y los intereses
    de `investment` se ignoran y se toman del cuadro año a año.
    `appreciation_rate`: revalorización anual del precio (escenario de F5).
    `sale_cost_rate`: gastos de venta sobre el precio (agencia…), con `sale_sources`.
    Impuesto: `gains_tax_profile` (base del ahorro sin la venta y escalas) o
    `capital_gains_tax_rate` (supuesto), uno de los dos.
    `extra_sale_costs`: gastos y tributos de la venta ya calculados; restan de la ganancia.
    """
    if horizon_years <= 0:
        raise ValueError("El horizonte debe ser positivo")
    if (capital_gains_tax_rate is None) == (gains_tax_profile is None):
        raise ValueError("Indica el tipo de la ganancia o el perfil del ahorro, uno de los dos")

    rows = _schedule(investment, annual_rate, loan_years)
    acquisition = investment.price + investment.purchase_costs + investment.renovation
    flows = [-money(acquisition - investment.loan)]  # dinero aportado
    for year_result in yearly_cashflows(investment, rent, tax, annual_rate, loan_years,
                                        horizon_years):
        flows.append(
            year_result.annual_operating_cashflow.value - year_result.annual_tax.value
        )

    sale_price = projected_sale_price(investment.price, appreciation_rate, horizon_years)
    sale_costs = money(sale_price * sale_cost_rate) + sum(
        (f.value for f in extra_sale_costs), Decimal(0)
    )
    depreciated = investment.construction_value * tax.depreciation_rate * horizon_years
    gain = sale_price - sale_costs - (acquisition - depreciated)
    deduction = tax.territorial_deduction
    deducted = (f"; menos el {deduction} de la parte de la cuota de la ganancia (deducción "
                "por rentas obtenidas en Ceuta o Melilla)") if deduction else ""
    deduction_sources = tax.sources if deduction else ()
    if gains_tax_profile is not None:
        gains_tax = max(incremental_tax(gain, gains_tax_profile, deduction), Decimal(0))
        gains_formula = (
            "cuota del ahorro con la ganancia − sin ella; ganancia = venta − gastos y "
            "tributos de la venta − (precio + gastos de compra + reforma − amortizaciones)"
            + deducted
        )
        gains_sources = combine_sources(gains_tax_profile.sources, deduction_sources)
    elif capital_gains_tax_rate is not None:
        gains_tax = money(max(gain, Decimal(0)) * capital_gains_tax_rate * (1 - deduction))
        gains_formula = (
            "máx(0, ganancia) × tipo; ganancia = venta − gastos y tributos de la venta − "
            "(precio + gastos de compra + reforma − amortizaciones)" + deducted
        )
        gains_sources = deduction_sources
    else:  # comprobado arriba; se deja explícito
        raise ValueError("Falta el tipo de la ganancia o el perfil del ahorro")
    months = horizon_years * 12
    pending_loan = rows[months - 1].balance if months <= len(rows) else Decimal(0)
    net_sale = money(sale_price - sale_costs - pending_loan - gains_tax)
    flows[-1] += net_sale

    extra_sources = combine_sources(*(f.sources for f in extra_sale_costs))
    sources = combine_sources(
        investment.sources,
        rent.sources,
        tax.sources,
        rate_sources,
        appreciation_sources,
        sale_sources,
        gains_sources,
        extra_sources,
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
            "venta − gastos y tributos de la venta − préstamo pendiente − impuesto sobre "
            "la ganancia",
            sources,
        ),
        capital_gains_tax=Figure(
            "irr.capital_gains_tax",
            gains_tax,
            "EUR",
            gains_formula,
            combine_sources(investment.sources, appreciation_sources, sale_sources,
                            gains_sources, extra_sources, tax.sources),
        ),
    )


def yearly_cashflows(
    investment: InvestmentInputs,
    rent: RentalAssumptions,
    tax: TaxParams,
    annual_rate: Decimal,
    loan_years: int,
    years: int,
) -> tuple[CashflowResult, ...]:
    """Cash flow de cada año con las cuotas e intereses reales del cuadro.

    El exceso de intereses y reparación de un año pasa a los siguientes (LIRPF
    art. 23.1.a.1.º), así que cada año depende del anterior.
    """
    rows = _schedule(investment, annual_rate, loan_years)
    results: list[CashflowResult] = []
    pending: tuple[PendingExcess, ...] = ()
    for year in range(1, years + 1):
        year_rows = rows[12 * (year - 1) : 12 * year]
        payments = sum((r.payment for r in year_rows), Decimal(0))
        interest = sum((r.interest for r in year_rows), Decimal(0))
        inputs = replace(
            investment,
            monthly_mortgage_payment=payments / 12,
            first_year_interest=interest,  # en compute_cashflow, los intereses del año
        )
        result = compute_cashflow(inputs, rent, tax, pending_excess=pending)
        pending = result.pending_excess
        results.append(result)
    return tuple(results)


def _schedule(
    investment: InvestmentInputs, annual_rate: Decimal, loan_years: int
) -> list[AmortizationRow]:
    if investment.loan <= 0:
        return []
    return amortization_schedule(investment.loan, annual_rate, loan_years)
