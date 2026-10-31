"""Renta y precio estimados desde referencias públicas (F5.3, F5.4, ADR-0018).

Funciones puras: reciben estadísticos ya leídos (mediana y P25–P75 del SERPAVI, valor tasado,
índice de precios) y devuelven valores con su rango. El servicio de `valuation/` lee los datos y
convierte el resultado en `Figure` con sus fuentes.

- Contracción: con pocos alquileres, la sección se acerca a la zona que la contiene,
  w = n / (n + k), estadístico = w·sección + (1 − w)·zona.
- Precio desde la renta: €/m² = renta €/m² mes × 12 × (valor tasado / (renta municipal × 12)) del
  municipio. Supone la misma rentabilidad bruta en todo el municipio.
- Oferta: lo pedido frente a lo estimado (pedido / estimado − 1, con el rango de la estimación) y
  rentabilidad bruta al precio pedido (renta anual / precio).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from housefinder.core.figures import CENT, money, ratio

TWELVE = Decimal(12)
FOUR = Decimal("0.0001")


@dataclass(frozen=True)
class RentStats:
    """Renta €/m² al mes de un territorio y un año: recuento, P25, mediana y P75."""

    n: int | None
    p25: Decimal
    median: Decimal
    p75: Decimal


@dataclass(frozen=True)
class Shrunk:
    p25: Decimal
    median: Decimal
    p75: Decimal
    weight: Decimal  # peso de la sección: 1 sin contracción


@dataclass(frozen=True)
class Range:
    low: Decimal
    value: Decimal
    high: Decimal


def shrink(local: RentStats, parent: RentStats, k: Decimal) -> Shrunk:
    """Contrae `local` hacia `parent` con peso n / (n + k)."""
    if local.n is None or k <= 0:
        weight = Decimal(1)
    else:
        weight = Decimal(local.n) / (Decimal(local.n) + k)

    def blend(own: Decimal, zone: Decimal) -> Decimal:
        return (weight * own + (1 - weight) * zone).quantize(CENT)

    return Shrunk(blend(local.p25, parent.p25), blend(local.median, parent.median),
                  blend(local.p75, parent.p75), weight)


def rent_for_area(per_m2: Shrunk, area_m2: Decimal) -> Range:
    """Renta mensual del inmueble: €/m² mes × superficie."""
    return Range(money(per_m2.p25 * area_m2), money(per_m2.median * area_m2),
                 money(per_m2.p75 * area_m2))


def price_to_rent_ratio(appraisal_m2: Decimal, rent_m2_month: Decimal) -> Decimal:
    """Años de renta que vale un m²: valor tasado / renta anual por m²."""
    if rent_m2_month <= 0:
        raise ValueError("La renta municipal tiene que ser positiva")
    return (appraisal_m2 / (rent_m2_month * TWELVE)).quantize(FOUR)


def price_per_m2(rent: Shrunk, ratio: Decimal) -> Range:
    """€/m² de venta desde la renta €/m² mes y la relación precio/renta del municipio."""
    return Range(money(rent.p25 * TWELVE * ratio), money(rent.median * TWELVE * ratio),
                 money(rent.p75 * TWELVE * ratio))


def index_update(value: Decimal, index_from: Decimal, index_to: Decimal) -> Decimal:
    """Lleva un valor del periodo del índice `index_from` al de `index_to`."""
    if index_from <= 0:
        raise ValueError("El índice de partida tiene que ser positivo")
    return money(value * index_to / index_from)


def scale(per_m2: Shrunk, index_from: Decimal, index_to: Decimal) -> Shrunk:
    """Lleva la renta €/m² (P25, mediana y P75) de un periodo a otro con un índice."""
    return Shrunk(index_update(per_m2.p25, index_from, index_to),
                  index_update(per_m2.median, index_from, index_to),
                  index_update(per_m2.p75, index_from, index_to), per_m2.weight)


def asking_gap(asked: Decimal, estimate: Range) -> Range:
    """Cuánto se aparta lo pedido de lo estimado: pedido / estimado − 1.

    El rango sale de comparar con el P75 (el extremo bajo) y con el P25 (el alto)."""
    if estimate.low <= 0:
        raise ValueError("La estimación tiene que ser positiva")
    return Range(ratio(asked / estimate.high - 1), ratio(asked / estimate.value - 1),
                 ratio(asked / estimate.low - 1))


def gross_yield(rent_monthly: Range, price: Decimal) -> Range:
    """Rentabilidad bruta a un precio: renta anual / precio, con el rango de la renta."""
    if price <= 0:
        raise ValueError("El precio tiene que ser positivo")
    return Range(ratio(rent_monthly.low * TWELVE / price),
                 ratio(rent_monthly.value * TWELVE / price),
                 ratio(rent_monthly.high * TWELVE / price))
