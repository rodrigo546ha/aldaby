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

import yaml

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
        return self.effective_from <= on and (self.effective_to is None or on < self.effective_to)


@dataclass
class RuleBook:
    rules: list[Rule] = field(default_factory=list)

    @classmethod
    def from_dir(cls, path: Path) -> RuleBook:
        rules: list[Rule] = []
        for file in sorted(path.glob("*.yaml")):
            for raw in yaml.safe_load(file.read_text(encoding="utf-8")) or []:
                rules.append(_parse_rule(raw))
        return cls(rules)

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
        candidates = [
            r
            for r in self.rules
            if r.kind == kind
            and r.status in allowed
            and r.applies_on(on)
            and (r.verified or allow_unverified)
            and _territory_contains(r.territory, territory)
        ]
        if not candidates:
            return None
        # Más específico primero; a igualdad, la de inicio de vigencia más reciente.
        candidates.sort(key=lambda r: (r.territory.count("-"), r.effective_from), reverse=True)
        return candidates[0]


def _territory_contains(rule_territory: str, target: str) -> bool:
    return target == rule_territory or target.startswith(rule_territory + "-")


def _parse_rule(raw: dict[str, Any]) -> Rule:
    status = raw.get("status", "vigente")
    if status not in VALID_STATUS:
        raise ValueError(f"Estado no válido en la regla {raw.get('id')}: {status}")
    for key in ("id", "kind", "territory", "effective_from", "source_url"):
        if key not in raw:
            raise ValueError(f"Falta '{key}' en una regla: {raw}")
    return Rule(
        id=raw["id"],
        kind=raw["kind"],
        territory=raw["territory"],
        effective_from=_to_date(raw["effective_from"]),
        effective_to=_to_date(raw["effective_to"]) if raw.get("effective_to") else None,
        status=status,
        params=raw.get("params", {}),
        source_url=raw["source_url"],
        notes=raw.get("notes", ""),
        verified=bool(raw.get("verified", False)),
    )


def _to_date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))
