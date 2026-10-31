"""Qué significa cada cifra, para el modelo (ADR-0019).

El modelo solo veía la clave (`valuation.price_m2`) y una fórmula sin números: llamaba «valor
tasado» al precio estimado, leía mal el signo de una diferencia o tomaba una tasa anual por un
total. Cada descripción dice qué es la cifra y cómo se lee, sin números (ADR-0012).
"""

from __future__ import annotations

from collections.abc import Sequence

from housefinder.core.figures import Figure
from housefinder.territory.figures import ABSOLUTE_CHANGE_UNITS, LABELS

GAP_SIGN = ("Negativa: el anuncio pide menos que lo estimado; positiva: pide más. La cifra ya "
            "lleva el signo: no le añadas «por debajo» ni «por encima».")
SCENARIO = ("Revalorización media por año del precio de la vivienda en el escenario {name}, "
            "durante el horizonte de la valoración. Es una tasa anual, no la subida total.")
DESCRIPTIONS = {
    "valuation.rent_monthly": "Renta mensual estimada del inmueble: renta por metro cuadrado de "
                              "la zona por su superficie. El rango va del cuartil bajo al alto.",
    "valuation.rent_m2_month": "Renta mensual estimada por metro cuadrado en la zona del inmueble.",
    "valuation.price_total": "Precio de compraventa estimado del inmueble, calculado desde la "
                             "renta con la relación entre precio y renta del municipio. No es "
                             "una tasación.",
    "valuation.price_m2": "Precio estimado del inmueble por metro cuadrado, calculado desde la "
                          "renta. No es el valor tasado.",
    "valuation.price_rent_ratio": "Cuántos años de renta vale una vivienda en el municipio: valor "
                                  "tasado del municipio entre su renta anual. Es del municipio, "
                                  "no del inmueble.",
    "valuation.appreciation_conservative": SCENARIO.format(name="conservador"),
    "valuation.appreciation_base": SCENARIO.format(name="base"),
    "valuation.appreciation_optimistic": SCENARIO.format(name="optimista"),
    "offer.asking_price": "Lo que pide el anuncio (precio de venta o renta mensual), confirmado "
                          "por el usuario.",
    "offer.asking_gap": "Diferencia entre el precio que pide el anuncio y el estimado, en "
                        "proporción. " + GAP_SIGN + " No es un margen de negociación.",
    "offer.asking_rent_gap": "Diferencia entre la renta que pide el anuncio y la estimada, en "
                             "proporción. " + GAP_SIGN,
    "offer.gross_yield_at_asking": "Rentabilidad bruta si se compra al precio pedido: renta "
                                   "estimada de un año entre el precio pedido, sin gastos ni "
                                   "impuestos.",
    # Búsqueda inversa (F6.5, ADR-0023)
    "offer.price": "Precio de la oferta: lo que pide el anuncio o, en una subasta del BOE, el "
                   "tipo de salida (el precio final puede ser otro).",
    "cashflow.monthly_after_tax": "Lo que le queda al usuario cada mes con este inmueble, tras "
                                  "la hipoteca, los gastos y el IRPF del alquiler.",
    "search.stressed_cashflow": "El cash flow mensual si suben los tipos (con riesgo bajo, "
                                "además con la renta baja de la zona).",
    "irr.rate": "Rentabilidad anual de la inversión del usuario hasta su horizonte, con la venta "
                "y el escenario base de revalorización.",
    "cashflow.cash_invested": "Dinero que pone el usuario: entrada, gastos de compra y reforma.",
    "assumption.mortgage_rate": "Tipo de mercado de una hipoteca fija nueva (Banco de España); no "
                                "es el que le darían al usuario.",
    "assumption.rate_shock": "Subida de tipos del escenario de estrés: la mayor de la serie en "
                             "una ventana de dos años.",
}
# Las etiquetas del INE que llevan números, dichas sin ellos
SPOKEN_LABELS = {"poblacion_menor_18": "Porcentaje de población menor de edad",
                 "poblacion_65_y_mas": "Porcentaje de población de edad avanzada"}
ZONE = "en la sección censal de la oferta, según el Atlas de renta del INE"


def describe(figures: Sequence[Figure]) -> dict[str, str]:
    """Clave del Figure → descripción, para las cifras que la tienen."""
    units = {f.key: f.unit for f in figures}
    result = {}
    for figure in figures:
        text = DESCRIPTIONS.get(figure.key) or _territory(figure.key, units)
        if text:
            result[figure.key] = text
    return result


def _territory(key: str, units: dict[str, str]) -> str | None:
    parts = key.split(".")
    if parts[0] != "territory" or len(parts) not in (2, 3) or parts[1] not in LABELS:
        return None
    label = SPOKEN_LABELS.get(parts[1], LABELS[parts[1]])
    if len(parts) == 2:
        return f"{label} {ZONE}."
    unit = units.get(f"territory.{parts[1]}")
    if unit == "años":
        how = "en años: la diferencia entre el valor de ahora y el de entonces"
    elif unit in ABSOLUTE_CHANGE_UNITS:
        how = ("en puntos: la diferencia entre el porcentaje de ahora y el de entonces, no un "
               "porcentaje de cambio")
    else:
        how = "relativa: cuánto ha crecido o bajado en proporción"
    return f"Variación en el último lustro, {how}. Indicador: {label.lower()} {ZONE}."
