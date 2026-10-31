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


CONVERGENCE_KIND = "convergencia_municipal"


@dataclass(frozen=True)
class Convergence:
    step_years: int
    b_base: Decimal
    b_low: Decimal  # percentil 25 de los periodos
    b_high: Decimal  # percentil 75
    source: SourceRef


def convergence(book: ParamBook, territory: str, on: date) -> Convergence:
    param = book.resolve(CONVERGENCE_KIND, territory, on)
    if param is None:
        raise LookupError(f"No hay parámetro de convergencia vigente para {territory} el {on}")
    p = param.params
    missing = [k for k in ("step_years", "b_base", "b_low", "b_high") if k not in p]
    if missing:
        raise ValueError(f"Faltan {', '.join(missing)} en {param.id}")
    low, high = Decimal(str(p["b_low"])), Decimal(str(p["b_high"]))
    if low > high:
        raise ValueError(f"b_low mayor que b_high en {param.id}")
    return Convergence(int(p["step_years"]), Decimal(str(p["b_base"])), low, high, param.ref)
