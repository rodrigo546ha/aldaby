"""Parámetros del modelo de valoración resueltos desde el `ParamBook` (ADR-0018)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from housefinder.core.figures import SourceRef
from housefinder.params.book import ParamBook

SHRINKAGE_KIND = "contraccion_renta"


@dataclass(frozen=True)
class Shrinkage:
    k: Decimal  # alquileres equivalentes de la zona
    source: SourceRef


def shrinkage(book: ParamBook, territory: str, on: date) -> Shrinkage:
    param = book.resolve(SHRINKAGE_KIND, territory, on)
    if param is None:
        raise LookupError(f"No hay parámetro de contracción vigente para {territory} el {on}")
    if "k" not in param.params:
        raise ValueError(f"Falta k en {param.id}")
    k = Decimal(str(param.params["k"]))
    if k < 0:
        raise ValueError(f"k no puede ser negativo en {param.id}: {k}")
    return Shrinkage(k, param.ref)
