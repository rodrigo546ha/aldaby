"""Resolutores de normativa: de las reglas vigentes a entradas de los motores (F2.7).

Cada resolutor elige la regla aplicable con el `RuleBook` y devuelve cifras o parámetros
que citan esa regla. Una regla sin verificar solo se usa con `allow_unverified=True`, y
su cita sale provisional, así que toda cifra que dependa de ella también.

Fechas: el impuesto de compra se resuelve en la fecha de compra, el IBI en el año del
devengo y las reducciones del IRPF en la fecha de celebración del contrato de alquiler.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money
from housefinder.engines.cashflow import TaxParams
from housefinder.engines.irpf import (
    Bracket,
    IncomeTaxProfile,
    IrpfPart,
    MinimumAmounts,
    personal_minimum,
)
from housefinder.regulation.kinds import (
    BracketScale,
    DescendantsMinimum,
    InterestRepairLimit,
    RateParams,
    ReductionCases,
    RentalFacts,
    TaxpayerMinimum,
    parse_params,
)
from housefinder.regulation.rules import Rule, RuleBook


def purchase_tax(
    book: RuleBook,
    price: Decimal,
    territory: str,
    on: date,
    new_build: bool,
    price_sources: tuple[SourceRef, ...] = (),
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> Figure:
    """Impuesto de la compra: ITP para vivienda usada.

    Vivienda nueva (IVA y AJD) aún no está cargada: el AJD de Madrid necesita un esquema
    propio (inventario, fila 1.3).
    """
    if new_build:
        raise LookupError("El impuesto de compra de vivienda nueva (IVA y AJD) aún no está cargado")
    rule = _rule(book, "impuesto_compra_segunda_mano", territory, on, include_pending,
                 allow_unverified)
    rate = _rate(rule)
    return Figure(
        "purchase_costs.transfer_tax",
        money(price * rate),
        "EUR",
        f"precio × tipo del ITP ({rate})",
        combine_sources(price_sources, (rule.ref,)),
    )


def ibi_annual(
    book: RuleBook,
    cadastral_value: Decimal,
    territory: str,
    on: date,
    cadastral_sources: tuple[SourceRef, ...] = (),
    allow_unverified: bool = False,
) -> Figure:
    """IBI anual: valor catastral × tipo de gravamen del municipio."""
    rule = _rule(book, "tipo_ibi", territory, on, False, allow_unverified)
    rate = _rate(rule)
    return Figure(
        "holding_costs.ibi_annual",
        money(cadastral_value * rate),
        "EUR/año",
        f"valor catastral × tipo del IBI ({rate})",
        combine_sources(cadastral_sources, (rule.ref,)),
    )


@dataclass(frozen=True)
class RentalReduction:
    rule: Rule
    case: str | None  # supuesto aplicado; None si la situación no encaja en ninguno
    reduction: Decimal  # 0 si no hay supuesto aplicable


def rental_reduction(
    book: RuleBook,
    territory: str,
    contract_date: date,
    situation: RentalFacts,
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> RentalReduction:
    """Reducción del art. 23.2 de la Ley del IRPF para una situación de contrato.

    Cada caso de la regla declara los hechos que exige; se aplica el de mayor reducción
    entre los que se cumplen. Si no se cumple ninguno, no hay reducción.
    """
    rule = _rule(book, "reduccion_irpf_alquiler", territory, contract_date, include_pending,
                 allow_unverified)
    cases = parse_params(rule.kind, rule.params)
    if not isinstance(cases, ReductionCases):
        raise TypeError(f"{rule.id}: se esperaba una reducción por casos")
    best = cases.best(situation)
    if best is None:
        return RentalReduction(rule, None, Decimal(0))
    return RentalReduction(rule, best.condition, best.reduction)


def tax_params(
    book: RuleBook,
    territory: str,
    contract_date: date,
    situation: RentalFacts,
    marginal_rate: Decimal | None = None,
    marginal_rate_sources: tuple[SourceRef, ...] = (),
    include_pending: bool = False,
    allow_unverified: bool = False,
    income: IncomeTaxProfile | None = None,
) -> TaxParams:
    """Parámetros fiscales del alquiler para el motor de cash flow.

    Con `income` (perfil de `income_tax_profile`), el impuesto es la cuota incremental
    (ADR-0007). Sin él, `marginal_rate` es un supuesto del usuario: citarlo en
    `marginal_rate_sources` como `assumption`.
    """
    reduction = rental_reduction(book, territory, contract_date, situation, include_pending,
                                 allow_unverified)
    depreciation_rule = _rule(book, "amortizacion_inmueble_alquiler", territory,
                              contract_date, include_pending, allow_unverified)
    limit_rule = _rule(book, "limite_intereses_reparacion", territory, contract_date,
                       include_pending, allow_unverified)
    limit = parse_params(limit_rule.kind, limit_rule.params)
    if not isinstance(limit, InterestRepairLimit):
        raise TypeError(f"{limit_rule.id}: se esperaba un límite de intereses y reparación")
    return TaxParams(
        marginal_rate=marginal_rate,
        rental_income_reduction=reduction.reduction,
        depreciation_rate=_rate(depreciation_rule),
        interest_repair_carryforward_years=limit.carryforward_years,
        sources=(reduction.rule.ref, depreciation_rule.ref, limit_rule.ref,
                 *marginal_rate_sources),
        income_tax=income,
    )


def income_tax_profile(
    book: RuleBook,
    residence: str,
    tax_year: date,
    other_base: Decimal,
    age: int,
    descendant_ages: tuple[int, ...],
    other_base_sources: tuple[SourceRef, ...] = (),
    allow_unverified: bool = False,
) -> IncomeTaxProfile:
    """IRPF del contribuyente sin el alquiler, para la cuota incremental (ADR-0007).

    `residence`: comunidad de residencia del contribuyente (`ES-13`), no la del inmueble.
    La parte estatal usa las reglas de `ES`; la autonómica, la escala de la comunidad (sin
    heredar la estatal) y sus mínimos (heredando los estatales si no los ha sustituido).
    `descendant_ages`: solo los descendientes que dan derecho al mínimo, en orden.
    """
    state_scale = _rule(book, "escala_irpf_general_estatal", "ES", tax_year, False,
                        allow_unverified)
    regional_scale = _rule(book, "escala_irpf_general_autonomica", residence, tax_year, False,
                           allow_unverified)
    state_min, state_refs = _minimum(book, "ES", tax_year, age, descendant_ages,
                                     allow_unverified)
    regional_min, regional_refs = _minimum(book, residence, tax_year, age, descendant_ages,
                                           allow_unverified)
    return IncomeTaxProfile(
        other_base=other_base,
        state=IrpfPart(_scale(state_scale), state_min),
        regional=IrpfPart(_scale(regional_scale), regional_min),
        sources=combine_sources(
            other_base_sources,
            (state_scale.ref, regional_scale.ref),
            state_refs,
            regional_refs,
        ),
    )


def _minimum(
    book: RuleBook,
    territory: str,
    tax_year: date,
    age: int,
    descendant_ages: tuple[int, ...],
    allow_unverified: bool,
) -> tuple[Decimal, tuple[SourceRef, ...]]:
    taxpayer_rule = _rule(book, "minimo_contribuyente", territory, tax_year, False,
                          allow_unverified)
    descendants_rule = _rule(book, "minimo_descendientes", territory, tax_year, False,
                             allow_unverified)
    taxpayer = parse_params(taxpayer_rule.kind, taxpayer_rule.params)
    descendants = parse_params(descendants_rule.kind, descendants_rule.params)
    if not isinstance(taxpayer, TaxpayerMinimum) or not isinstance(
        descendants, DescendantsMinimum
    ):
        raise TypeError(f"{taxpayer_rule.id} / {descendants_rule.id}: mínimos mal formados")
    amounts = MinimumAmounts(
        general=taxpayer.general,
        over_65_extra=taxpayer.over_65_extra,
        over_75_extra=taxpayer.over_75_extra,
        descendants=(
            descendants.first,
            descendants.second,
            descendants.third,
            descendants.fourth_and_more,
        ),
        under_3_extra=descendants.under_3_extra,
    )
    minimum = personal_minimum(amounts, age, descendant_ages)
    return minimum, (taxpayer_rule.ref, descendants_rule.ref)


def _scale(rule: Rule) -> tuple[Bracket, ...]:
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, BracketScale):
        raise TypeError(f"{rule.id}: se esperaba una escala por tramos")
    return tuple(Bracket(b.from_amount, b.rate) for b in params.brackets)


def _rule(
    book: RuleBook,
    kind: str,
    territory: str,
    on: date,
    include_pending: bool,
    allow_unverified: bool,
) -> Rule:
    rule = book.resolve(kind, territory, on, include_pending, allow_unverified)
    if rule is None:
        verified = "" if allow_unverified else " verificada"
        raise LookupError(f"No hay regla{verified} de {kind} para {territory} el {on}")
    return rule


def _rate(rule: Rule) -> Decimal:
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, RateParams):
        raise TypeError(f"{rule.id}: se esperaba un tipo único (rate)")
    return params.rate
