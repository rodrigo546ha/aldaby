"""Hoja de ruta de compra: los pasos de `data/plan/hoja_de_ruta.yaml` que aplican a un plan.

Los pasos son datos con su fuente oficial, como las reglas (ADR-0025): el código solo elige los
que aplican por canal, hipoteca y tipo de alquiler. Ninguno está verificado hasta que Rodrigo lea
su fuente.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from housefinder.regulation.kinds import RENTAL_TYPES

Stage = Literal["antes", "compra", "despues"]


class When(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: tuple[Literal["enlace", "lote"], ...] | None = None
    mortgage: bool | None = None
    rental_types: tuple[str, ...] | None = None


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    stage: Stage
    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https?://")
    verified: bool = False
    when: When = When()

    def applies(self, channel: str, mortgage: bool, rental_type: str | None) -> bool:
        w = self.when
        return ((w.channel is None or channel in w.channel)
                and (w.mortgage is None or w.mortgage == mortgage)
                and (w.rental_types is None or rental_type in w.rental_types))


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "plan" / "hoja_de_ruta.yaml"


@lru_cache
def load_steps(path: Path | None = None) -> tuple[Step, ...]:
    raw = yaml.safe_load((path or default_path()).read_text(encoding="utf-8"))
    steps = tuple(Step.model_validate(item) for item in raw)
    ids = [s.id for s in steps]
    if len(set(ids)) != len(ids):
        raise ValueError("Pasos repetidos en la hoja de ruta")
    unknown = {t for s in steps for t in (s.when.rental_types or ()) if t not in RENTAL_TYPES}
    if unknown:
        raise ValueError(f"Tipos de alquiler desconocidos en la hoja de ruta: {sorted(unknown)}")
    return steps


def roadmap(channel: str, mortgage: bool, rental_type: str | None,
            steps: tuple[Step, ...] | None = None) -> tuple[Step, ...]:
    """Los pasos que aplican, en el orden del fichero."""
    return tuple(s for s in (steps or load_steps()) if s.applies(channel, mortgage, rental_type))
