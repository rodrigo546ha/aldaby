"""Trazabilidad de cifras (ADR-0001 y ADR-0004).

Regla de oro del proyecto: toda cifra que llega al usuario es un `Figure`,
con su fórmula y sus fuentes. El LLM nunca produce cifras: solo las explica.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

CENT = Decimal("0.01")
RATIO_PLACES = Decimal("0.0001")  # una centésima de punto porcentual

SourceKind = Literal["rule", "param", "dataset", "model", "user_input", "assumption"]


def money(value: Decimal | int | float | str) -> Decimal:
    """Redondea a céntimos con redondeo comercial."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def ratio(value: Decimal | int | str) -> Decimal:
    """Redondea una proporción en tanto por uno a cuatro decimales (0.0720 = 7,20 %)."""
    return Decimal(str(value)).quantize(RATIO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class SourceRef:
    """De dónde sale un dato: regla, parámetro, conjunto de datos, modelo, usuario o supuesto."""

    kind: SourceKind
    id: str
    provisional: bool = False  # parámetro PROVISIONAL, regla sin verificar o supuesto por fijar

    def to_dict(self) -> dict:
        return {"kind": self.kind, "id": self.id, "provisional": self.provisional}


def combine_sources(*groups: Iterable[SourceRef]) -> tuple[SourceRef, ...]:
    """Une las fuentes de varias entradas, sin duplicados y en orden de aparición."""
    return tuple(dict.fromkeys(ref for group in groups for ref in group))


@dataclass(frozen=True)
class Figure:
    """Una cifra con procedencia verificable."""

    key: str  # estable, "dominio.nombre": "cashflow.monthly_after_tax"
    value: Decimal
    unit: str  # "EUR", "EUR/mes", "EUR/año", "ratio", "años"
    formula: str  # descripción legible del cálculo
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)
    as_of: date | None = None
    low: Decimal | None = None  # rango (P25) de las estimaciones estadísticas
    high: Decimal | None = None  # rango (P75)

    def __post_init__(self) -> None:
        if "." not in self.key:
            raise ValueError(f"La clave de una cifra debe tener dominio: {self.key!r}")
        if (self.low is None) != (self.high is None):
            raise ValueError(f"Rango incompleto en {self.key}: low y high van juntos")
        if self.low is not None and self.high is not None:
            if not self.low <= self.value <= self.high:
                raise ValueError(f"El rango de {self.key} no contiene su valor")

    @property
    def provisional(self) -> bool:
        return any(ref.provisional for ref in self.sources)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": str(self.value),
            "unit": self.unit,
            "formula": self.formula,
            "sources": [ref.to_dict() for ref in self.sources],
            "provisional": self.provisional,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "low": str(self.low) if self.low is not None else None,
            "high": str(self.high) if self.high is not None else None,
        }
