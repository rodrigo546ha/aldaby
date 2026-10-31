"""Contradicciones de sentido en el texto del asesor (F6.9, ADR-0027).

La comprobación de ADR-0012 asegura que cada cifra sale de un marcador, pero no que la frase la
describa bien. Estas reglas fijas miran la frase de cada marcador:
- una palabra de signo junto a una cifra del signo contrario («positivo» ante un cash flow
  negativo, «pierdes» ante uno positivo);
- una comparación entre dos marcadores de la misma unidad que las cifras no cumplen
  («A supera B» con A ≤ B, «A no llega a B» con A ≥ B).
Solo ven lo explícito; el resto del texto se lee a mano.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from housefinder.agent.references import FigureSegment, OfferSegment, Segment, TextSegment

WINDOW = 40  # caracteres de texto a cada lado del marcador
POSITIVE = re.compile(r"\b(?:positiv[oa]s?|ganas|ganancias?|beneficios?)\b", re.IGNORECASE)
NEGATIVE = re.compile(r"\b(?:negativ[oa]s?|pierdes|p[ée]rdidas?)\b", re.IGNORECASE)
GREATER = re.compile(r"\b(?:supera|superan|por encima de|mayor que|m[áa]s que|excede|"
                     r"sobrepasa)\b", re.IGNORECASE)
LESS = re.compile(r"\b(?:por debajo de|menor que|no llega a|no alcanza|inferior a|"
                  r"menos que)\b", re.IGNORECASE)
NEGATED = re.compile(r"\bno\s+(?:es\s+|son\s+|sale\s+)?$", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.!?;])\s+|\n")
MAX_BETWEEN = 60


@dataclass(frozen=True)
class Contradiction:
    rule: str
    sentence: str  # la frase con las cifras como [clave]


def contradictions(segments: Sequence[Segment]) -> list[Contradiction]:
    found: list[Contradiction] = []
    for sentence in _sentences(segments):
        shown = "".join(f"[{p.figure.key}]" if isinstance(p, FigureSegment) else
                        (p.label if isinstance(p, OfferSegment) else p.text) for p in sentence)
        found += [Contradiction(rule, shown) for rule in _sign(sentence) + _compare(sentence)]
    return found


def _sentences(segments: Sequence[Segment]) -> list[list[Segment]]:
    sentences: list[list[Segment]] = [[]]
    for segment in segments:
        if not isinstance(segment, TextSegment):
            sentences[-1].append(segment)
            continue
        pieces = SENTENCE_END.split(segment.text)
        for i, piece in enumerate(pieces):
            if i > 0:
                sentences.append([])
            if piece:
                sentences[-1].append(TextSegment(piece))
    return [s for s in sentences if any(isinstance(p, FigureSegment) for p in s)]


def _sign(sentence: list[Segment]) -> list[str]:
    rules = []
    for i, part in enumerate(sentence):
        if not isinstance(part, FigureSegment) or part.part != "value":
            continue
        before = _text(sentence[:i])[-WINDOW:]
        after = _text(sentence[i + 1:])[:WINDOW]
        value = part.figure.value
        for window in (before, after):
            if value < 0 and _unnegated(POSITIVE, window):
                rules.append(f"palabra positiva junto a {part.figure.key}, que es negativa")
            if value > 0 and _unnegated(NEGATIVE, window):
                rules.append(f"palabra negativa junto a {part.figure.key}, que es positiva")
    return list(dict.fromkeys(rules))


def _compare(sentence: list[Segment]) -> list[str]:
    rules = []
    figures = [(i, p) for i, p in enumerate(sentence)
               if isinstance(p, FigureSegment) and p.part == "value"]
    for (i, a), (j, b) in zip(figures, figures[1:], strict=False):
        between = _text(sentence[i + 1:j])
        if len(between) > MAX_BETWEEN or a.figure.unit != b.figure.unit:
            continue
        x, y = a.figure.value, b.figure.value
        if _unnegated(GREATER, between) and not x > y:
            rules.append(f"dice que {a.figure.key} supera a {b.figure.key}, y no es así")
        if LESS.search(between) and not x < y:
            rules.append(f"dice que {a.figure.key} queda por debajo de {b.figure.key}, y no es así")
    return rules


def _unnegated(pattern: re.Pattern[str], text: str) -> bool:
    return any(not NEGATED.search(text[:m.start()]) for m in pattern.finditer(text))


def _text(parts: Sequence[Segment]) -> str:
    return "".join(p.text if isinstance(p, TextSegment) else " · " for p in parts)
