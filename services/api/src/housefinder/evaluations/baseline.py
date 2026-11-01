"""Línea base de las evaluaciones (ADR-0027): sin umbrales inventados.

Lo que no depende del modelo tiene que dar cero (`MUST_BE_ZERO`). Lo que sí depende se compara con
la última línea base guardada: avisa si un acierto baja o un fallo sube.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HIGHER_IS_BETTER = {"extraccion.correctos", "agente.herramientas", "agente.mostrados",
                    "agente.a_la_primera"}
LOWER_IS_BETTER = {"extraccion.falta", "extraccion.distinto", "extraccion.sobra",
                   "extraccion.lotes_de_mas", "extraccion.lotes_de_menos", "extraccion.errores",
                   "agente.contradicciones"}
MUST_BE_ZERO = {"agente.cifras_fuera", "coherencia.incoherencias"}


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "evaluation" / "linea_base.json"


def flatten(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {f"{group}.{name}": value for group, values in metrics.items()
            for name, value in values.items()}


def compare(current: dict[str, dict[str, Any]], saved: dict[str, Any] | None) -> list[str]:
    """Los problemas: cifras que tenían que ser cero y empeoramientos frente a la base."""
    now = flatten(current)
    problems = [f"{k} = {now[k]}: tiene que ser cero" for k in sorted(MUST_BE_ZERO)
                if now.get(k)]
    before = flatten(saved.get("metricas", {})) if saved else {}
    for key in sorted(now):
        if key not in before or not isinstance(now[key], int):
            continue
        if key in HIGHER_IS_BETTER and now[key] < before[key]:
            problems.append(f"{key} baja de {before[key]} a {now[key]}")
        if key in LOWER_IS_BETTER and now[key] > before[key]:
            problems.append(f"{key} sube de {before[key]} a {now[key]}")
    return problems


def load(path: Path | None = None) -> dict[str, Any] | None:
    path = path or default_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(metrics: dict[str, dict[str, Any]], model: str | None, day: str,
         path: Path | None = None) -> None:
    (path or default_path()).write_text(
        json.dumps({"modelo": model, "fecha": day, "metricas": metrics}, ensure_ascii=False,
                   indent=2) + "\n", encoding="utf-8")
