"""Formas de cálculo de los gastos y tributos de compra y venta.

Solo las fórmulas: los importes, tipos y límites llegan resueltos por el motor de
normativa (data/rules), nunca escritos aquí.

- Arancel por tramos (notarios y registradores): fijo hasta el primer tramo y cada tipo
  sobre el exceso de su tramo; límites mínimo y máximo; rebaja final.
- Tipo por bandas sobre toda la base (AJD de Madrid): el tipo depende de la banda del valor
  y se aplica al total, con la corrección del salto entre bandas si la norma la prevé.
- Plusvalía municipal: valor del suelo × coeficiente por años de tenencia, o el incremento
  real si es menor; sin incremento real, no hay impuesto.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from housefinder.core.figures import money


@dataclass(frozen=True)
class FeeBand:
    start: Decimal  # valor por encima del cual se aplica `rate`
    rate: Decimal  # tanto por uno sobre el exceso


@dataclass(frozen=True)
class FeeSchedule:
    base_fee: Decimal  # cantidad fija hasta el primer tramo
    bands: tuple[FeeBand, ...]
    min_fee: Decimal | None = None
    max_fee: Decimal | None = None
    max_base: Decimal | None = None  # por encima, el arancel no fija la cantidad
    rebate: Decimal = Decimal(0)


def scheduled_fee(value: Decimal, schedule: FeeSchedule) -> Decimal:
    """Derechos de arancel para un valor, en céntimos.

    Orden: escala, límites mínimo y máximo y, al final, la rebaja.
    """
    if value < 0:
        raise ValueError("El valor no puede ser negativo")
    if schedule.max_base is not None and value > schedule.max_base:
        raise ValueError(
            f"Por encima de {schedule.max_base} € el arancel no fija la cantidad (pacto libre)"
        )
    total = schedule.base_fee
    for band, following in zip(schedule.bands, (*schedule.bands[1:], None), strict=True):
        if value <= band.start:
            break
        top = value if following is None else min(value, following.start)
        total += (top - band.start) * band.rate
    if schedule.min_fee is not None:
        total = max(total, schedule.min_fee)
    if schedule.max_fee is not None:
        total = min(total, schedule.max_fee)
    return money(total * (1 - schedule.rebate))


@dataclass(frozen=True)
class RateBand:
    up_to: Decimal | None  # incluido; None = sin límite (solo la última)
    rate: Decimal


def banded_tax(value: Decimal, bands: tuple[RateBand, ...], cap_jumps: bool) -> Decimal:
    """Cuota con el tipo de la banda del valor aplicado a toda la base.

    Con `cap_jumps`, la cuota no puede superar la del límite de la banda anterior más lo
    que el valor excede de ese límite: así, pasar de banda nunca cuesta más que el euro de
    más (DL 1/2010 de Madrid, art. 37).
    """
    if value <= 0:
        return money(0)
    previous_limit: Decimal | None = None
    previous_tax = Decimal(0)
    for band in bands:
        tax = value * band.rate
        if cap_jumps and previous_limit is not None:
            tax = min(tax, previous_tax + (value - previous_limit))
        if band.up_to is None or value <= band.up_to:
            return money(tax)
        limit_tax = band.up_to * band.rate
        if cap_jumps and previous_limit is not None:
            limit_tax = min(limit_tax, previous_tax + (band.up_to - previous_limit))
        previous_limit, previous_tax = band.up_to, limit_tax
    raise ValueError("La última banda debe no tener límite")


@dataclass(frozen=True)
class MunicipalGainsTax:
    """Datos de la plusvalía municipal de una venta."""

    land_value: Decimal  # valor catastral del suelo en la venta
    coefficient: Decimal  # el del periodo de generación
    rate: Decimal  # tipo de gravamen del municipio
    land_share: Decimal  # valor catastral del suelo / valor catastral total
    rebate: Decimal = Decimal(0)  # bonificación de la cuota (Ceuta y Melilla, ADR-0045)


def municipal_gains_tax(
    params: MunicipalGainsTax, purchase_price: Decimal, sale_price: Decimal
) -> tuple[Decimal, str]:
    """Cuota y método aplicado.

    Base objetiva = valor del suelo × coeficiente. Incremento real = (venta − compra) ×
    proporción del suelo. Si no hay incremento real, no hay impuesto (TRLRHL, art. 104.5);
    si es menor que la base objetiva, se toma como base (art. 107.5), porque el
    contribuyente puede pedirlo.
    """
    real = (sale_price - purchase_price) * params.land_share
    if real <= 0:
        return money(0), "sin incremento real: no sujeta"
    objective = params.land_value * params.coefficient
    rebated = f", menos la bonificación de la cuota ({params.rebate})" if params.rebate else ""
    if real < objective:
        return (money(real * params.rate * (1 - params.rebate)),
                "incremento real (menor que la base objetiva)" + rebated)
    return (money(objective * params.rate * (1 - params.rebate)),
            "base objetiva: valor del suelo × coeficiente" + rebated)
