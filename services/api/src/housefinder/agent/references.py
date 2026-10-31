"""El agente escribe referencias a cifras, no cifras (ADR-0012).

El texto del agente nombra cada cifra con un marcador `{{fig:clave}}` (o `{{fig:clave:low}}`,
`:high`, `:range` si tiene rango). Antes de mostrarlo se comprueba sin LLM: ningún dígito fuera de
un marcador, cada clave entre las cifras del plan y ninguna llave suelta. El texto válido se
convierte en segmentos; la web y el PDF formatean cada cifra, Python no la escribe como texto.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from housefinder.core.figures import Figure

Part = Literal["value", "low", "high", "range"]
ProblemKind = Literal["digito", "clave_desconocida", "sin_rango", "marcador_mal_escrito"]

MARKER = re.compile(r"\{\{fig:([a-z0-9_]+(?:\.[a-z0-9_]+)+)(?::(low|high|range))?\}\}")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
BRACES = re.compile(r"\{|\}")
CONTEXT = 12  # caracteres a cada lado del problema en el mensaje


@dataclass(frozen=True)
class TextSegment:
    text: str


@dataclass(frozen=True)
class FigureSegment:
    figure: Figure
    part: Part


Segment = TextSegment | FigureSegment


@dataclass(frozen=True)
class Problem:
    kind: ProblemKind
    message: str  # en español: se devuelve al modelo en el reintento
    phrase: str = ""  # el número con la palabra de cada lado, para saber de dónde lo copió


class InvalidText(ValueError):
    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("; ".join(p.message for p in problems))
        self.problems = problems


def check_text(text: str, figures: Mapping[str, Figure]) -> list[Problem]:
    problems: list[Problem] = []
    for start, end, match in _pieces(text):
        if match is None:
            problems += _loose(text[start:end])
            continue
        key, part = match.group(1), match.group(2)
        figure = figures.get(key)
        if figure is None:
            problems.append(Problem("clave_desconocida", f"La cifra «{key}» no está en el plan."))
        elif part is not None and figure.low is None:
            problems.append(Problem("sin_rango", f"La cifra «{key}» no tiene rango: usa "
                                                 f"{{{{fig:{key}}}}} sin «:{part}»."))
    return problems


def segments(text: str, figures: Mapping[str, Figure]) -> list[Segment]:
    """Texto comprobado → segmentos. `InvalidText` con los problemas si no pasa."""
    problems = check_text(text, figures)
    if problems:
        raise InvalidText(problems)
    result: list[Segment] = []
    for start, end, match in _pieces(text):
        if match is None:
            result.append(TextSegment(text[start:end]))
        else:
            part: Part = match.group(2) or "value"  # type: ignore[assignment]
            result.append(FigureSegment(figures[match.group(1)], part))
    return result


def _pieces(text: str) -> list[tuple[int, int, re.Match[str] | None]]:
    """Tramos de texto libre (sin match) y marcadores válidos, en orden."""
    pieces: list[tuple[int, int, re.Match[str] | None]] = []
    position = 0
    for match in MARKER.finditer(text):
        if match.start() > position:
            pieces.append((position, match.start(), None))
        pieces.append((match.start(), match.end(), match))
        position = match.end()
    if position < len(text):
        pieces.append((position, len(text), None))
    return pieces


def _loose(free: str) -> list[Problem]:
    """Problemas de un tramo de texto libre: cada número y llaves que no forman un marcador."""
    problems = []
    for number in NUMBER.finditer(free):
        phrase = " ".join(free[:number.start()].split()[-1:] + [number.group()]
                          + free[number.end():].split()[:1])
        problems.append(Problem("digito", f"Hay un número escrito a mano "
                                          f"(«{_around(free, number)}»): usa un marcador "
                                          "{{fig:clave}} o di lo mismo sin números.", phrase))
    brace = BRACES.search(free)
    if brace:
        problems.append(Problem("marcador_mal_escrito",
                                f"Marcador mal escrito («{_around(free, brace)}»): el formato es "
                                "{{fig:clave}}."))
    return problems


def _around(free: str, found: re.Match[str]) -> str:
    """El problema con un poco de contexto, sin salir del tramo de texto libre."""
    return free[max(0, found.start() - CONTEXT):found.start() + CONTEXT].strip()
