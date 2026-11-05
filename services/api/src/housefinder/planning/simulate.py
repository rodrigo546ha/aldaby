"""Simulación de una inversión de punta a punta (G3, F1.10).

Un solo camino de cálculo (D4): el endpoint del simulador, el plan completo y el agente
llaman a `simulate`. Compone, en este orden:

1. Gastos de compra que fija la normativa (impuesto, AJD, notaría si la paga el comprador,
   registro) y los demás (gestoría, tasación, copias) como tasa supuesta del usuario.
2. Capacidad de compra con los criterios bancarios del `ParamBook` y la tasa de gastos de
   compra del inmueble simulado.
3. Hipoteca a tipo fijo: cuota y cuota en estrés.
4. Cash flow del primer año con los intereses reales del cuadro y la fiscalidad resuelta:
   cuota incremental si se conoce la base del usuario (ADR-0007), tipo marginal si no.
5. Plazo recomendado en estrés.
6. TIR al horizonte con la venta: escritura (si la paga el vendedor), plusvalía municipal y
   cuota incremental del ahorro, con la normativa conocida hoy para la fecha de la venta.
7. Si hay ofertas alternativas, comparación con la trayectoria del Euríbor (ADR-0006).

Las incoherencias del plan (precio por encima del máximo, falta de ahorro…) no paran el
cálculo: salen como avisos, porque el usuario puede querer ver el plan igualmente.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal

from housefinder.core.figures import Figure, Series, SourceRef, combine_sources, money, ratio
from housefinder.engines.cashflow import (
    CashflowResult,
    InvestmentInputs,
    RentalAssumptions,
    TaxParams,
)
from housefinder.engines.irpf import IncomeTaxProfile
from housefinder.engines.irr import (
    IrrResult,
    investment_irr,
    projected_sale_price,
    sale_base,
    yearly_cashflows,
)
from housefinder.engines.mortgage import (
    AffordabilityResult,
    BuyerFinances,
    MortgageComparison,
    affordability,
    amortization_schedule,
    compare_mortgages,
    first_year_interest,
    monthly_payment,
    stressed_payment,
    yearly_amortization,
)
from housefinder.engines.rates import MortgageTerms
from housefinder.engines.taxes import municipal_gains_tax
from housefinder.engines.term import TermRecommendation, recommended_term
from housefinder.engines.valuation import Range
from housefinder.params.bank import bank_criteria
from housefinder.params.book import ParamBook
from housefinder.params.euribor import euribor_12m_path
from housefinder.regulation.kinds import RentalFacts
from housefinder.regulation.resolvers import (
    ibi_annual,
    income_tax_profile,
    rental_tax_base,
    stressed_zone,
    tax_params,
)
from housefinder.regulation.rules import RuleBook
from housefinder.regulation.transactions import (
    DeedAgreement,
    PurchaseCosts,
    buyer_pays_deed,
    municipal_gains_params,
    notary_fee,
    purchase_costs,
    savings_tax_profile,
)

# Los criterios bancarios aún no dependen de la ubicación: ámbito nacional.
BANK_TERRITORY = "ES"

BUYER = SourceRef("user_input", "comprador")
PROPERTY = SourceRef("user_input", "inmueble")
FINANCING = SourceRef("user_input", "financiacion")
RENT = SourceRef("user_input", "alquiler")
# Precios de mercado, no normativa: los fija el usuario (inventario, sección 4).
OTHER_PURCHASE_COSTS = SourceRef("assumption", "gestoria-tasacion-y-copias")
SALE_COSTS = SourceRef("assumption", "gastos-de-venta")
MARGINAL_RATE = SourceRef("assumption", "tipo-marginal")
APPRECIATION = SourceRef("assumption", "revalorizacion")
# La venta se calcula con las reglas conocidas hoy para su fecha y la situación personal de hoy.
RULES_AT_SALE = SourceRef("assumption", "normativa-conocida-hoy-en-la-venta")
PERSONAL_AT_SALE = SourceRef("assumption", "situacion-personal-constante-hasta-la-venta")


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
    savings_base: Decimal = Decimal(0)  # base del ahorro del año de la venta, sin la venta

    def __post_init__(self) -> None:
        if (self.taxable_base is None) == (self.marginal_rate is None):
            raise ValueError("Indica la base liquidable o el tipo marginal, uno de los dos")


@dataclass(frozen=True)
class PropertyInput:
    price: Decimal
    territory: str  # municipio con código INE (ES-13-28079)
    construction_value: Decimal  # base de la amortización fiscal
    other_purchase_cost_rate: Decimal  # gestoría, tasación y copias sobre el precio
    community_fees_monthly: Decimal
    insurance_annual: Decimal  # hogar + impago
    renovation: Decimal = Decimal(0)
    new_build: bool = False
    cadastral_value: Decimal | None = None  # valor catastral total (IBI y plusvalía)
    ibi_annual: Decimal | None = None  # si el usuario conoce el recibo
    cadastral_land_value: Decimal | None = None  # valor catastral del suelo (plusvalía)
    deed_agreement: DeedAgreement = "ley"  # quién paga la escritura de compra

    def __post_init__(self) -> None:
        if self.cadastral_value is None and self.ibi_annual is None:
            raise ValueError("Indica el valor catastral o el IBI anual")


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
    # False: no es alquiler de vivienda (temporada, turístico…) y no hay reducción; las
    # fuentes citan la regla del régimen que lo dice (ADR-0024)
    housing_lease: bool = True
    housing_lease_sources: tuple[SourceRef, ...] = ()
    # Subida anual de la renta desde el segundo año, para la TIR (ADR-0060); None: constante
    growth: Figure | None = None
    # Subida anual de la comunidad, el IBI y el seguro (ADR-0061); None: constantes
    cost_growth: Figure | None = None


@dataclass(frozen=True)
class AppreciationAlternative:
    """Otro escenario de revalorización con el que se repite la venta y la TIR (F5.5)."""

    name: str  # 'conservative', 'optimistic'…: la TIR sale como irr.rate_<name>
    rate: Decimal
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class ExitInput:
    appreciation_rate: Decimal
    sale_cost_rate: Decimal  # agencia y otros gastos de venta de mercado, sobre el precio
    horizon_years: int = 10
    # De dónde sale la revalorización: el supuesto del usuario o el escenario base (F5.5)
    appreciation_sources: tuple[SourceRef, ...] = (APPRECIATION,)
    alternatives: tuple[AppreciationAlternative, ...] = ()
    # Precio estimado del inmueble con su rango: la venta parte del precio acotado a él (ADR-0059)
    market_value: Range | None = None
    market_value_sources: tuple[SourceRef, ...] = ()


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
    regulated_costs: PurchaseCosts
    other_purchase_costs: Figure
    purchase_costs: Figure
    loan: Figure
    loan_years: Figure
    monthly_payment: Figure
    stressed_payment: Figure
    ibi_annual: Figure
    cashflow: CashflowResult  # primer año
    term: TermRecommendation
    sale_notary: Figure | None  # escritura de venta, si la paga el vendedor
    municipal_gains: Figure | None  # None si faltan los valores catastrales
    irr: IrrResult
    comparison: MortgageComparison | None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    irr_alternatives: tuple[Figure, ...] = ()  # TIR de los otros escenarios (irr.rate_<nombre>)
    series: tuple[Series, ...] = ()  # año a año, para las gráficas (ADR-0050)
    rent_growth: Figure | None = None  # subida anual de la renta en la TIR (ADR-0060)
    cost_growth: Figure | None = None  # subida anual de los gastos fijos (ADR-0061)

    def figures(self) -> tuple[Figure, ...]:
        """Todas las cifras del plan, cada clave una vez."""
        a, c, t = self.affordability, self.cashflow, self.term
        result = [
            a.max_price, a.max_loan, a.max_payment, a.years,
            *self.regulated_costs.figures(), self.other_purchase_costs, self.purchase_costs,
            self.loan, self.loan_years, self.monthly_payment, self.stressed_payment,
            self.ibi_annual,
            c.gross_yield, c.annual_operating_cashflow, c.annual_tax,
            c.annual_after_tax, c.monthly_cashflow_after_tax, c.cash_invested, c.cash_on_cash,
            t.years, t.stressed_monthly_payment, t.stressed_monthly_cashflow,
            self.irr.sale_base, self.irr.sale_price,
        ]
        result += [f for f in (self.sale_notary, self.municipal_gains) if f is not None]
        result += [self.irr.capital_gains_tax, self.irr.net_sale_proceeds]
        if self.irr.irr is not None:
            result.append(self.irr.irr)
        result += list(self.irr_alternatives)
        result += [f for f in (self.rent_growth, self.cost_growth) if f is not None]
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

    # 1. Gastos de compra.
    regulated = purchase_costs(rules, prop.price, prop.territory, on, prop.new_build,
                               prop.deed_agreement, (PROPERTY,), include_pending,
                               allow_unverified)
    other_costs = Figure(
        "purchase_costs.other",
        money(prop.price * prop.other_purchase_cost_rate),
        "EUR",
        "precio × tasa de gestoría, tasación y copias",
        (PROPERTY, OTHER_PURCHASE_COSTS),
    )
    purchase_total = Figure(
        "purchase_costs.total",
        regulated.total.value + other_costs.value,
        "EUR",
        "gastos que fija la normativa + gestoría, tasación y copias",
        combine_sources(regulated.total.sources, other_costs.sources),
    )

    # 2. Capacidad de compra, con la tasa de gastos del inmueble simulado.
    aff = affordability(
        BuyerFinances(
            net_monthly_income=buyer.net_monthly_income,
            existing_monthly_debt=buyer.existing_monthly_debt,
            available_savings=buyer.available_savings,
            age=buyer.age,
            sources=(BUYER,),
        ),
        annual_rate=fin.annual_rate,
        purchase_cost_rate=ratio(purchase_total.value / prop.price),
        criteria=criteria,
        rate_sources=(FINANCING,),
        purchase_cost_sources=purchase_total.sources,
    )
    max_years = int(aff.years.value)

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
    # En los IRPF forales vascos el alquiler de vivienda va a la base del ahorro (ADR-0046)
    rental_base = rental_tax_base(rules, buyer.residence, rental.contract_date,
                                  rental.housing_lease, allow_unverified)
    income: IncomeTaxProfile | None = None
    if buyer.taxable_base is not None and rental_base == "ahorro":
        income = savings_tax_profile(
            rules, buyer.residence, rental.contract_date, buyer.savings_base,
            buyer.taxable_base, buyer.age, buyer.descendant_ages, (BUYER,), allow_unverified)
    elif buyer.taxable_base is not None:
        income = income_tax_profile(rules, buyer.residence, rental.contract_date,
                                    buyer.taxable_base, buyer.age, buyer.descendant_ages,
                                    (BUYER,), allow_unverified)
    situation, zone_refs, zone_warnings = _zone_fact(rules, prop.territory, rental.contract_date,
                                                     rental.situation, allow_unverified)
    tax = tax_params(
        rules,
        prop.territory,
        rental.contract_date,
        situation,
        marginal_rate=buyer.marginal_rate,
        marginal_rate_sources=(MARGINAL_RATE,) if buyer.marginal_rate is not None else (),
        include_pending=include_pending,
        allow_unverified=allow_unverified,
        income=income,
        housing_lease=rental.housing_lease,
        housing_lease_sources=rental.housing_lease_sources,
        residence=buyer.residence,
        fact_sources=zone_refs,
    )
    investment = InvestmentInputs(
        price=prop.price,
        purchase_costs=purchase_total.value,
        renovation=prop.renovation,
        loan=loan.value,
        monthly_mortgage_payment=payment.value,
        first_year_interest=(
            first_year_interest(loan.value, fin.annual_rate, years)
            if loan.value > 0
            else Decimal(0)
        ),
        construction_value=prop.construction_value,
        sources=combine_sources((PROPERTY,), purchase_total.sources, loan_sources),
    )
    cashflow = yearly_cashflows(investment, rent, tax, fin.annual_rate, years, 1)[0]

    # 5. Plazo recomendado.
    term = recommended_term(investment, rent, tax, fin.annual_rate, fin.rate_shock, max_years,
                            rate_sources=(FINANCING,), max_years_sources=aff.years.sources)

    # 6. Venta y TIR, con la revalorización base y con cada escenario alternativo.
    exit_ = inp.exit
    sale_date = _years_later(on, exit_.horizon_years)
    buyer_pays, _ = buyer_pays_deed(rules, sale_date, "ley", allow_unverified)
    gains_profile = savings_tax_profile(
        rules, buyer.residence, sale_date, buyer.savings_base, buyer.taxable_base, buyer.age,
        buyer.descendant_ages, (BUYER, RULES_AT_SALE, PERSONAL_AT_SALE), allow_unverified,
    )

    growth = inp.rental.growth.value if inp.rental.growth is not None else Decimal(0)
    growth_sources = inp.rental.growth.sources if inp.rental.growth is not None else ()
    costs = inp.rental.cost_growth

    def sale_and_irr(
        rate: Decimal, appreciation_sources: tuple[SourceRef, ...]
    ) -> tuple[Figure | None, Figure | None, IrrResult]:
        base = sale_base(prop.price, exit_.market_value)
        sale_price = projected_sale_price(base, rate, exit_.horizon_years)
        value_sources = (PROPERTY, *exit_.market_value_sources, *appreciation_sources,
                         RULES_AT_SALE)
        notary = (None if buyer_pays else notary_fee(
            rules, sale_price, sale_date, "sale_costs.notary", value_sources, include_pending,
            allow_unverified))
        gains = _municipal_gains(rules, prop, sale_date, exit_.horizon_years, sale_price,
                                 value_sources, include_pending, allow_unverified)
        result = investment_irr(
            investment, rent, tax, fin.annual_rate, years,
            appreciation_rate=rate,
            sale_cost_rate=exit_.sale_cost_rate,
            horizon_years=exit_.horizon_years,
            rate_sources=(FINANCING,),
            appreciation_sources=appreciation_sources,
            sale_sources=(SALE_COSTS,),
            gains_tax_profile=gains_profile,
            extra_sale_costs=tuple(f for f in (notary, gains) if f is not None),
            market_value=exit_.market_value,
            market_value_sources=exit_.market_value_sources,
            rent_growth=growth,
            rent_growth_sources=growth_sources,
            cost_growth=costs.value if costs is not None else Decimal(0),
            cost_growth_sources=costs.sources if costs is not None else (),
        )
        return notary, gains, result

    sale_notary, municipal, irr = sale_and_irr(exit_.appreciation_rate,
                                               exit_.appreciation_sources)
    alternatives = []
    for alt in exit_.alternatives:
        alt_irr = sale_and_irr(alt.rate, alt.sources)[2].irr
        if alt_irr is not None:
            alternatives.append(replace(alt_irr, key=f"irr.rate_{alt.name}"))

    series = _series(investment, rent, tax, fin.annual_rate, years, exit_, loan.sources,
                     inp.rental.growth, costs)

    # 7. Comparación de ofertas.
    comparison = None
    if fin.alternatives:
        path = euribor_12m_path(params, on).rate_path(on)
        comparison = compare_mortgages(loan.value, years, fin.alternatives, path,
                                       fin.rate_shock, loan.sources)

    sim = InvestmentSimulation(
        affordability=aff,
        within_budget=prop.price <= aff.max_price.value,
        regulated_costs=regulated,
        other_purchase_costs=other_costs,
        purchase_costs=purchase_total,
        loan=loan,
        loan_years=loan_years,
        monthly_payment=payment,
        stressed_payment=stressed,
        ibi_annual=ibi,
        cashflow=cashflow,
        term=term,
        sale_notary=sale_notary,
        municipal_gains=municipal,
        irr=irr,
        comparison=comparison,
        irr_alternatives=tuple(alternatives),
        series=series,
        rent_growth=inp.rental.growth,
        cost_growth=costs,
    )
    return replace(sim, warnings=(*zone_warnings,
                                  *_warnings(sim, inp, criteria.max_ltv, max_years)))


def _series(investment: InvestmentInputs, rent: RentalAssumptions, tax: TaxParams,
            annual_rate: Decimal, loan_years: int, exit_: ExitInput,
            loan_sources: tuple[SourceRef, ...],
            rent_growth: Figure | None = None,
            cost_growth: Figure | None = None) -> tuple[Series, ...]:
    """Lo que el plan calcula año a año, para dibujarlo sin calcular nada en la web (ADR-0050)."""
    result: list[Series] = []
    if investment.loan > 0:
        years = yearly_amortization(amortization_schedule(investment.loan, annual_rate, loan_years))
        sources = combine_sources(loan_sources, (FINANCING,))
        terms = f"cuota francesa con tipo {annual_rate} a {loan_years} años"
        result += [
            Series("mortgage.balance_by_year", "EUR",
                   ((0, investment.loan), *((y.year, y.balance) for y in years)),
                   f"capital pendiente al acabar cada año; {terms}", sources),
            Series("mortgage.interest_by_year", "EUR/año",
                   tuple((y.year, y.interest) for y in years),
                   f"intereses de las cuotas de cada año; {terms}", sources),
            Series("mortgage.principal_by_year", "EUR/año",
                   tuple((y.year, y.principal) for y in years),
                   f"capital amortizado con las cuotas de cada año; {terms}", sources),
        ]
    growth = rent_growth.value if rent_growth is not None else Decimal(0)
    costs = cost_growth.value if cost_growth is not None else Decimal(0)
    flows = yearly_cashflows(investment, rent, tax, annual_rate, loan_years, exit_.horizon_years,
                             growth, costs)
    first = flows[0].annual_after_tax
    rising = (f", la renta que sube un {growth} al año desde el segundo (ADR-0060)"
              if growth else "")
    rising += f", los gastos fijos que suben un {costs} al año (ADR-0061)" if costs else ""
    result.append(Series(
        "cashflow.after_tax_by_year", "EUR/año",
        tuple((year, f.annual_after_tax.value) for year, f in enumerate(flows, start=1)),
        "cash flow operativo − impuesto de cada año, con las cuotas e intereses del cuadro"
        f"{rising} y el exceso de intereses que pasa de un año a otro",
        combine_sources(first.sources, rent_growth.sources if rent_growth else (),
                        cost_growth.sources if cost_growth else ())))
    scenarios = [("", exit_.appreciation_rate, exit_.appreciation_sources),
                 *((f"_{a.name}", a.rate, a.sources) for a in exit_.alternatives)]
    base = sale_base(investment.price, exit_.market_value)
    for suffix, rate, sources in scenarios:
        result.append(Series(
            f"valuation.price_by_year{suffix}", "EUR",
            tuple((t, projected_sale_price(base, rate, t))
                  for t in range(exit_.horizon_years + 1)),
            f"valor de partida de la venta × (1 + revalorización {rate})^año (ADR-0059)",
            combine_sources((PROPERTY,), exit_.market_value_sources, sources)))
    return tuple(result)


def _zone_fact(
    rules: RuleBook, territory: str, on: date, situation: RentalFacts, allow_unverified: bool
) -> tuple[RentalFacts, tuple[SourceRef, ...], tuple[str, ...]]:
    """El hecho «zona tensionada» del contrato, desde la regla de zona del inmueble.

    Con el municipio entero declarado, se marca y se cita la regla. Con solo una parte (barrios,
    núcleos) no se supone: se avisa. Sin declarar o sin revisar, vale lo que diga el usuario,
    que puede saber de una declaración que aún no está cargada.
    """
    try:
        zone = stressed_zone(rules, territory, on, allow_unverified)
    except LookupError:
        return situation, (), ()
    if not zone.declared or situation.stressed_zone:
        return situation, (), ()
    if zone.area is not None:
        return situation, (), (
            f"Solo parte del municipio es zona de mercado residencial tensionado ({zone.area}): "
            "el plan no supone que el inmueble esté dentro. Si lo está, indícalo: puede cambiar "
            "la reducción del IRPF del alquiler.",)
    return situation.model_copy(update={"stressed_zone": True}), (zone.rule.ref,), ()


def _years_later(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 de febrero
        return day.replace(year=day.year + years, day=28)


def _municipal_gains(
    rules: RuleBook,
    prop: PropertyInput,
    sale_date: date,
    holding_years: int,
    sale_price: Decimal,
    value_sources: tuple[SourceRef, ...],
    include_pending: bool,
    allow_unverified: bool,
) -> Figure | None:
    """Plusvalía municipal de la venta; None si faltan los valores catastrales."""
    if prop.cadastral_land_value is None or not prop.cadastral_value:
        return None
    resolved = municipal_gains_params(
        rules, prop.territory, sale_date, holding_years, 0, prop.cadastral_land_value,
        prop.cadastral_land_value / prop.cadastral_value,
        value_sources, include_pending, allow_unverified,
    )
    tax, method = municipal_gains_tax(resolved.params, prop.price, sale_price)
    return Figure(
        "sale_costs.municipal_gains_tax",
        tax,
        "EUR",
        f"plusvalía municipal: {method}; tipo {resolved.params.rate}, coeficiente "
        f"{resolved.params.coefficient} a {holding_years} años (valor del suelo de hoy)",
        resolved.sources,
    )


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
    if sim.municipal_gains is None:
        result.append(
            "Falta el valor catastral del suelo o el total: la venta no incluye la plusvalía "
            "municipal, así que la TIR sale más alta de lo que será."
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
