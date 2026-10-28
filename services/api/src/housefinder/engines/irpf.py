"""Motor del IRPF: cuota por escala con mínimo personal y familiar, y cuota incremental
del alquiler (ADR-0007).

Determinista y sin normativa escrita: escalas e importes de los mínimos llegan como datos
resueltos desde las reglas (`regulation/resolvers.py`).

Cada parte (estatal y autonómica) se calcula como manda la Ley del IRPF (arts. 63.1 y 74.1):
la escala sobre la base liquidable general menos la escala sobre la parte de la base que
corresponde al mínimo personal y familiar (art. 56.2: como mucho, la propia base).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from housefinder.core.figures import SourceRef, money


@dataclass(frozen=True)
class Bracket:
    start: Decimal  # base desde la que se aplica `rate`
    rate: Decimal  # tanto por uno


@dataclass(frozen=True)
class IrpfPart:
    """Una de las dos partes de la cuota: estatal o autonómica."""

    scale: tuple[Bracket, ...]  # primer tramo desde 0, inicios crecientes
    minimum: Decimal  # mínimo personal y familiar de esta parte


@dataclass(frozen=True)
class IncomeTaxProfile:
    """IRPF del contribuyente sin el alquiler: lo necesario para la cuota incremental."""

    other_base: Decimal  # base liquidable general sin el alquiler (dato personal)
    state: IrpfPart
    regional: IrpfPart  # comunidad de residencia del contribuyente
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MinimumAmounts:
    """Importes del mínimo personal y familiar de una parte (arts. 57 y 58, o autonómicos)."""

    general: Decimal
    over_65_extra: Decimal
    over_75_extra: Decimal
    descendants: tuple[Decimal, Decimal, Decimal, Decimal]  # 1.º, 2.º, 3.º, 4.º y siguientes
    under_3_extra: Decimal


def scale_tax(base: Decimal, scale: tuple[Bracket, ...]) -> Decimal:
    """Escala progresiva: cada tipo se aplica a la parte de la base de su tramo. Sin redondeo."""
    if base <= 0:
        return Decimal(0)
    total = Decimal(0)
    for bracket, following in zip(scale, (*scale[1:], None), strict=True):
        if base <= bracket.start:
            break
        top = base if following is None else min(base, following.start)
        total += (top - bracket.start) * bracket.rate
    return total


def part_tax(base: Decimal, part: IrpfPart) -> Decimal:
    """Cuota de una parte, redondeada a céntimos: escala(base) − escala(mínimo, hasta la base)."""
    if base <= 0:
        return money(0)
    return money(scale_tax(base, part.scale) - scale_tax(min(base, part.minimum), part.scale))


def income_tax(base: Decimal, profile: IncomeTaxProfile) -> Decimal:
    """Cuota estatal + autonómica para una base liquidable general."""
    return part_tax(base, profile.state) + part_tax(base, profile.regional)


def incremental_tax(rental_net: Decimal, profile: IncomeTaxProfile) -> Decimal:
    """IRPF atribuible al alquiler: cuota con el rendimiento − cuota sin él.

    `rental_net` es el rendimiento neto ya reducido; si es negativo, baja la base y la
    cuota incremental sale negativa (ahorro fiscal). La base no baja de cero: compensar
    una base negativa en años siguientes queda fuera de este cálculo.
    """
    with_rental = max(profile.other_base + rental_net, Decimal(0))
    return income_tax(with_rental, profile) - income_tax(profile.other_base, profile)


def personal_minimum(
    amounts: MinimumAmounts, age: int, descendant_ages: tuple[int, ...]
) -> Decimal:
    """Mínimo del contribuyente y por descendientes.

    `descendant_ages`: solo los descendientes que dan derecho al mínimo (art. 58.1), en el
    orden en que se cuentan (primero, segundo…). Los aumentos por edad exigen «edad
    superior a» 65 y 75 años.
    """
    total = amounts.general
    if age > 65:
        total += amounts.over_65_extra
    if age > 75:
        total += amounts.over_75_extra
    for i, child_age in enumerate(descendant_ages):
        total += amounts.descendants[min(i, 3)]
        if child_age < 3:
            total += amounts.under_3_extra
    return total
