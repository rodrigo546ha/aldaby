"""Motor de cash flow y rentabilidad personal de una inversión en alquiler.

La fiscalidad concreta (reducción por alquiler, % de amortización, tipo marginal)
llega como parámetros resueltos por el motor de normativa: aquí no hay ningún
porcentaje legal escrito en el código.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from housefinder.core.figures import Figure, money

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


@dataclass(frozen=True)
class TaxParams:
    """Parámetros fiscales resueltos por el motor de normativa, con su regla de origen."""

    marginal_rate: Decimal  # tipo marginal del usuario (tanto por uno)
    rental_income_reduction: Decimal  # reducción sobre el rendimiento neto positivo
    depreciation_rate: Decimal  # amortización anual sobre el valor de construcción
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class InvestmentInputs:
    price: Decimal
    purchase_costs: Decimal  # impuestos, notaría, registro, gestoría, tasación
    renovation: Decimal
    loan: Decimal
    monthly_mortgage_payment: Decimal
    first_year_interest: Decimal
    construction_value: Decimal  # base de la amortización fiscal


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
        money((operating_cashflow - annual_tax) / cash_invested * 100)
        if cash_invested > 0
        else Decimal(0)
    )
    gross = money(annual_rent / inv.price * 100) if inv.price > 0 else Decimal(0)

    tax_sources = tax.rule_ids
    return CashflowResult(
        gross_yield=Figure(gross, "%", "renta anual / precio × 100"),
        annual_operating_cashflow=Figure(
            operating_cashflow,
            "EUR/año",
            "renta cobrada − gastos de explotación − cuotas hipotecarias",
        ),
        annual_tax=Figure(
            annual_tax,
            "EUR/año",
            "máx(0, rendimiento neto × (1 − reducción)) × tipo marginal",
            tax_sources,
        ),
        monthly_cashflow_after_tax=Figure(
            after_tax_monthly, "EUR/mes", "(cash flow operativo − impuesto) / 12", tax_sources
        ),
        cash_invested=Figure(
            cash_invested, "EUR", "precio + gastos de compra + reforma − préstamo"
        ),
        cash_on_cash=Figure(
            coc, "%", "cash flow anual tras impuestos / dinero aportado × 100", tax_sources
        ),
    )
