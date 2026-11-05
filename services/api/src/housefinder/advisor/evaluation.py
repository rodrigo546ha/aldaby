"""Banco del agente: las mismas preguntas a un modelo, medidas igual (F6.0).

Para comparar modelos con algo más que una pregunta suelta. Mide lo que se puede medir sin leer el
texto: si pidió las herramientas que hacían falta, si el texto pasó la comprobación (a la primera o
tras el reintento), por qué falló y cuánto tardó. El significado del texto se lee a mano: el banco
lo guarda junto a cada resultado.

Las preguntas hablan de «la oferta de {municipio}»: se rellenan con una oferta confirmada y ubicada
de la organización de desarrollo. Las de búsqueda, tipo de alquiler y plan necesitan el perfil
confirmado (F6.9): sin él se saltan.

De cada texto mostrado se cuentan además los dígitos fuera de marcadores (cero por construcción,
ADR-0012) y las contradicciones de sentido (`agent.sense`, ADR-0027).

Las conversaciones (ADR-0067) son varias preguntas seguidas, con el historial que pone la API
(ADR-0064): las respuestas anteriores con sus marcadores. Miden además lo que solo pasa en una
conversación: si vuelve a pedir la herramienta en cada vuelta (los marcadores viejos no valen), si
cita la cifra de lo que se pregunta («¿y con la variable?») y si «está cara» habla de la misma
oferta que la vuelta anterior.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from housefinder.advisor.conversations import HISTORY_MESSAGES
from housefinder.agent.llm import Message
from housefinder.agent.loop import AgentAnswer
from housefinder.agent.references import MARKER, FigureSegment, OfferSegment, TextSegment
from housefinder.agent.sense import contradictions


@dataclass(frozen=True)
class Case:
    question: str
    tools: frozenset[str]  # herramientas que tiene que pedir para contestar
    needs_profile: bool = False


CASES = (
    Case("¿Está cara mi oferta de {municipio}? ¿Cuánto se alquilaría?",
         frozenset({"valorar_oferta"})),
    Case("¿Cuánto podría revalorizarse la oferta de {municipio}?",
         frozenset({"valorar_oferta"})),
    Case("¿Qué rentabilidad bruta tendría la oferta de {municipio} si la compro al precio que "
         "piden?", frozenset({"valorar_oferta"})),
    Case("¿Cómo es la zona de mi oferta de {municipio}?", frozenset({"zona_de_oferta"})),
    Case("¿Qué ofertas tengo guardadas?", frozenset({"ofertas_guardadas"})),
    # F6.9: búsqueda, tipo de alquiler y plan completo, con el perfil del usuario
    Case("¿Qué ofertas me encajan?", frozenset({"buscar_ofertas"}), needs_profile=True),
    Case("¿Cómo me conviene alquilar la oferta de {municipio}? ¿La gestiono yo o la delego?",
         frozenset({"recomendar_alquiler"}), needs_profile=True),
    Case("Explícame mi plan completo para la oferta de {municipio}.",
         frozenset({"plan_completo"}), needs_profile=True),
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
    invented: int = 0  # dígitos fuera de marcadores en el texto mostrado (tiene que ser cero)
    contradictions: tuple[str, ...] = ()  # reglas de sentido que no cumple


def run_cases(answer: Callable[[str], AgentAnswer], cases: Sequence[Case],
              municipality: str) -> list[Result]:
    results = []
    for case in cases:
        question = case.question.format(municipio=municipality)
        start = time.monotonic()
        reply = answer(question)
        results.append(_result(question, case.tools, reply, time.monotonic() - start))
    return results


def _result(question: str, tools: frozenset[str], reply: AgentAnswer, seconds: float) -> Result:
    worked = {s.tool for s in reply.steps if s.ok}
    parts = reply.segments or []
    return Result(
        question=question, tools_ok=tools <= worked, shown=reply.segments is not None,
        first_try=reply.segments is not None and not reply.rejected,
        failure=reply.failure, seconds=round(seconds, 1), text=_text(reply),
        invented=sum(ch.isdigit() for p in parts if isinstance(p, TextSegment) for ch in p.text),
        contradictions=tuple(c.rule for c in contradictions(parts)))


@dataclass(frozen=True)
class Turn:
    question: str
    tools: frozenset[str]  # las que tiene que pedir en esta vuelta, aunque ya las pidiera antes
    keys: frozenset[str] = frozenset()  # tiene que citar al menos una (sin el prefijo de oferta)
    same_offer: bool = False  # sus cifras son de la oferta de la vuelta anterior


@dataclass(frozen=True)
class Conversation:
    name: str
    turns: tuple[Turn, ...]
    offer: bool  # en el plan de una oferta (ADR-0063) o en «Mi plan», sin oferta (ADR-0066)
    needs_profile: bool = True


CONVERSATIONS = (
    Conversation("Plan de una oferta", offer=True, turns=(
        Turn("¿Qué me queda al mes con esta oferta?", frozenset({"plan_completo"}),
             keys=frozenset({"cashflow.monthly_after_tax"})),
        Turn("¿Y si suben los tipos?", frozenset({"plan_completo"}),
             keys=frozenset({"mortgage.stressed_payment", "search.stressed_cashflow"})),
        # El fallo visto en la web: atribuir a la variable las cifras de la fija
        Turn("¿Y con la hipoteca variable?", frozenset({"plan_completo"}),
             keys=frozenset({"mortgage_comparison.variable.expected_total_interest"})),
    )),
    Conversation("Zona y precio en «Mi plan»", offer=False, needs_profile=False, turns=(
        Turn("¿Cómo es la zona de mi oferta de {municipio}?", frozenset({"zona_de_oferta"})),
        Turn("¿Y está cara frente a lo que vale?", frozenset({"valorar_oferta"}),
             same_offer=True),
    )),
    Conversation("Búsqueda y alquiler en «Mi plan»", offer=False, turns=(
        Turn("¿Qué ofertas me encajan?", frozenset({"buscar_ofertas"})),
        Turn("¿Cómo me conviene alquilar la primera?", frozenset({"recomendar_alquiler"})),
    )),
)


@dataclass(frozen=True)
class TurnResult:
    conversation: str
    result: Result
    keys_ok: bool | None  # None: la vuelta no pide ninguna cifra concreta
    same_offer: bool | None  # None: no se comprueba en esta vuelta


Ask = Callable[[Conversation, str, list[Message]], AgentAnswer]


def run_conversations(answer: Ask, conversations: Sequence[Conversation],
                      municipality: str) -> list[TurnResult]:
    """Cada conversación con el historial que pondría la API: las preguntas y los textos
    aceptados, con sus marcadores, hasta HISTORY_MESSAGES."""
    results = []
    for conversation in conversations:
        history: list[Message] = []
        before: set[str] = set()  # ofertas de las cifras de la vuelta anterior
        for turn in conversation.turns:
            question = turn.question.format(municipio=municipality)
            start = time.monotonic()
            reply = answer(conversation, question, history)
            result = _result(question, turn.tools, reply, time.monotonic() - start)
            cited = cited_keys(reply.text) if result.shown else set()
            offers = {key.split(".")[0] for key in cited if key.startswith("oferta_")}
            bare = {key.split(".", 1)[1] if key.startswith("oferta_") else key for key in cited}
            results.append(TurnResult(
                conversation=conversation.name, result=result,
                keys_ok=bool(bare & turn.keys) if turn.keys else None,
                same_offer=bool(offers) and offers <= before if turn.same_offer else None))
            if reply.text and result.shown:
                history = [*history, {"role": "user", "content": question},
                           {"role": "assistant", "content": reply.text}][-HISTORY_MESSAGES:]
            before = offers
    return results


def cited_keys(text: str | None) -> set[str]:
    """Las claves de las cifras que cita un texto aceptado, con su prefijo de oferta si lo hay."""
    return {m.group(1) for m in MARKER.finditer(text or "") if m.group(1)}


def conversation_metrics(results: Sequence[TurnResult]) -> dict[str, int]:
    turns = [r.result for r in results]
    return {"vueltas": len(turns), "herramientas": sum(r.tools_ok for r in turns),
            "mostrados": sum(r.shown for r in turns),
            "a_la_primera": sum(r.first_try for r in turns),
            "con_cifra_pedida": sum(r.keys_ok is not None for r in results),
            "cifra_pedida": sum(bool(r.keys_ok) for r in results),
            "con_misma_oferta": sum(r.same_offer is not None for r in results),
            "misma_oferta": sum(bool(r.same_offer) for r in results),
            "cifras_fuera": sum(r.invented for r in turns),
            "contradicciones": sum(len(r.contradictions) for r in turns)}


def summary(results: Sequence[Result]) -> str:
    n = len(results)
    if n == 0:
        return "Sin casos."
    return (f"herramientas correctas {sum(r.tools_ok for r in results)}/{n} · "
            f"texto mostrado {sum(r.shown for r in results)}/{n} · "
            f"a la primera {sum(r.first_try for r in results)}/{n} · "
            f"cifras fuera de marcadores {sum(r.invented for r in results)} · "
            f"contradicciones {sum(len(r.contradictions) for r in results)} · "
            f"tiempo medio {sum(r.seconds for r in results) / n:.0f} s")


def _text(reply: AgentAnswer) -> str:
    if reply.segments is None:
        return " | ".join(p for problems in reply.rejected for p in problems) or "(sin texto)"
    return "".join(f"[{s.figure.key}]" if isinstance(s, FigureSegment)
                   else f"[oferta {s.label}]" if isinstance(s, OfferSegment) else s.text
                   for s in reply.segments)
