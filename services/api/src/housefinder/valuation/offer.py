"""Valoración de una oferta confirmada (F5.4, ADR-0018): renta, precio y escenarios del inmueble,
y lo que pide el anuncio frente a lo estimado.

- Solo viviendas ubicadas y con superficie construida: el SERPAVI y el valor tasado son de
  vivienda. Sin tipología en el anuncio, se valora como piso salvo que se indique otra cosa.
- Venta: precio pedido frente al precio estimado (con el rango P25–P75) y rentabilidad bruta al
  precio pedido. Alquiler: renta pedida frente a la renta estimada.
- No es un margen de negociación: el descuento habitual sobre el precio pedido no tiene fuente
  pública. Es la distancia entre el anuncio y las referencias públicas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from housefinder.core.figures import Figure, SourceRef, combine_sources
from housefinder.db.connection import Connection
from housefinder.db.offers import PrivateOffer
from housefinder.engines.valuation import Range, asking_gap, gross_yield
from housefinder.params.book import ParamBook
from housefinder.valuation.scenarios import NoScenarios, appreciation_scenarios
from housefinder.valuation.service import ValuationReport, value_property

ASKED = SourceRef("user_input", "anuncio-confirmado")
OPERATION_NAMES = {"venta": "precio pedido", "alquiler": "renta pedida"}


class CannotValue(ValueError):
    """A la oferta le falta algo para valorarla: confirmación, ubicación, superficie o tipo."""


@dataclass(frozen=True)
class OfferValuation:
    report: ValuationReport
    figures: list[Figure]  # las del inmueble, los escenarios y la comparación con el anuncio
    notes: list[str] = field(default_factory=list)


def value_offer(
    conn: Connection, book: ParamBook, offer: PrivateOffer, horizon_years: int = 10,
    typology: str = "colectiva", new_build: bool = False, on: date | None = None,
) -> OfferValuation:
    if offer.extraction_status != "confirmada":
        raise CannotValue("Confirma primero los datos del anuncio")
    extracted = offer.extracted or {}
    property_type = (extracted.get("listing") or {}).get("property_type")
    if property_type not in (None, "vivienda"):
        raise CannotValue(f"Solo se valoran viviendas: el anuncio es de tipo {property_type}")
    if offer.lon is None or offer.lat is None:
        raise CannotValue("La oferta no está ubicada: confirma la dirección o la referencia "
                          "catastral")
    if offer.built_area_m2 is None:
        raise CannotValue("Falta la superficie construida")

    report = value_property(conn, book, offer.lon, offer.lat, offer.built_area_m2, typology,
                            new_build, on)
    figures, notes = list(report.figures), list(report.notes)
    if property_type is None:
        notes.append("El anuncio no dice el tipo de inmueble: se valora como vivienda.")
    try:
        scenarios = appreciation_scenarios(conn, book, report.section_code[:5], horizon_years,
                                           new_build, on)
        figures += scenarios.figures
        notes += scenarios.notes
    except NoScenarios as exc:
        notes.append(f"Sin escenarios de revalorización: {exc}")

    confirmed = extracted.get("confirmed") or {}
    operation = confirmed.get("operation")
    asked = _number(((confirmed.get("fields") or {}).get("price") or {}).get("value"))
    by_key = {f.key: f for f in figures}
    if operation in OPERATION_NAMES and asked:
        figures.append(Figure(
            key="offer.asking_price", value=asked,
            unit="EUR" if operation == "venta" else "EUR/mes", sources=(ASKED,),
            formula=f"{OPERATION_NAMES[operation].capitalize()} en el anuncio, confirmado por ti"))
    if operation == "venta" and asked and "valuation.price_total" in by_key:
        figures += _sale(asked, by_key["valuation.price_total"],
                         by_key["valuation.rent_monthly"], notes)
    elif operation == "alquiler" and asked:
        figures += _rent(asked, by_key["valuation.rent_monthly"], notes)
    elif operation in OPERATION_NAMES and asked:
        notes.append("Sin precio estimado: no se puede comparar con el precio pedido.")
    else:
        notes.append("Sin operación o precio confirmados: no se compara con el anuncio.")
    notes.append("La diferencia con el anuncio no es un margen de negociación: el descuento "
                 "habitual sobre el precio pedido no tiene fuente pública.")
    return OfferValuation(report, figures, notes)


def _sale(asked: Decimal, price: Figure, rent: Figure, notes: list[str]) -> list[Figure]:
    estimate = _range(price)
    gap = asking_gap(asked, estimate)
    notes.append(_position("precio pedido", asked, estimate))
    gross = gross_yield(_range(rent), asked)
    return [
        Figure(
            key="offer.asking_gap", value=gap.value, unit="ratio", low=gap.low, high=gap.high,
            as_of=price.as_of, sources=combine_sources((ASKED,), price.sources),
            formula=(f"Precio pedido {_eur(asked)} / precio estimado {_eur(estimate.value)} − 1;"
                     f" rango frente al P75 ({_eur(estimate.high)}) y al P25 "
                     f"({_eur(estimate.low)})"),
        ),
        Figure(
            key="offer.gross_yield_at_asking", value=gross.value, unit="ratio", low=gross.low,
            high=gross.high, as_of=rent.as_of, sources=combine_sources((ASKED,), rent.sources),
            formula=(f"Renta estimada {_eur(rent.value)} al mes × 12 / precio pedido "
                     f"{_eur(asked)}; rango con la renta P25–P75"),
        ),
    ]


def _rent(asked: Decimal, rent: Figure, notes: list[str]) -> list[Figure]:
    estimate = _range(rent)
    gap = asking_gap(asked, estimate)
    notes.append(_position("renta pedida", asked, estimate))
    return [Figure(
        key="offer.asking_rent_gap", value=gap.value, unit="ratio", low=gap.low, high=gap.high,
        as_of=rent.as_of, sources=combine_sources((ASKED,), rent.sources),
        formula=(f"Renta pedida {_eur(asked)} al mes / renta estimada {_eur(estimate.value)} − 1;"
                 f" rango frente al P75 ({_eur(estimate.high)}) y al P25 ({_eur(estimate.low)})"),
    )]


def _position(what: str, asked: Decimal, estimate: Range) -> str:
    if asked < estimate.low:
        return (f"El {what} está por debajo del rango estimado (P25 {_eur(estimate.low)}): "
                "comprueba la superficie y el estado antes de darlo por una oportunidad.")
    if asked > estimate.high:
        return f"El {what} está por encima del rango estimado (P75 {_eur(estimate.high)})."
    return (f"El {what} está dentro del rango estimado ({_eur(estimate.low)} – "
            f"{_eur(estimate.high)}).")


def _range(figure: Figure) -> Range:
    if figure.low is None or figure.high is None:
        raise ValueError(f"{figure.key} no tiene rango")
    return Range(figure.low, figure.value, figure.high)


def _number(value: str | None) -> Decimal | None:
    try:
        return Decimal(value) if value else None
    except InvalidOperation:
        return None


def _eur(value: Decimal) -> str:
    """189500.00 → «189.500 €»; 1452.50 → «1.452,50 €»."""
    places = 0 if value == value.to_integral_value() else 2
    text = f"{value:,.{places}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{text} €"
