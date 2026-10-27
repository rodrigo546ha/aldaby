"""Motor de normativa: reglas como DATOS con vigencia, territorio y estado.

Una ley que cambia = una regla nueva en data/rules/, nunca un cambio de código.

Territorio: código jerárquico tipo "ES", "ES-13" (comunidad), "ES-13-28079" (municipio,
código INE). Se aplica la regla vigente más específica.
Estado: "vigente", "pendiente_convalidacion", "derogada". Las pendientes solo se
aplican cuando se pide un escenario que las incluya.
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

VALID_STATUS = {"vigente", "pendiente_convalidacion", "derogada"}


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str  # p. ej. "impuesto_compra_segunda_mano", "reduccion_irpf_alquiler"
    territory: str
    effective_from: date
    effective_to: date | None
    status: str
    params: dict[str, Any]
    source_url: str
    notes: str = ""
    verified: bool = False  # False = pendiente de verificación humana

    def applies_on(self, on: date) -> bool:
        return applies_on(self.effective_from, self.effective_to, on)


@dataclass
class RuleBook:
    rules: list[Rule] = field(default_factory=list)

    @classmethod
    def from_dir(cls, path: Path) -> RuleBook:
        return cls([_parse_rule(raw) for raw in load_yaml_records(path)])

    def resolve(
        self,
        kind: str,
        territory: str,
        on: date,
        include_pending: bool = False,
        allow_unverified: bool = False,
    ) -> Rule | None:
        """Regla aplicable más específica para un territorio y una fecha."""
        allowed = {"vigente"} | ({"pendiente_convalidacion"} if include_pending else set())
        return most_specific(
            r
            for r in self.rules
            if r.kind == kind
            and r.status in allowed
            and r.applies_on(on)
            and (r.verified or allow_unverified)
            and territory_contains(r.territory, territory)
        )


def _parse_rule(raw: dict[str, Any]) -> Rule:
    status = raw.get("status", "vigente")
    if status not in VALID_STATUS:
        raise ValueError(f"Estado no válido en la regla {raw.get('id')}: {status}")
    require_keys(raw, ("id", "kind", "territory", "effective_from", "source_url"))
    return Rule(
        id=raw["id"],
        kind=raw["kind"],
        territory=raw["territory"],
        effective_from=to_date(raw["effective_from"]),
        effective_to=optional_date(raw.get("effective_to")),
        status=status,
        params=raw.get("params", {}),
        source_url=raw["source_url"],
        notes=raw.get("notes", ""),
        verified=bool(raw.get("verified", False)),
    )
