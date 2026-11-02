"""Niveles de acceso de los particulares (F8.2, ADR-0041): el límite es un dato, no código."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FreeTier:
    full_plans: int  # ofertas distintas con plan completo


def default_path() -> Path:
    """services/api/data/niveles.yaml"""
    return Path(__file__).resolve().parents[3] / "data" / "niveles.yaml"


@lru_cache
def free_tier(path: Path | None = None) -> FreeTier:
    data = yaml.safe_load((path or default_path()).read_text(encoding="utf-8"))
    return FreeTier(full_plans=int(data["gratuito"]["planes_completos"]))


def plans_left(used: int, tier: FreeTier) -> int:
    return max(tier.full_plans - used, 0)
