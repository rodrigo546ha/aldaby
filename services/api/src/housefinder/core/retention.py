"""Plazos de conservación que citan los textos legales (`data/conservacion.yaml`, ADR-0064)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "conservacion.yaml"


@lru_cache
def conversation_days(path: Path | None = None) -> int:
    """Días que se guarda una conversación con el asesor desde la última pregunta."""
    data = yaml.safe_load((path or default_path()).read_text(encoding="utf-8"))
    return int(data["conversaciones_dias"])
