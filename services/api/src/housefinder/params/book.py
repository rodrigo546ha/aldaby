"""Parámetros con fecha como DATOS: criterios bancarios, trayectoria de tipos (ADR-0005).

No son normativa: no tienen fuente oficial que verificar, sino una fuente documentada
(un banco, un intermediario, una serie publicada). Mientras no la tengan van marcados
`provisional: true`, y toda cifra que los use sale provisional (ADR-0004).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from housefinder.core.dated import (
    applies_on,
    load_yaml_records,
    most_specific,
    optional_date,
    require_keys,
    territory_contains,
    to_date,
)
from housefinder.core.figures import SourceRef


def default_params_dir() -> Path:
    """services/api/data/params"""
    return Path(__file__).resolve().parents[3] / "data" / "params"


@dataclass(frozen=True)
class Param:
    id: str
    kind: str  # p. ej. "criterios_bancarios", "trayectoria_euribor"
    territory: str
    effective_from: date
    effective_to: date | None
    params: dict[str, Any]
    source: str  # de dónde salen los valores, en una frase
    source_url: str | None = None
    provisional: bool = True  # True mientras no haya fuente documentada
    notes: str = ""

    @property
    def ref(self) -> SourceRef:
        return SourceRef("param", self.id, provisional=self.provisional)

    def applies_on(self, on: date) -> bool:
        return applies_on(self.effective_from, self.effective_to, on)


@dataclass
class ParamBook:
    params: list[Param] = field(default_factory=list)

    @classmethod
    def from_dir(cls, path: Path) -> ParamBook:
        params = [_parse_param(raw) for raw in load_yaml_records(path)]
        seen: set[str] = set()
        for p in params:
            if p.id in seen:
                raise ValueError(f"Parámetro con id repetido: {p.id}")
            seen.add(p.id)
        return cls(params)

    def of_kind(self, kind: str) -> list[Param]:
        return [p for p in self.params if p.kind == kind]

    def resolve(self, kind: str, territory: str, on: date) -> Param | None:
        """Parámetro vigente más específico para un territorio y una fecha."""
        return most_specific(
            p
            for p in self.params
            if p.kind == kind and p.applies_on(on) and territory_contains(p.territory, territory)
        )


def _parse_param(raw: dict[str, Any]) -> Param:
    require_keys(raw, ("id", "kind", "territory", "effective_from", "params", "source"))
    return Param(
        id=raw["id"],
        kind=raw["kind"],
        territory=raw["territory"],
        effective_from=to_date(raw["effective_from"]),
        effective_to=optional_date(raw.get("effective_to")),
        params=raw["params"],
        source=raw["source"],
        source_url=raw.get("source_url"),
        provisional=bool(raw.get("provisional", True)),
        notes=raw.get("notes", ""),
    )
