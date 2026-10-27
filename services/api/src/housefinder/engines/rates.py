"""Trayectoria de tipos y condiciones de una hipoteca fija, variable o mixta.

Los meses se cuentan desde la firma del préstamo (mes 0 = primer mes). La trayectoria
del índice (Euríbor) llega como dato con sus fuentes: hasta fijar la serie pública de
F1.7 es un supuesto de quien llama, nunca una previsión de este motor.

Sin suelo de tipo: si índice + diferencial sale negativo se usa tal cual. Un límite
legal llegaría como regla de normativa (F2), no como constante aquí.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from housefinder.core.figures import SourceRef, combine_sources

LABEL = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class RatePath:
    """Valor del índice por tramos: (mes desde la firma, valor desde ese mes)."""

    steps: tuple[tuple[int, Decimal], ...]
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.steps or self.steps[0][0] != 0:
            raise ValueError("La trayectoria debe empezar en el mes 0")
        months = [month for month, _ in self.steps]
        if any(a >= b for a, b in zip(months, months[1:], strict=False)):
            raise ValueError("Los meses de la trayectoria deben ser estrictamente crecientes")

    @classmethod
    def flat(cls, value: Decimal, sources: tuple[SourceRef, ...] = ()) -> RatePath:
        return cls(((0, value),), sources)

    def value_at(self, month: int) -> Decimal:
        current = self.steps[0][1]
        for start, value in self.steps:
            if start > month:
                break
            current = value
        return current

    def shifted(self, shock: Decimal, source: SourceRef) -> RatePath:
        """La misma trayectoria con `shock` sumado en todos los tramos (escenario de estrés)."""
        return RatePath(
            tuple((month, value + shock) for month, value in self.steps),
            combine_sources(self.sources, (source,)),
        )


@dataclass(frozen=True)
class MortgageTerms:
    """Condiciones de tipo de una oferta hipotecaria.

    - Fija: tramo inicial que cubre todo el plazo (`fixed`).
    - Variable: tramo inicial corto (6–12 meses), después índice + diferencial.
    - Mixta: tramo inicial de años, después índice + diferencial.
    """

    label: str  # identificador corto: "fija-banco-a"; forma parte de las claves de Figure
    initial_rate: Decimal  # tipo anual del tramo inicial
    initial_months: int  # meses a tipo inicial
    spread: Decimal = Decimal(0)  # diferencial sobre el índice tras el tramo inicial
    revision_months: int = 12  # cada cuántos meses se revisa el tipo
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not LABEL.match(self.label):
            raise ValueError(f"Etiqueta no válida (minúsculas, cifras y guiones): {self.label!r}")
        if self.initial_months < 0:
            raise ValueError("El tramo inicial no puede ser negativo")
        if self.revision_months <= 0:
            raise ValueError("El periodo de revisión debe ser positivo")

    @classmethod
    def fixed(
        cls, label: str, rate: Decimal, sources: tuple[SourceRef, ...] = ()
    ) -> MortgageTerms:
        # Un tramo inicial sin fin práctico: ningún plazo hipotecario llega a 1.200 años.
        return cls(label, rate, 10**6, sources=sources)

    def is_indexed_within(self, total_months: int) -> bool:
        return self.initial_months < total_months


@dataclass(frozen=True)
class RateSegment:
    start_month: int  # desde la firma; el tramo aplica a partir de este mes
    annual_rate: Decimal


def rate_segments(
    terms: MortgageTerms, path: RatePath, total_months: int
) -> tuple[RateSegment, ...]:
    """Tramos de tipo a lo largo del plazo: inicial y una revisión cada `revision_months`."""
    segments = [RateSegment(0, terms.initial_rate)]
    for start in range(terms.initial_months, total_months, terms.revision_months):
        if start == 0:
            segments[0] = RateSegment(0, path.value_at(0) + terms.spread)
        else:
            segments.append(RateSegment(start, path.value_at(start) + terms.spread))
    return tuple(segments)
