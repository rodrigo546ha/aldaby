"""Escenarios normativos: el mismo plan con y sin las reglas pendientes (F2.5).

Un escenario es el conjunto de cifras que sale al recalcular con otras reglas. Se compara
con el plan base cifra a cifra, por su clave, y cada diferencia es a su vez una `Figure`
que cita las fuentes de las dos cifras.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from housefinder.core.figures import Figure, SourceRef, combine_sources

NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class FigureChange:
    key: str
    base: Figure
    scenario: Figure
    delta: Figure  # escenario − base

    @property
    def changed(self) -> bool:
        return self.delta.value != 0


@dataclass(frozen=True)
class ScenarioComparison:
    name: str  # p. ej. "rdl-29-2026"
    changes: tuple[FigureChange, ...]  # claves presentes en los dos lados, en orden del base
    only_in_base: tuple[str, ...]
    only_in_scenario: tuple[str, ...]
    new_rules: tuple[SourceRef, ...]  # reglas que cita el escenario y no el base

    @property
    def changed(self) -> tuple[FigureChange, ...]:
        return tuple(c for c in self.changes if c.changed)


def compare_figures(
    name: str, base: Iterable[Figure], scenario: Iterable[Figure]
) -> ScenarioComparison:
    if not NAME.match(name):
        raise ValueError(f"Nombre de escenario no válido (minúsculas, cifras y guiones): {name!r}")
    base_by_key = _by_key(base)
    scenario_by_key = _by_key(scenario)
    changes = []
    for key, b in base_by_key.items():
        s = scenario_by_key.get(key)
        if s is None:
            continue
        if b.unit != s.unit:
            raise ValueError(f"{key}: unidad distinta en base ({b.unit}) y escenario ({s.unit})")
        delta = Figure(
            f"scenario.{name}.{key}.delta",
            s.value - b.value,
            b.unit,
            f"{key} en el escenario «{name}» − {key} en el plan base",
            combine_sources(b.sources, s.sources),
        )
        changes.append(FigureChange(key, b, s, delta))
    base_rules = {ref for f in base_by_key.values() for ref in f.sources if ref.kind == "rule"}
    new_rules = combine_sources(
        *(
            [ref for ref in f.sources if ref.kind == "rule" and ref not in base_rules]
            for f in scenario_by_key.values()
        )
    )
    return ScenarioComparison(
        name=name,
        changes=tuple(changes),
        only_in_base=tuple(k for k in base_by_key if k not in scenario_by_key),
        only_in_scenario=tuple(k for k in scenario_by_key if k not in base_by_key),
        new_rules=new_rules,
    )


def compare_with_pending(
    name: str, build: Callable[[bool], Iterable[Figure]]
) -> ScenarioComparison:
    """Compara el plan base con el mismo plan aplicando las reglas pendientes.

    `build(include_pending)` calcula las cifras del plan con o sin reglas pendientes.
    """
    return compare_figures(name, build(False), build(True))


def _by_key(figures: Iterable[Figure]) -> dict[str, Figure]:
    result: dict[str, Figure] = {}
    for fig in figures:
        if fig.key in result:
            raise ValueError(f"Clave repetida en un mismo escenario: {fig.key}")
        result[fig.key] = fig
    return result
