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
    scale_tax,
)
from housefinder.regulation.kinds import (
    RENTAL_TYPES,
    BracketScale,
    DescendantsMinimum,
    InterestRepairLimit,
    LeaseExtension,
    RateParams,
    ReductionCases,
    RentalFacts,
    RentalRegime,
    TaxpayerMinimum,
    TransferTaxParams,
    ZoneDeclaration,
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
    """Impuesto de la compra de vivienda usada (ITP).

    La vivienda nueva paga IVA y AJD: ver `regulation.transactions.purchase_costs`.
    """
    if new_build:
        raise LookupError("La vivienda nueva no paga ITP sino IVA y AJD (purchase_costs)")
    rule = _rule(book, "impuesto_compra_segunda_mano", territory, on, include_pending,
                 allow_unverified)
    params = _transfer_tax(rule)
    sources = combine_sources(price_sources, (rule.ref,))
    if params.brackets is not None and params.whole_value:
        rate = max((b for b in params.brackets if price >= b.from_amount),
                   key=lambda b: b.from_amount).rate
        figure = Figure(
            "purchase_costs.transfer_tax",
            money(price * rate),
            "EUR",
            f"precio × tipo del ITP del tramo del precio, sobre todo el precio ({rate})",
            sources,
        )
    elif params.brackets is not None:
        scale = tuple(Bracket(b.from_amount, b.rate) for b in params.brackets)
        steps = ", ".join(f"{b.rate} desde {b.from_amount}" for b in params.brackets)
        figure = Figure(
            "purchase_costs.transfer_tax",
            money(scale_tax(price, scale)),
            "EUR",
            f"escala del ITP sobre el precio, cada tipo en su tramo ({steps})",
            sources,
        )
    else:
        assert params.rate is not None
        figure = Figure("purchase_costs.transfer_tax", money(price * params.rate), "EUR",
                        f"precio × tipo del ITP ({params.rate})", sources)
    return with_rebate(figure, *tax_rebate(book, "bonificacion_itp", territory, on,
                                           include_pending, allow_unverified))


def purchase_tax_rate(
    book: RuleBook,
    territory: str,
    on: date,
    new_build: bool,
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> Figure:
    """Tipo del impuesto de compra sobre el precio, para la capacidad de compra."""
    if new_build:
        raise LookupError("La vivienda nueva no paga ITP sino IVA y AJD (purchase_costs)")
    rule = _rule(book, "impuesto_compra_segunda_mano", territory, on, include_pending,
                 allow_unverified)
    params = _transfer_tax(rule)
    if params.rate is None:
        raise LookupError(f"El ITP de {territory} va por tramos: no tiene un tipo único "
                          "(usar purchase_tax con el precio)")
    rebate, rebate_refs = tax_rebate(book, "bonificacion_itp", territory, on, include_pending,
                                     allow_unverified)
    return Figure(
        "purchase_costs.transfer_tax_rate",
        params.rate * (1 - rebate),
        "ratio",
        "tipo del ITP de la regla vigente"
        + (f" × (1 − bonificación de la cuota {rebate})" if rebate else ""),
        (rule.ref, *rebate_refs),
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
    figure = Figure(
        "holding_costs.ibi_annual",
        money(cadastral_value * rate),
        "EUR/año",
        f"valor catastral × tipo del IBI ({rate})",
        combine_sources(cadastral_sources, (rule.ref,)),
    )
    return with_rebate(figure, *tax_rebate(book, "bonificacion_ibi", territory, on, False,
                                           allow_unverified))


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
    housing_lease: bool = True,
    housing_lease_sources: tuple[SourceRef, ...] = (),
) -> TaxParams:
    """Parámetros fiscales del alquiler para el motor de cash flow.

    Con `income` (perfil de `income_tax_profile`), el impuesto es la cuota incremental
    (ADR-0007). Sin él, `marginal_rate` es un supuesto del usuario: citarlo en
    `marginal_rate_sources` como `assumption`.

    `housing_lease=False`: la renta no es de alquiler de vivienda (temporada, turístico…) y no
    tiene la reducción del art. 23.2; `housing_lease_sources` cita la regla que lo dice
    (ADR-0024).
    """
    reduction_value = Decimal(0)
    reduction_sources: tuple[SourceRef, ...] = housing_lease_sources
    if housing_lease:
        reduction = rental_reduction(book, territory, contract_date, situation,
                                     include_pending, allow_unverified)
        reduction_value, reduction_sources = reduction.reduction, (reduction.rule.ref,)
    depreciation_rule = _rule(book, "amortizacion_inmueble_alquiler", territory,
                              contract_date, include_pending, allow_unverified)
    limit_rule = _rule(book, "limite_intereses_reparacion", territory, contract_date,
                       include_pending, allow_unverified)
    limit = parse_params(limit_rule.kind, limit_rule.params)
    if not isinstance(limit, InterestRepairLimit):
        raise TypeError(f"{limit_rule.id}: se esperaba un límite de intereses y reparación")
    deduction, deduction_refs = tax_rebate(book, "deduccion_irpf_rentas_territorio", territory,
                                           contract_date, include_pending, allow_unverified)
    return TaxParams(
        marginal_rate=marginal_rate,
        rental_income_reduction=reduction_value,
        depreciation_rate=_rate(depreciation_rule),
        interest_repair_carryforward_years=limit.carryforward_years,
        sources=(*reduction_sources, depreciation_rule.ref, limit_rule.ref,
                 *marginal_rate_sources, *deduction_refs),
        income_tax=income,
        territorial_deduction=deduction,
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


@dataclass(frozen=True)
class StressedZone:
    declared: bool
    checked_through: date  # última resolución trimestral revisada
    rule: Rule
    area: str | None = None  # ámbito declarado si no es todo el municipio


def stressed_zone(
    book: RuleBook, territory: str, on: date, allow_unverified: bool = False
) -> StressedZone:
    """Si el inmueble está en zona de mercado residencial tensionado (hecho `stressed_zone`).

    Un territorio sin regla no se da por no tensionado: es un error, porque no consta que se
    hayan revisado sus resoluciones.
    """
    rule = _rule(book, "zona_tensionada", territory, on, False, allow_unverified)
    zone = parse_params(rule.kind, rule.params)
    if not isinstance(zone, ZoneDeclaration):
        raise TypeError(f"{rule.id}: se esperaba una declaración de zona")
    return StressedZone(zone.declared, zone.checked_through, rule, zone.area)


@dataclass(frozen=True)
class RegimeRequirement:
    code: str
    description: str
    source_url: str
    rule_id: str  # regla de la que sale


@dataclass(frozen=True)
class RentalRegimeResult:
    rental_type: str
    regime: str  # el del nivel más específico
    allowed: bool  # False si algún nivel lo prohíbe
    requirements: tuple[RegimeRequirement, ...]  # de todos los niveles, del estatal al municipal
    rules: tuple[Rule, ...]
    # Reducción del art. 23.2 del IRPF: la del nivel más específico que lo dice; None, por
    # confirmar (ADR-0024)
    irpf_reduction: bool | None = None
    tax_notes: tuple[str, ...] = ()


def rental_regime(
    book: RuleBook,
    rental_type: str,
    territory: str,
    on: date,
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> RentalRegimeResult:
    """Régimen y requisitos de un tipo de alquiler en un territorio.

    A diferencia de los tipos impositivos, aquí no gana la regla más específica: los
    requisitos estatales, autonómicos y municipales se suman.
    """
    if rental_type not in RENTAL_TYPES:
        known = ", ".join(RENTAL_TYPES)
        raise ValueError(f"Tipo de alquiler desconocido: {rental_type!r} ({known})")
    kind = f"regimen_alquiler_{rental_type}"
    rules: list[Rule] = []
    for level in _territory_levels(territory):
        rule = book.resolve(kind, level, on, include_pending, allow_unverified)
        if rule is not None and rule.id not in {r.id for r in rules}:
            rules.append(rule)
    if not rules:
        raise LookupError(f"No hay régimen de {kind} para {territory} el {on}")
    regimes: list[RentalRegime] = []
    for rule in rules:
        regime = parse_params(rule.kind, rule.params)
        if not isinstance(regime, RentalRegime):
            raise TypeError(f"{rule.id}: se esperaba un régimen de alquiler")
        regimes.append(regime)
    requirements = tuple(
        RegimeRequirement(req.code, req.description, req.source_url, rule.id)
        for rule, regime in zip(rules, regimes, strict=True)
        for req in regime.requirements
    )
    return RentalRegimeResult(
        rental_type=rental_type,
        regime=regimes[-1].regime,
        allowed=all(regime.allowed for regime in regimes),
        requirements=requirements,
        rules=tuple(rules),
        irpf_reduction=next((r.irpf_reduction for r in reversed(regimes)
                             if r.irpf_reduction is not None), None),
        tax_notes=tuple(r.tax_note for r in regimes if r.tax_note),
    )


def _territory_levels(territory: str) -> list[str]:
    """«ES-13-28079» → ["ES", "ES-13", "ES-13-28079"]."""
    parts = territory.split("-")
    return ["-".join(parts[: i + 1]) for i in range(len(parts))]


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


def tax_rebate(
    book: RuleBook,
    kind: str,
    territory: str,
    on: date,
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> tuple[Decimal, tuple[SourceRef, ...]]:
    """Bonificación de la cuota de un tributo en el territorio del inmueble (ADR-0045).

    Sin regla no hay bonificación (0): a diferencia de los tipos, es la excepción.
    """
    rule = book.resolve(kind, territory, on, include_pending, allow_unverified)
    if rule is None:
        return Decimal(0), ()
    return _rate(rule), (rule.ref,)


def with_rebate(figure: Figure, rebate: Decimal, refs: tuple[SourceRef, ...]) -> Figure:
    """La cuota de `figure` con la bonificación aplicada; igual si no la hay."""
    if not rebate:
        return figure
    return Figure(
        figure.key,
        money(figure.value * (1 - rebate)),
        figure.unit,
        f"{figure.formula}, menos la bonificación de la cuota ({rebate})",
        combine_sources(figure.sources, refs),
    )


def _transfer_tax(rule: Rule) -> TransferTaxParams:
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, TransferTaxParams):
        raise TypeError(f"{rule.id}: se esperaba el ITP (rate o brackets)")
    return params


def _rate(rule: Rule) -> Decimal:
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, RateParams):
        raise TypeError(f"{rule.id}: se esperaba un tipo único (rate)")
    return params.rate


@dataclass(frozen=True)
class LeaseExtensionResult:
    params: LeaseExtension
    rule: Rule


def lease_extension(
    book: RuleBook,
    territory: str,
    on: date,
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> LeaseExtensionResult:
    """Duración mínima, prórroga tácita, preaviso e indemnización del alquiler de vivienda
    habitual vigentes en `on` (o en el escenario con reglas pendientes)."""
    rule = _rule(book, "prorroga_alquiler_habitual", territory, on, include_pending,
                 allow_unverified)
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, LeaseExtension):
        raise TypeError(f"{rule.id}: se esperaba la prórroga del alquiler")
    return LeaseExtensionResult(params, rule)
