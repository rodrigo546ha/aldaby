"""Embudo de alta de particulares (ADR-0042): cuántos llegan a cada paso y qué parte del
anterior."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Step:
    name: str
    count: int
    of_previous: Decimal | None  # tanto por uno respecto al paso anterior; None en el primero


STEPS = (
    ("visits", "Visitas a la página de presentación"),
    ("waitlist", "Particulares apuntados a la lista de espera"),
    ("accounts", "Altas de particulares"),
    ("profiles", "Con el perfil confirmado"),
    ("plans", "Con algún plan completo"),
)


def funnel(counts: dict[str, int]) -> list[Step]:
    steps: list[Step] = []
    previous: int | None = None
    for key, name in STEPS:
        count = counts[key]
        share = None
        if previous is not None and previous > 0:
            share = (Decimal(count) / Decimal(previous)).quantize(Decimal("0.001"),
                                                                 rounding=ROUND_HALF_UP)
        steps.append(Step(name, count, share))
        previous = count
    return steps
