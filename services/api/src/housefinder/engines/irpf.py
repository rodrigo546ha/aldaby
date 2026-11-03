"""Motor del IRPF: cuota por escala con mínimo personal y familiar, y cuota incremental
del alquiler (ADR-0007).

Determinista y sin normativa escrita: escalas e importes de los mínimos llegan como datos
resueltos desde las reglas (`regulation/resolvers.py`).

Cada parte (estatal y autonómica) se calcula como manda la Ley del IRPF (arts. 63.1 y 74.1):
la escala sobre la base liquidable general menos la escala sobre la parte de la base que
corresponde al mínimo personal y familiar (art. 56.2: como mucho, la propia base).

Los IRPF forales (Navarra y los territorios históricos vascos, ADR-0046) tienen una sola escala
y restan los mínimos de la cuota, en euros, algunos menores cuanto mayor es la base: es una sola
parte con `quota_reduction` y `tapered`, y la otra a cero (`ZERO_PART`).
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
class TaperedDeduction:
    """Deducción en la cuota que depende de la base: tramos lineales entre puntos (base, importe).

    Por debajo del primer punto, su importe; por encima del último, el suyo.
    """

    points: tuple[tuple[Decimal, Decimal], ...]  # bases crecientes

    def amount(self, base: Decimal) -> Decimal:
        (first_base, first), *_ = self.points
        if base <= first_base:
            return first
        for (b0, a0), (b1, a1) in zip(self.points, self.points[1:], strict=False):
            if base <= b1:
                return a0 + (a1 - a0) * (base - b0) / (b1 - b0)
        return self.points[-1][1]


@dataclass(frozen=True)
class IrpfPart:
    """Una de las dos partes de la cuota: estatal o autonómica (o la foral, que es única)."""

    scale: tuple[Bracket, ...]  # primer tramo desde 0, inicios crecientes
    minimum: Decimal  # mínimo personal y familiar de esta parte
    quota_reduction: Decimal = Decimal(0)  # deducciones fijas en la cuota (forales)
    tapered: tuple[TaperedDeduction, ...] = ()  # deducciones en la cuota que dependen de la base


ZERO_PART = IrpfPart((Bracket(Decimal(0), Decimal(0)),), Decimal(0))  # la otra parte foral


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
    """Cuota de una parte, redondeada a céntimos: escala(base) − escala(mínimo, hasta la base),
    menos las deducciones en la cuota, sin bajar de cero."""
    if base <= 0:
        return money(0)
    tax = scale_tax(base, part.scale) - scale_tax(min(base, part.minimum), part.scale)
    deductions = part.quota_reduction + sum((t.amount(base) for t in part.tapered), Decimal(0))
    return money(max(tax - deductions, Decimal(0)))


def income_tax(base: Decimal, profile: IncomeTaxProfile) -> Decimal:
    """Cuota estatal + autonómica para una base liquidable general."""
    return part_tax(base, profile.state) + part_tax(base, profile.regional)


def incremental_tax(
    rental_net: Decimal, profile: IncomeTaxProfile, territorial_deduction: Decimal = Decimal(0)
) -> Decimal:
    """IRPF atribuible al alquiler: cuota con el rendimiento − cuota sin él.

    `rental_net` es el rendimiento neto ya reducido; si es negativo, baja la base y la
    cuota incremental sale negativa (ahorro fiscal). La base no baja de cero: compensar
    una base negativa en años siguientes queda fuera de este cálculo.

    `territorial_deduction`: parte que se deduce de la cuota que proporcionalmente corresponde a
    esta renta (Ley del IRPF, art. 68.4: el 60 % en Ceuta y Melilla). La proporción es la de la
    renta en la base; el resto de la base se supone obtenida fuera de esas ciudades (ADR-0045).
    """
    with_rental = max(profile.other_base + rental_net, Decimal(0))
    tax_with = income_tax(with_rental, profile)
    result = tax_with - income_tax(profile.other_base, profile)
    if territorial_deduction and rental_net > 0 and with_rental > 0:
        result -= money(tax_with * rental_net / with_rental * territorial_deduction)
    return result


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


@dataclass(frozen=True)
class ForalAmounts:
    """Deducciones personales y familiares en la cuota de un IRPF foral (ADR-0046)."""

    general: Decimal  # mínimo personal o minoración de cuota
    general_by_income: tuple[tuple[Decimal, Decimal], ...] = ()  # (base, importe), decreciente
    age: tuple[tuple[int, Decimal], ...] = ()  # (edad mínima, importe): el de mayor edad cumplida
    age_phaseout: tuple[Decimal, Decimal] | None = None  # base desde la que baja y en la que es 0
    descendants: tuple[Decimal, ...] = (Decimal(0),)  # 1.º, 2.º…; el último sirve para los demás
    young_children: tuple[tuple[int, Decimal], ...] = ()  # (menor de esta edad, importe)


def foral_deductions(
    amounts: ForalAmounts, age: int, descendant_ages: tuple[int, ...]
) -> tuple[Decimal, tuple[TaperedDeduction, ...]]:
    """Deducciones fijas y las que dependen de la base, para la edad y los descendientes.

    `descendant_ages`: solo los que dan derecho a la deducción, en orden. Por cada niño cuenta
    el primer complemento por edad que cumpla (de menor a mayor edad límite).
    """
    fixed = amounts.general
    tapered: list[TaperedDeduction] = []
    if amounts.general_by_income:
        tapered.append(TaperedDeduction(amounts.general_by_income))
    by_age = max((a for min_age, a in amounts.age if age >= min_age), default=Decimal(0))
    if by_age and amounts.age_phaseout is not None:
        start, end = amounts.age_phaseout
        tapered.append(TaperedDeduction(((start, by_age), (end, Decimal(0)))))
    else:
        fixed += by_age
    extras = sorted(amounts.young_children)
    for i, child_age in enumerate(descendant_ages):
        fixed += amounts.descendants[min(i, len(amounts.descendants) - 1)]
        fixed += next((a for limit, a in extras if child_age < limit), Decimal(0))
    return fixed, tuple(tapered)

