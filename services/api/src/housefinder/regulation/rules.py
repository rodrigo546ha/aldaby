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
from housefinder.core.figures import SourceRef
from housefinder.regulation.validate import check_rules

VALID_STATUS = {"vigente", "pendiente_convalidacion", "derogada"}


def default_rules_dir() -> Path:
    """services/api/data/rules"""
    return Path(__file__).resolve().parents[3] / "data" / "rules"


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
    verified_by: str = ""  # quién leyó la fuente oficial
    verified_on: date | None = None  # cuándo

    def applies_on(self, on: date) -> bool:
        return applies_on(self.effective_from, self.effective_to, on)

    @property
    def ref(self) -> SourceRef:
        """Cita de la regla; provisional mientras no esté verificada."""
        return SourceRef("rule", self.id, provisional=not self.verified)


@dataclass
class RuleBook:
    rules: list[Rule] = field(default_factory=list)

    @classmethod
    def from_dir(cls, path: Path) -> RuleBook:
        """Carga y valida las reglas (catálogo de tipos, territorios, vigencias)."""
        rules = [_parse_rule(raw) for raw in load_yaml_records(path)]
        errors = check_rules(rules)
        if errors:
            raise ValueError("Reglas no válidas:\n" + "\n".join(f"- {e}" for e in errors))
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
        return most_specific(
            r
            for r in self.rules
            if r.kind == kind
            and r.status in allowed
            and r.applies_on(on)
            and (r.verified or allow_unverified)
            and territory_contains(r.territory, territory)
        )

    def pending(
        self, territory: str, on: date, allow_unverified: bool = False
    ) -> list[Rule]:
        """Reglas pendientes de convalidación aplicables: avisan de que hay un escenario."""
        return [
            r
            for r in self.rules
            if r.status == "pendiente_convalidacion"
            and r.applies_on(on)
            and (r.verified or allow_unverified)
            and territory_contains(r.territory, territory)
        ]


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
        verified_by=raw.get("verified_by", ""),
        verified_on=optional_date(raw.get("verified_on")),
    )
