"""Motor de cash flow y rentabilidad personal de una inversión en alquiler.

La fiscalidad concreta (reducción por alquiler, % de amortización, escalas del IRPF)
llega como parámetros resueltos por el motor de normativa: aquí no hay ningún
porcentaje legal escrito en el código.

El impuesto es la cuota incremental del IRPF (ADR-0007) o, si no se conoce la base del
usuario, el rendimiento reducido por un tipo marginal dado como supuesto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money, ratio
from housefinder.engines.irpf import IncomeTaxProfile, incremental_tax

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
    """Parámetros fiscales resueltos por el motor de normativa, con su regla de origen.

    Exactamente uno de `marginal_rate` (supuesto) e `income_tax` (cuota incremental).
    """

    marginal_rate: Decimal | None  # tipo marginal supuesto (tanto por uno)
    rental_income_reduction: Decimal  # reducción sobre el rendimiento neto positivo
    depreciation_rate: Decimal  # amortización anual sobre el valor de construcción
    interest_repair_carryforward_years: int  # arrastre del exceso de intereses y reparación
    sources: tuple[SourceRef, ...]
    income_tax: IncomeTaxProfile | None = None  # IRPF del usuario sin el alquiler
    # Parte de la cuota de las rentas del inmueble que se deduce (art. 68.4, ADR-0045)
    territorial_deduction: Decimal = Decimal(0)
    # Cómo tributa el alquiler (ADR-0046); por defecto, el IRPF común
    rental_base: str = "general"  # «general» o «ahorro»: a qué base va el rendimiento
    gross_bonus: Decimal = Decimal(0)  # bonificación sobre los ingresos (forales vascos)
    deductible_expenses: str = "todos"  # «todos» o solo los «intereses»
    expense_cap: str = "intereses_reparacion"  # o «todos» (Navarra) o «sin_negativo» (vascos)

    def __post_init__(self) -> None:
        if (self.marginal_rate is None) == (self.income_tax is None):
            raise ValueError("Indica el tipo marginal o el perfil del IRPF, uno de los dos")

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(ref.id for ref in self.sources if ref.kind == "rule")


@dataclass(frozen=True)
class PendingExcess:
    """Exceso de intereses y gastos de reparación pendiente de deducir."""

    amount: Decimal
    years_left: int  # ejercicios en los que aún se puede deducir


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
    pending_excess: tuple[PendingExcess, ...] = ()  # para el ejercicio siguiente


def compute_cashflow(
    inv: InvestmentInputs,
    rent: RentalAssumptions,
    tax: TaxParams,
    pending_excess: tuple[PendingExcess, ...] = (),
) -> CashflowResult:
    """Cash flow de un año. `inv.first_year_interest` son los intereses de ese año y
    `pending_excess`, el exceso de intereses y reparación que llega de años anteriores."""
    annual_rent = rent.monthly_rent * TWELVE
    collected = annual_rent * (1 - rent.vacancy_rate)

    community = rent.community_fees_monthly * TWELVE
    management = collected * rent.management_fee_rate
    maintenance = collected * rent.maintenance_reserve_rate  # reparación y conservación
    other_costs = community + rent.ibi_annual + rent.insurance_annual + management
    operating_costs = other_costs + maintenance

    mortgage_annual = inv.monthly_mortgage_payment * TWELVE
    operating_cashflow = money(collected - operating_costs - mortgage_annual)

    # Rendimiento fiscal: ingresos − gastos deducibles (intereses, no el capital), con el tope
    # de cada régimen (ADR-0046)
    net, next_pending, net_formula = _taxable_net(inv, tax, collected, other_costs, maintenance,
                                                  pending_excess)
    reduced = net * (1 - tax.rental_income_reduction) if net > 0 else net
    deduction = tax.territorial_deduction
    deducted = (f", menos el {deduction} de la parte de la cuota de esta renta (deducción por "
                "rentas obtenidas en Ceuta o Melilla)") if deduction else ""
    if tax.income_tax is not None:
        annual_tax = incremental_tax(reduced, tax.income_tax, deduction)
        tax_formula = (f"cuota IRPF con el rendimiento reducido − cuota IRPF sin él{deducted}; "
                       f"{net_formula}")
        tax_sources = combine_sources(tax.sources, tax.income_tax.sources)
    elif tax.marginal_rate is not None:
        annual_tax = money(max(reduced, Decimal(0)) * tax.marginal_rate * (1 - deduction))
        tax_formula = (f"máx(0, rendimiento neto × (1 − reducción)) × tipo marginal{deducted}; "
                       f"{net_formula}")
        tax_sources = tax.sources
    else:  # TaxParams lo impide; se deja explícito
        raise ValueError("Falta el tipo marginal o el perfil del IRPF")

    after_tax_monthly = money((operating_cashflow - annual_tax) / TWELVE)
    cash_invested = money(inv.price + inv.purchase_costs + inv.renovation - inv.loan)
    coc = (
        ratio((operating_cashflow - annual_tax) / cash_invested)
        if cash_invested > 0
        else Decimal(0)
    )
    gross = ratio(annual_rent / inv.price) if inv.price > 0 else Decimal(0)

    operating_sources = combine_sources(inv.sources, rent.sources)
    all_sources = combine_sources(inv.sources, rent.sources, tax_sources)
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
            tax_formula,
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
        pending_excess=next_pending,
    )


def _taxable_net(
    inv: InvestmentInputs,
    tax: TaxParams,
    collected: Decimal,
    other_costs: Decimal,
    maintenance: Decimal,
    pending: tuple[PendingExcess, ...],
) -> tuple[Decimal, tuple[PendingExcess, ...], str]:
    """Rendimiento neto antes de reducciones, exceso pendiente y cómo se ha calculado."""
    income = collected * (1 - tax.gross_bonus)
    bonus = f"ingresos × (1 − bonificación {tax.gross_bonus})" if tax.gross_bonus else "ingresos"
    base = "en la base del ahorro" if tax.rental_base == "ahorro" else "en la base general"
    depreciation = inv.construction_value * tax.depreciation_rate
    if tax.deductible_expenses == "intereses":
        net = income - inv.first_year_interest
        if tax.expense_cap == "sin_negativo":
            net = max(net, Decimal(0))
        return (net, (), f"rendimiento = máx(0, {bonus} − intereses), {base}"
                if tax.expense_cap == "sin_negativo" else f"rendimiento = {bonus} − intereses")
    if tax.expense_cap == "todos":
        # Navarra: todos los gastos, amortización incluida, hasta los ingresos; primero los del año
        expenses, left = _capped(income, other_costs + inv.first_year_interest + maintenance
                                 + depreciation, pending, tax.interest_repair_carryforward_years,
                                 current_first=True)
        return (income - expenses, left,
                f"rendimiento = {bonus} − gastos (todos, hasta los ingresos), {base}")
    financing_repair, left = _capped(income, inv.first_year_interest + maintenance, pending,
                                     tax.interest_repair_carryforward_years)
    return (income - other_costs - financing_repair - depreciation, left,
            f"rendimiento = {bonus} − gastos − amortización, con intereses y reparación hasta "
            f"los ingresos, {base}")


def _capped(
    gross: Decimal,
    current: Decimal,
    pending: tuple[PendingExcess, ...],
    carryforward_years: int,
    current_first: bool = False,
) -> tuple[Decimal, tuple[PendingExcess, ...]]:
    """Gastos con tope deducibles del año y exceso que queda pendiente.

    El total (lo arrastrado más lo del año) no puede superar los rendimientos íntegros. Si la
    norma no fija el orden se usa primero lo más antiguo, que es lo que antes caduca; con
    `current_first`, primero los del año (Navarra, art. 25.1).
    """
    room = max(gross, Decimal(0))
    left: list[PendingExcess] = []
    used_now = Decimal(0)
    if current_first:
        used_now = min(current, room)
        room -= used_now
    for p in pending:
        used = min(p.amount, room)
        room -= used
        if p.amount - used > 0 and p.years_left > 1:
            left.append(PendingExcess(money(p.amount - used), p.years_left - 1))
    if not current_first:
        used_now = min(current, room)
        room -= used_now
    if current - used_now > 0:
        left.append(PendingExcess(money(current - used_now), carryforward_years))
    return max(gross, Decimal(0)) - room, tuple(left)
