"""Trazabilidad de cifras.

Regla de oro del proyecto: toda cifra que llega al usuario es un `Figure`,
con su fórmula y sus fuentes. El LLM nunca produce cifras: solo las explica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    """Redondea a céntimos con redondeo comercial."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Figure:
    """Una cifra con procedencia verificable."""

    value: Decimal
    unit: str  # "EUR", "EUR/mes", "%", "años"...
    formula: str  # descripción legible del cálculo
    sources: tuple[str, ...] = field(default_factory=tuple)  # ids de fuente o de regla
    as_of: date | None = None

    def to_dict(self) -> dict:
        return {
            "value": str(self.value),
            "unit": self.unit,
            "formula": self.formula,
            "sources": list(self.sources),
            "as_of": self.as_of.isoformat() if self.as_of else None,
        }
