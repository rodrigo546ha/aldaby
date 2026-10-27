"""Motor de cash flow y rentabilidad personal de una inversión en alquiler.

La fiscalidad concreta (reducción por alquiler, % de amortización, tipo marginal)
llega como parámetros resueltos por el motor de normativa: aquí no hay ningún
porcentaje legal escrito en el código.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money, ratio

TWELVE = Decimal(12)


@dataclass(frozen=True)
class RentalAssumptions:
    monthly_rent: Decimal
    vacancy_rate: Decimal  # tanto por uno del año sin ingresos (p. ej. 0.05)
    community_fees_monthly: Decimal
    ibi_annual: Decimal
    insurance_annual: Decimal  # hogar + impago
    management_fee_rate: Decimal  # % de la renta cobrada (0 si gestión activa)
    maintenance_reserve_rate: Decimal  # % de la renta reservado a mantenimiento
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaxParams:
    """Parámetros fiscales resueltos por el motor de normativa, con su regla de origen."""

    marginal_rate: Decimal  # tipo marginal del usuario (tanto por uno)
    rental_income_reduction: Decimal  # reducción sobre el rendimiento neto positivo
    depreciation_rate: Decimal  # amortización anual sobre el valor de construcción
    sources: tuple[SourceRef, ...]

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(ref.id for ref in self.sources if ref.kind == "rule")


@dataclass(frozen=True)
class InvestmentInputs:
    price: Decimal
    purchase_costs: Decimal  # impuestos, notaría, registro, gestoría, tasación
    renovation: Decimal
    loan: Decimal
    monthly_mortgage_payment: Decimal
    first_year_interest: Decimal
    construction_value: Decimal  # base de la amortización fiscal
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CashflowResult:
    gross_yield: Figure
    annual_operating_cashflow: Figure
    annual_tax: Figure
    monthly_cashflow_after_tax: Figure
    cash_invested: Figure
    cash_on_cash: Figure


def compute_cashflow(
    inv: InvestmentInputs, rent: RentalAssumptions, tax: TaxParams
) -> CashflowResult:
    annual_rent = rent.monthly_rent * TWELVE
    collected = annual_rent * (1 - rent.vacancy_rate)

    community = rent.community_fees_monthly * TWELVE
    management = collected * rent.management_fee_rate
    maintenance = collected * rent.maintenance_reserve_rate
    operating_costs = community + rent.ibi_annual + rent.insurance_annual + management + maintenance

    mortgage_annual = inv.monthly_mortgage_payment * TWELVE
    operating_cashflow = money(collected - operating_costs - mortgage_annual)

    # Rendimiento fiscal: ingresos − gastos deducibles (intereses, no el capital).
    depreciation = inv.construction_value * tax.depreciation_rate
    taxable = collected - operating_costs - inv.first_year_interest - depreciation
    if taxable > 0:
        taxable = taxable * (1 - tax.rental_income_reduction)
    annual_tax = money(max(taxable, Decimal(0)) * tax.marginal_rate)

    after_tax_monthly = money((operating_cashflow - annual_tax) / TWELVE)
    cash_invested = money(inv.price + inv.purchase_costs + inv.renovation - inv.loan)
    coc = (
        ratio((operating_cashflow - annual_tax) / cash_invested)
        if cash_invested > 0
        else Decimal(0)
    )
    gross = ratio(annual_rent / inv.price) if inv.price > 0 else Decimal(0)

    operating_sources = combine_sources(inv.sources, rent.sources)
    all_sources = combine_sources(inv.sources, rent.sources, tax.sources)
    return CashflowResult(
        gross_yield=Figure(
            "cashflow.gross_yield", gross, "ratio", "renta anual / precio", operating_sources
        ),
        annual_operating_cashflow=Figure(
            "cashflow.annual_operating",
            operating_cashflow,
            "EUR/año",
            "renta cobrada − gastos de explotación − cuotas hipotecarias",
            operating_sources,
        ),
        annual_tax=Figure(
            "cashflow.annual_tax",
            annual_tax,
            "EUR/año",
            "máx(0, rendimiento neto × (1 − reducción)) × tipo marginal",
            all_sources,
        ),
        monthly_cashflow_after_tax=Figure(
            "cashflow.monthly_after_tax",
            after_tax_monthly,
            "EUR/mes",
            "(cash flow operativo − impuesto) / 12",
            all_sources,
        ),
        cash_invested=Figure(
            "cashflow.cash_invested",
            cash_invested,
            "EUR",
            "precio + gastos de compra + reforma − préstamo",
            inv.sources,
        ),
        cash_on_cash=Figure(
            "cashflow.cash_on_cash",
            coc,
            "ratio",
            "cash flow anual tras impuestos / dinero aportado",
            all_sources,
        ),
    )
