"""Criterios bancarios de concesión resueltos desde el `ParamBook`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from housefinder.engines.mortgage import BankCriteria
from housefinder.params.book import Param, ParamBook

KIND = "criterios_bancarios"


def bank_criteria(book: ParamBook, territory: str, on: date) -> BankCriteria:
    param = book.resolve(KIND, territory, on)
    if param is None:
        raise LookupError(f"No hay criterios bancarios vigentes para {territory} el {on}")
    return _to_criteria(param)


def _to_criteria(param: Param) -> BankCriteria:
    p = param.params
    max_ltv = _fraction(p, "max_ltv", param.id)
    max_dti = _fraction(p, "max_dti", param.id)
    max_age_at_end = _positive_int(p, "max_age_at_end", param.id)
    max_years = _positive_int(p, "max_years", param.id)
    return BankCriteria(
        max_ltv=max_ltv,
        max_dti=max_dti,
        max_age_at_end=max_age_at_end,
        max_years=max_years,
        source=param.ref,
    )


def _fraction(params: dict[str, Any], key: str, param_id: str) -> Decimal:
    """Tanto por uno en (0, 1]. Vía str para no arrastrar el error binario del float de YAML."""
    value = Decimal(str(_get(params, key, param_id)))
    if not Decimal(0) < value <= Decimal(1):
        raise ValueError(f"{key} fuera de (0, 1] en {param_id}: {value}")
    return value


def _positive_int(params: dict[str, Any], key: str, param_id: str) -> int:
    value = _get(params, key, param_id)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{key} debe ser un entero positivo en {param_id}: {value!r}")
    return value


def _get(params: dict[str, Any], key: str, param_id: str) -> Any:
    if key not in params:
        raise ValueError(f"Falta {key} en {param_id}")
    return params[key]
