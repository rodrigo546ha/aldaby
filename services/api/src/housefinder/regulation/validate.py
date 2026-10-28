"""Validación de un conjunto de reglas: esquema, territorio, vigencias y verificación."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from typing import TYPE_CHECKING

from housefinder.regulation.kinds import parse_params

if TYPE_CHECKING:
    from housefinder.regulation.rules import Rule

TERRITORY = re.compile(r"^ES(-\d{2}(-\d{5})?)?$")  # ES | ES-<ccaa> | ES-<ccaa>-<municipio>


def check_rules(rules: Sequence[Rule]) -> list[str]:
    """Errores encontrados, uno por línea con forma «id: motivo». Vacío si todo es válido."""
    errors: list[str] = []
    seen: set[str] = set()
    for rule in rules:
        if rule.id in seen:
            errors.append(f"{rule.id}: id repetido")
        seen.add(rule.id)
        errors.extend(f"{rule.id}: {msg}" for msg in _rule_errors(rule))
    errors.extend(_overlaps(rules))
    return errors


def _rule_errors(rule: Rule) -> list[str]:
    errors: list[str] = []
    try:
        parse_params(rule.kind, rule.params)
    except ValueError as exc:
        errors.append(str(exc))
    if not TERRITORY.match(rule.territory):
        errors.append(f"territorio no válido {rule.territory!r} (ES, ES-13 o ES-13-28079)")
    if rule.effective_to is not None and rule.effective_to <= rule.effective_from:
        errors.append("effective_to debe ser posterior a effective_from")
    if not rule.source_url.startswith(("https://", "http://")):
        errors.append(f"source_url no es una URL: {rule.source_url!r}")
    if rule.verified and not (rule.verified_by and rule.verified_on):
        errors.append("verified: true exige verified_by y verified_on")
    return errors


def _overlaps(rules: Sequence[Rule]) -> list[str]:
    """Dos reglas del mismo tipo, territorio y estado no pueden estar vigentes a la vez.

    Las derogadas no cuentan; una pendiente sí puede solaparse con una vigente (escenarios).
    """
    groups: dict[tuple[str, str, str], list[Rule]] = defaultdict(list)
    for rule in rules:
        if rule.status != "derogada":
            groups[(rule.kind, rule.territory, rule.status)].append(rule)
    errors: list[str] = []
    for group in groups.values():
        group.sort(key=lambda r: r.effective_from)
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if b.effective_from < (a.effective_to or date.max):
                    errors.append(
                        f"{a.id}: se solapan las vigencias con {b.id} "
                        f"({a.kind}, {a.territory}, {a.status}); cierra una con effective_to"
                    )
    return errors
