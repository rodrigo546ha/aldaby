"""Resolutores de normativa: de las reglas vigentes a entradas de los motores (F2.7).

Cada resolutor elige la regla aplicable con el `RuleBook` y devuelve cifras o parámetros
que citan esa regla. Una regla sin verificar solo se usa con `allow_unverified=True`, y
su cita sale provisional, así que toda cifra que dependa de ella también.

Fechas: el impuesto de compra se resuelve en la fecha de compra, el IBI en el año del
devengo y las reducciones del IRPF en la fecha de celebración del contrato de alquiler.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from housefinder.core.figures import Figure, SourceRef, combine_sources, money
from housefinder.engines.cashflow import TaxParams
from housefinder.regulation.kinds import RateParams, ReductionCases, parse_params
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


def tax_params(
    book: RuleBook,
    territory: str,
    contract_date: date,
    reduction_case: str,
    marginal_rate: Decimal,
    marginal_rate_sources: tuple[SourceRef, ...] = (),
    include_pending: bool = False,
    allow_unverified: bool = False,
) -> TaxParams:
    """Parámetros fiscales del alquiler para el motor de cash flow.

    `reduction_case`: supuesto de la reducción del art. 23.2 de la Ley del IRPF (una
    `condition` de la regla aplicable, p. ej. «general» o «primer-alquiler-zona-tensionada»).
    `marginal_rate` llega del usuario mientras no se calcule la cuota incremental (D-G2-1).
    """
    reduction_rule = _rule(book, "reduccion_irpf_alquiler", territory, contract_date,
                           include_pending, allow_unverified)
    depreciation_rule = _rule(book, "amortizacion_inmueble_alquiler", territory,
                              contract_date, include_pending, allow_unverified)
    cases = parse_params(reduction_rule.kind, reduction_rule.params)
    if not isinstance(cases, ReductionCases):
        raise TypeError(f"{reduction_rule.id}: se esperaba una reducción por casos")
    try:
        reduction = cases.case(reduction_case).reduction
    except KeyError:
        available = ", ".join(c.condition for c in cases.cases)
        raise ValueError(
            f"La regla {reduction_rule.id} no tiene el caso {reduction_case!r}. "
            f"Casos: {available}"
        ) from None
    return TaxParams(
        marginal_rate=marginal_rate,
        rental_income_reduction=reduction,
        depreciation_rate=_rate(depreciation_rule),
        sources=(reduction_rule.ref, depreciation_rule.ref, *marginal_rate_sources),
    )


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
