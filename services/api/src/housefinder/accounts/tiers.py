"""Niveles de acceso (F8.2, ADR-0041) y consultas al asesor al día (ADR-0065): los límites son
datos, no código."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FreeTier:
    full_plans: int  # ofertas distintas con plan completo
    advisor_per_day: int  # preguntas y explicaciones del asesor al día


@dataclass(frozen=True)
class ProfessionalTier:
    advisor_per_day: int  # de toda la organización


def default_path() -> Path:
    """services/api/data/niveles.yaml"""
    return Path(__file__).resolve().parents[3] / "data" / "niveles.yaml"


def _read(path: Path | None) -> dict:
    return yaml.safe_load((path or default_path()).read_text(encoding="utf-8"))


@lru_cache
def free_tier(path: Path | None = None) -> FreeTier:
    free = _read(path)["gratuito"]
    return FreeTier(full_plans=int(free["planes_completos"]),
                    advisor_per_day=int(free["consultas_asesor_dia"]))


@lru_cache
def professional_tier(path: Path | None = None) -> ProfessionalTier:
    return ProfessionalTier(advisor_per_day=int(_read(path)["profesional"]["consultas_asesor_dia"]))


def advisor_limit(particular: bool) -> int:
    """Consultas al asesor al día de una organización (ADR-0065)."""
    return free_tier().advisor_per_day if particular else professional_tier().advisor_per_day


def plans_left(used: int, tier: FreeTier) -> int:
    return max(tier.full_plans - used, 0)
