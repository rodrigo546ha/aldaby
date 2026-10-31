"""Banco del agente: las mismas preguntas a un modelo, medidas igual (F6.0).

Para comparar modelos con algo más que una pregunta suelta. Mide lo que se puede medir sin leer el
texto: si pidió las herramientas que hacían falta, si el texto pasó la comprobación (a la primera o
tras el reintento), por qué falló y cuánto tardó. El significado del texto se lee a mano: el banco
lo guarda junto a cada resultado.

Las preguntas hablan de «la oferta de {municipio}»: se rellenan con una oferta confirmada y ubicada
de la organización de desarrollo.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from housefinder.agent.loop import AgentAnswer
from housefinder.agent.references import FigureSegment


@dataclass(frozen=True)
class Case:
    question: str
    tools: frozenset[str]  # herramientas que tiene que pedir para contestar


CASES = (
    Case("¿Está cara mi oferta de {municipio}? ¿Cuánto se alquilaría?",
         frozenset({"valorar_oferta"})),
    Case("¿Cuánto podría revalorizarse la oferta de {municipio}?",
         frozenset({"valorar_oferta"})),
    Case("¿Qué rentabilidad bruta tendría la oferta de {municipio} si la compro al precio que "
         "piden?", frozenset({"valorar_oferta"})),
    Case("¿Cómo es la zona de mi oferta de {municipio}?", frozenset({"zona_de_oferta"})),
    Case("¿Qué ofertas tengo guardadas?", frozenset({"ofertas_guardadas"})),
)


@dataclass(frozen=True)
class Result:
    question: str
    tools_ok: bool  # pidió todas las herramientas necesarias y todas funcionaron
    shown: bool  # el texto pasó la comprobación y se puede mostrar
    first_try: bool  # sin ningún rechazo
    failure: str | None
    seconds: float
    text: str  # el texto con las cifras como [clave], o los problemas si no se muestra


def run_cases(answer: Callable[[str], AgentAnswer], cases: Sequence[Case],
              municipality: str) -> list[Result]:
    results = []
    for case in cases:
        question = case.question.format(municipio=municipality)
        start = time.monotonic()
        reply = answer(question)
        seconds = time.monotonic() - start
        worked = {s.tool for s in reply.steps if s.ok}
        results.append(Result(
            question=question, tools_ok=case.tools <= worked, shown=reply.segments is not None,
            first_try=reply.segments is not None and not reply.rejected,
            failure=reply.failure, seconds=round(seconds, 1), text=_text(reply)))
    return results


def summary(results: Sequence[Result]) -> str:
    n = len(results)
    if n == 0:
        return "Sin casos."
    return (f"herramientas correctas {sum(r.tools_ok for r in results)}/{n} · "
            f"texto mostrado {sum(r.shown for r in results)}/{n} · "
            f"a la primera {sum(r.first_try for r in results)}/{n} · "
            f"tiempo medio {sum(r.seconds for r in results) / n:.0f} s")


def _text(reply: AgentAnswer) -> str:
    if reply.segments is None:
        return " | ".join(p for problems in reply.rejected for p in problems) or "(sin texto)"
    return "".join(f"[{s.figure.key}]" if isinstance(s, FigureSegment) else s.text
                   for s in reply.segments)
