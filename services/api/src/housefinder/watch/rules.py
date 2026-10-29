"""Filtros de vigilancia (data/watch/vigilancia.yaml) y su aplicación a una publicación.

Funciones puras: deciden si una publicación abre tarea, con qué temas y qué reglas afecta.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Publication:
    source: str  # 'boe' | 'bocm'
    identifier: str
    title: str
    url: str
    published_on: date
    section: str
    part: str = ""  # apartado del BOCM
    department: str = ""


@dataclass(frozen=True)
class Tracked:
    pattern: re.Pattern[str]
    rules: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class SourceFilter:
    sections: frozenset[str]
    exclude_parts: frozenset[str] = frozenset()


@dataclass(frozen=True)
class WatchRules:
    sources: dict[str, SourceFilter]
    topics: dict[str, tuple[re.Pattern[str], ...]]
    exclude: tuple[re.Pattern[str], ...]
    tracked: tuple[Tracked, ...]
    always: tuple[re.Pattern[str], ...] = ()  # pasan aunque caigan en una exclusión
    exclude_departments: tuple[re.Pattern[str], ...] = ()


@dataclass(frozen=True)
class Match:
    tags: tuple[str, ...]
    rule_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


def default_rules_path() -> Path:
    """services/api/data/watch/vigilancia.yaml"""
    return Path(__file__).resolve().parents[3] / "data" / "watch" / "vigilancia.yaml"


def fold(text: str) -> str:
    """Minúsculas y sin tildes, para comparar títulos con patrones simples."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def load_rules(path: Path | None = None) -> WatchRules:
    raw: dict[str, Any] = yaml.safe_load((path or default_rules_path()).read_text("utf-8"))

    def compile_all(patterns: list[str]) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(fold(p)) for p in patterns)

    sources = {
        name: SourceFilter(frozenset(spec.get("sections", [])),
                           frozenset(spec.get("exclude_parts", [])))
        for name, spec in raw["sources"].items()
    }
    return WatchRules(
        sources=sources,
        topics={tag: compile_all(patterns) for tag, patterns in raw["topics"].items()},
        exclude=compile_all(raw.get("exclude", [])),
        tracked=tuple(
            Tracked(re.compile(fold(t["pattern"])), tuple(t.get("rules", [])), t["note"])
            for t in raw.get("tracked", [])
        ),
        always=compile_all(raw.get("always", [])),
        exclude_departments=compile_all(raw.get("exclude_departments", [])),
    )


def match(pub: Publication, rules: WatchRules) -> Match | None:
    """Temas y reglas de una publicación, o None si no abre tarea.

    Lo que se sigue por nombre abre tarea en cualquier sección. El resto, solo en las
    secciones vigiladas y fuera de los departamentos excluidos, si toca algún tema y no cae
    en una exclusión (salvo los patrones de `always`).
    """
    title = fold(pub.title)
    tracked = [t for t in rules.tracked if t.pattern.search(title)]
    if tracked:
        return Match(
            tags=("seguimiento",),
            rule_ids=tuple(r for t in tracked for r in t.rules),
            notes=tuple(t.note for t in tracked),
        )
    scope = rules.sources.get(pub.source)
    if scope is None or pub.section not in scope.sections or pub.part in scope.exclude_parts:
        return None
    if any(p.search(fold(pub.department)) for p in rules.exclude_departments):
        return None
    forced = any(p.search(title) for p in rules.always)
    if not forced and any(p.search(title) for p in rules.exclude):
        return None
    tags = tuple(tag for tag, patterns in rules.topics.items()
                 if any(p.search(title) for p in patterns))
    return Match(tags) if tags else None
