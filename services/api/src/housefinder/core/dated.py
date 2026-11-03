"""Lector común de registros con fecha: reglas de normativa y parámetros (ADR-0005).

Territorio: código jerárquico tipo "ES", "ES-13" (comunidad), "ES-13-28079" (municipio,
código INE). Gana el registro aplicable más específico y, a igualdad, el de inicio de
vigencia más reciente.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any, Protocol, TypeVar

import yaml


class DatedRecord(Protocol):
    @property
    def territory(self) -> str: ...

    @property
    def effective_from(self) -> date: ...


R = TypeVar("R", bound=DatedRecord)

# El lector seguro en C (libyaml) lee lo mismo que yaml.safe_load, unas diez veces más deprisa:
# las reglas generadas de Hacienda son miles (ADR-0044)
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def load_yaml_records(path: Path) -> list[dict[str, Any]]:
    """Todos los registros de los `*.yaml` de una carpeta, en orden de fichero."""
    records: list[dict[str, Any]] = []
    for file in sorted(path.glob("*.yaml")):
        records.extend(yaml.load(file.read_text(encoding="utf-8"), Loader=_LOADER) or [])
    return records


def require_keys(raw: dict[str, Any], keys: Iterable[str]) -> None:
    for key in keys:
        if key not in raw:
            raise ValueError(f"Falta '{key}' en un registro: {raw}")


def to_date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def optional_date(value: Any) -> date | None:
    return to_date(value) if value else None


def applies_on(effective_from: date, effective_to: date | None, on: date) -> bool:
    return effective_from <= on and (effective_to is None or on < effective_to)


def territory_contains(record_territory: str, target: str) -> bool:
    return target == record_territory or target.startswith(record_territory + "-")


def most_specific(candidates: Iterable[R]) -> R | None:
    """Más específico primero; a igualdad, el de inicio de vigencia más reciente."""
    ordered = sorted(
        candidates, key=lambda r: (r.territory.count("-"), r.effective_from), reverse=True
    )
    return ordered[0] if ordered else None
