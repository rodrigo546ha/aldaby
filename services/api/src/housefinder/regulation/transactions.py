"""Resolutores de los gastos y tributos de la compra y la venta (F2.3, tanda 4).

Compra: impuesto (ITP en vivienda usada; IVA y AJD en nueva), arancel notarial de la
escritura si la paga el comprador y arancel registral de la inscripción, con su IVA.
Venta: escala del ahorro para la ganancia y plusvalía municipal.

Igual que en `resolvers`: una regla sin verificar solo se usa con `allow_unverified=True`
y las cifras que salen de ella son PROVISIONALES.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money
from housefinder.engines.irpf import IncomeTaxProfile, IrpfPart
from housefinder.engines.taxes import (
    FeeBand,
    FeeSchedule,
    MunicipalGainsTax,
    RateBand,
    banded_tax,
    scheduled_fee,
)
from housefinder.regulation.kinds import (
    BandedRate,
    DeedPayer,
    FeeScale,
    GainsCoefficients,
    GainsRate,
    parse_params,
)
from housefinder.regulation.resolvers import (
    _minimum,
    _rate,
    _rule,
    _scale,
    purchase_tax,
    tax_rebate,
    with_rebate,
)
from housefinder.regulation.rules import Rule, RuleBook

DeedAgreement = Literal["ley", "comprador", "vendedor"]


@dataclass(frozen=True)
class PurchaseCosts:
    tax: Figure  # ITP (usada) o IVA (nueva)
    stamp_duty: Figure | None  # AJD de la escritura (solo vivienda nueva)
    notary: Figure | None  # None si la escritura la paga el vendedor
    registry: Figure
    total: Figure

    def figures(self) -> tuple[Figure, ...]:
        optional = tuple(f for f in (self.stamp_duty, self.notary) if f is not None)
        return (self.tax, *optional, self.registry, self.total)


def purchase_costs(
    book: RuleBook,
    price: Decimal,
    territory: str,
    on: date,
    new_build: bool,
    deed_agreement: DeedAgreement = "ley",
    price_sources: tuple[SourceRef, ...] = (),
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> PurchaseCosts:
    """Gastos y tributos de la compra que fija la normativa, para un comprador persona física.

    `deed_agreement`: quién paga la escritura; «ley» aplica la regla del Código Civil
    (art. 1455: el vendedor, salvo pacto).
    """
    if new_build:
        # El del territorio: IGIC en Canarias, IPSI en Ceuta y Melilla, IVA en el resto
        vat_rule = _rule(book, "iva_vivienda_nueva", territory, on, include_pending,
                         allow_unverified)
        vat_rate = _rate(vat_rule)
        tax = Figure("purchase_costs.vat", money(price * vat_rate), "EUR",
                     f"precio × impuesto indirecto de la entrega ({vat_rate}; IVA, o IGIC o "
                     "IPSI donde rigen)",
                     combine_sources(price_sources, (vat_rule.ref,)))
        stamp_duty: Figure | None = stamp_duty_new_home(
            book, price, territory, on, price_sources, include_pending, allow_unverified
        )
    else:
        tax = purchase_tax(book, price, territory, on, False, price_sources, include_pending,
                           allow_unverified)
        stamp_duty = None

    buyer_pays, payer_sources = buyer_pays_deed(book, on, deed_agreement, allow_unverified)
    notary = (
        notary_fee(book, price, on, "purchase_costs.notary", price_sources + payer_sources,
                   include_pending, allow_unverified)
        if buyer_pays
        else None
    )
    registry = _fee_with_vat(book, "arancel_registral", price, on, "purchase_costs.registry",
                             "arancel registral de la inscripción", price_sources,
                             include_pending, allow_unverified)
    parts = [f for f in (tax, stamp_duty, notary, registry) if f is not None]
    total = Figure(
        "purchase_costs.regulated",
        sum((f.value for f in parts), Decimal(0)),
        "EUR",
        "impuesto + AJD + notaría (si la pagas tú) + registro, con el IVA de los aranceles",
        combine_sources(*(f.sources for f in parts)),
    )
    return PurchaseCosts(tax, stamp_duty, notary, registry, total)


def stamp_duty_new_home(
    book: RuleBook,
    price: Decimal,
    territory: str,
    on: date,
    price_sources: tuple[SourceRef, ...] = (),
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> Figure:
    """AJD de la escritura de compra de vivienda sujeta a IVA, adquirente persona física."""
    rule = _rule(book, "ajd_compra_vivienda", territory, on, include_pending, allow_unverified)
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, BandedRate):
        raise TypeError(f"{rule.id}: se esperaba un tipo por bandas")
    bands = tuple(RateBand(b.up_to, b.rate) for b in params.bands)
    figure = Figure(
        "purchase_costs.stamp_duty",
        banded_tax(price, bands, params.cap_jumps),
        "EUR",
        "precio × tipo de su banda de valor"
        + (", sin que el salto de banda suba la cuota más que la base" if params.cap_jumps
           else ""),
        combine_sources(price_sources, (rule.ref,)),
    )
    return with_rebate(figure, *tax_rebate(book, "bonificacion_ajd", territory, on,
                                           include_pending, allow_unverified))


def buyer_pays_deed(
    book: RuleBook, on: date, agreement: DeedAgreement, allow_unverified: bool = False
) -> tuple[bool, tuple[SourceRef, ...]]:
    """Si el comprador paga la escritura y de dónde sale: pacto o Código Civil."""
    if agreement != "ley":
        return agreement == "comprador", (SourceRef("user_input", "pacto-gastos-escritura"),)
    rule = _rule(book, "pagador_escritura_compraventa", "ES", on, False, allow_unverified)
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, DeedPayer):
        raise TypeError(f"{rule.id}: se esperaba quién paga la escritura")
    return params.deed == "comprador", (rule.ref,)


def notary_fee(
    book: RuleBook,
    value: Decimal,
    on: date,
    key: str,
    value_sources: tuple[SourceRef, ...] = (),
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> Figure:
    """Arancel notarial de la escritura de compraventa, con IVA."""
    return _fee_with_vat(book, "arancel_notarial", value, on, key,
                         "arancel notarial de la escritura", value_sources, include_pending,
                         allow_unverified)


def _fee_with_vat(
    book: RuleBook,
    kind: str,
    value: Decimal,
    on: date,
    key: str,
    label: str,
    value_sources: tuple[SourceRef, ...],
    include_pending: bool,
    allow_unverified: bool,
) -> Figure:
    rule = _rule(book, kind, "ES", on, include_pending, allow_unverified)
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, FeeScale):
        raise TypeError(f"{rule.id}: se esperaba un arancel por tramos")
    schedule = FeeSchedule(
        base_fee=params.base_fee,
        bands=tuple(FeeBand(b.from_amount, b.rate) for b in params.bands),
        min_fee=params.min_fee,
        max_fee=params.max_fee,
        max_base=params.max_base,
        rebate=params.rebate,
    )
    vat_rule = _rule(book, "iva_tipo_general", "ES", on, include_pending, allow_unverified)
    vat_rate = _rate(vat_rule)
    fee = scheduled_fee(value, schedule)
    return Figure(
        key,
        fee + money(fee * vat_rate),
        "EUR",
        f"{label} (escala por tramos, rebaja {params.rebate}) × (1 + IVA {vat_rate}); "
        "sin folios, copias ni suplidos",
        combine_sources(value_sources, (rule.ref, vat_rule.ref)),
    )


def savings_tax_profile(
    book: RuleBook,
    residence: str,
    tax_year: date,
    other_savings_base: Decimal,
    general_base: Decimal | None,
    age: int,
    descendant_ages: tuple[int, ...],
    sources: tuple[SourceRef, ...] = (),
    allow_unverified: bool = False,
) -> IncomeTaxProfile:
    """IRPF de la base del ahorro sin la venta, para la cuota incremental de la ganancia.

    El mínimo personal y familiar se aplica primero a la base general (art. 56.2); a la del
    ahorro solo llega lo que sobra. Sin la base general, se supone que la base general lo
    absorbe entero, y se cita como supuesto.
    """
    state_scale = _rule(book, "escala_irpf_ahorro_estatal", "ES", tax_year, False,
                        allow_unverified)
    regional_scale = _rule(book, "escala_irpf_ahorro_autonomica", residence, tax_year, False,
                           allow_unverified)
    state_min, state_refs = _minimum(book, "ES", tax_year, age, descendant_ages,
                                     allow_unverified)
    regional_min, regional_refs = _minimum(book, residence, tax_year, age, descendant_ages,
                                           allow_unverified)
    if general_base is None:
        left_state = left_regional = Decimal(0)
        assumption: tuple[SourceRef, ...] = (
            SourceRef("assumption", "minimo-absorbido-por-la-base-general"),
        )
    else:
        left_state = max(state_min - general_base, Decimal(0))
        left_regional = max(regional_min - general_base, Decimal(0))
        assumption = ()
    return IncomeTaxProfile(
        other_base=other_savings_base,
        state=IrpfPart(_scale(state_scale), left_state),
        regional=IrpfPart(_scale(regional_scale), left_regional),
        sources=combine_sources(
            sources, (state_scale.ref, regional_scale.ref), state_refs, regional_refs,
            assumption,
        ),
    )


@dataclass(frozen=True)
class ResolvedMunicipalGains:
    params: MunicipalGainsTax
    sources: tuple[SourceRef, ...]


def municipal_gains_params(
    book: RuleBook,
    territory: str,
    sale_date: date,
    holding_years: int,
    holding_months: int,
    land_value: Decimal,
    land_share: Decimal,
    value_sources: tuple[SourceRef, ...] = (),
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> ResolvedMunicipalGains:
    """Coeficiente y tipo de la plusvalía municipal para una venta.

    El coeficiente es el del municipio si ha fijado uno propio, nunca mayor que el máximo
    estatal vigente (TRLRHL, art. 107.4). `holding_months` solo cuenta con menos de un año.
    """
    coefficients = _rule(book, "coeficientes_plusvalia", territory, sale_date, include_pending,
                         allow_unverified)
    maximums = _rule(book, "coeficientes_plusvalia", "ES", sale_date, include_pending,
                     allow_unverified)
    coefficient = min(
        _coefficient(coefficients.kind, coefficients.params, holding_years, holding_months),
        _coefficient(maximums.kind, maximums.params, holding_years, holding_months),
    )
    rate_rule = _rule(book, "tipo_plusvalia", territory, sale_date, include_pending,
                      allow_unverified)
    rebate, rebate_refs = tax_rebate(book, "bonificacion_plusvalia", territory, sale_date,
                                     include_pending, allow_unverified)
    return ResolvedMunicipalGains(
        MunicipalGainsTax(land_value, coefficient, _gains_rate(rate_rule, holding_years),
                          land_share, rebate),
        combine_sources(value_sources, (coefficients.ref, maximums.ref, rate_rule.ref),
                        rebate_refs),
    )


def _gains_rate(rule: Rule, years: int) -> Decimal:
    """Tipo del municipio: el único o el del periodo de generación (TRLRHL, art. 108.1)."""
    params = parse_params(rule.kind, rule.params)
    if not isinstance(params, GainsRate):
        raise TypeError(f"{rule.id}: se esperaba el tipo de la plusvalía")
    return params.for_years(years)


def _coefficient(kind: str, raw: dict, years: int, months: int) -> Decimal:
    params = parse_params(kind, raw)
    if not isinstance(params, GainsCoefficients):
        raise TypeError("se esperaban coeficientes de la plusvalía")
    if years < 0 or (years == 0 and not 0 <= months < 12):
        raise ValueError("Periodo de tenencia no válido")
    if years == 0:
        return params.by_years[0] * Decimal(months) / 12
    return params.by_years[min(years, 20)]
