"""Evaluaciones automáticas con el modelo de `.env` (F6.9, ADR-0027).

    python -m housefinder.evaluations                      # todas, contra la línea base
    python -m housefinder.evaluations extraccion            # solo una (agente, conversacion…)
    python -m housefinder.evaluations --salida informe.md   # informe con cada fallo y cada texto
    python -m housefinder.evaluations --guardar-base        # guarda la nueva línea base

El asesor, sus conversaciones (ADR-0067) y la coherencia usan el perfil confirmado de la
organización local (con la clave maestra): sin él, se saltan y se dice.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from housefinder.advisor.evaluation import (
    CASES,
    CONVERSATIONS,
    Conversation,
    Result,
    TurnResult,
    conversation_metrics,
    run_cases,
    run_conversations,
    summary,
)
from housefinder.advisor.tools import ask, ask_about_offer, ask_in_plan
from housefinder.agent.extraction import extract, extract_listing
from housefinder.agent.llm import LLMClient, Message, llm_from_env
from housefinder.agent.loop import AgentAnswer
from housefinder.crypto.envelope import provider_from_env
from housefinder.db.connection import Connection, connect
from housefinder.db.offers import list_private_offers, search_candidates
from housefinder.db.profiles import get_or_create_organization, latest_profile_id
from housefinder.evaluations import baseline
from housefinder.evaluations.listings import ExtractionReport, evaluate, load_cases
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.plans.coherence import check_plan
from housefinder.plans.service import PlanUnavailable, full_plan
from housefinder.profiles import store
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook, default_rules_dir
from housefinder.search.service import SearchUnavailable

WHICH = ("extraccion", "agente", "conversacion", "coherencia")
DEV_ORG = "Desarrollo local"  # la misma que usa la API hasta la autenticación (G8)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.evaluations")
    parser.add_argument("cual", nargs="?", choices=WHICH, help="solo esta evaluación")
    parser.add_argument("--salida", type=Path, help="informe en Markdown")
    parser.add_argument("--guardar-base", action="store_true",
                        help="guarda las métricas como nueva línea base")
    args = parser.parse_args()
    which = [args.cual] if args.cual else list(WHICH)

    llm = llm_from_env()
    book = ParamBook.from_dir(default_params_dir())
    rules = RuleBook.from_dir(default_rules_dir())
    metrics: dict[str, dict[str, Any]] = {}
    lines = _shown([f"# Evaluaciones con {os.environ.get('LLM_MODEL_ID')} · {date.today()}", ""])
    with connect() as conn:
        org = get_or_create_organization(conn, DEV_ORG, "particular")
        conn.commit()
        profile = _profile(conn, org)
        if "extraccion" in which:
            report = evaluate(load_cases(), lambda t: extract_listing(llm, t),
                              lambda t: extract(llm, t))
            metrics["extraccion"] = report.metrics()
            lines += _shown(_extraction_lines(report))
        if "agente" in which:
            agent = _agent(conn, book, rules, llm, org, profile)
            if agent is not None:
                metrics["agente"], text = agent
                lines += _shown(text)
        if "conversacion" in which:
            talked = _conversations(conn, book, rules, llm, org, profile)
            if talked is not None:
                metrics["conversacion"], text = talked
                lines += _shown(text)
        if "coherencia" in which:
            if profile is None:
                lines += ["## Coherencia del plan", "", "Sin perfil confirmado: se salta.", ""]
            else:
                metrics["coherencia"], text = _coherence(conn, book, rules, profile, org)
                lines += _shown(text)
    saved = baseline.load()
    problems = baseline.compare(metrics, saved)
    lines += _shown(["## Frente a la línea base", "",
                     *([f"- {p}" for p in problems] or ["Sin empeoramientos."])])
    report_text = "\n".join(lines)
    if args.salida:
        args.salida.write_text(report_text + "\n", encoding="utf-8")
    if args.guardar_base:
        merged = dict((saved or {}).get("metricas", {})) | metrics
        baseline.save(merged, os.environ.get("LLM_MODEL_ID"), date.today().isoformat())
        print("Línea base guardada.", file=sys.stderr)
    return 1 if problems else 0


def _shown(lines: list[str]) -> list[str]:
    """Cada sección se imprime al terminar: una evaluación tarda minutos y no se pierde nada."""
    print("\n".join(lines), flush=True)
    return lines


def _profile(conn: Connection, org: UUID) -> UserProfile | None:
    profile_id = latest_profile_id(conn, org)
    try:
        keys = provider_from_env()
    except FileNotFoundError:
        return None
    return store.load(conn, keys, profile_id, org) if profile_id else None


def _extraction_lines(report: ExtractionReport) -> list[str]:
    m = report.metrics()
    lines = ["## Extracción de anuncios", "",
             f"Correctos {m['correctos']}/{m['con_valor']} campos con valor · falta {m['falta']} · "
             f"distinto {m['distinto']} · sobra {m['sobra']} · lotes de más "
             f"{m['lotes_de_mas']} · lotes de menos {m['lotes_de_menos']} · errores "
             f"{m['errores']}", "", "| Campo | Correcto | Falta | Distinto | Sobra |",
             "|---|---|---|---|---|"]
    for name, counted in sorted(report.by_field().items()):
        lines.append(f"| {name} | {counted['correcto']} | {counted['falta']} | "
                     f"{counted['distinto']} | {counted['sobra']} |")
    lines += ["", "Fallos:", ""]
    lines += [f"- {r.case} · {r.field}: {r.outcome} (esperado {r.expected!r}, sale {r.got!r})"
              for r in report.fields if r.outcome in ("falta", "distinto", "sobra")]
    lines += [f"- error: {e}" for e in report.errors]
    return [*lines, ""]


def _town(conn: Connection, org: UUID) -> str | None:
    """El municipio de una oferta confirmada y ubicada: las preguntas hablan de «{municipio}»."""
    return next((((o.extracted or {}).get("confirmed") or {}).get("fields", {})
                 .get("municipality", {}).get("value")
                 for o in list_private_offers(conn, org) if o.property_id is not None), None)


def _planned_offer(conn: Connection, book: ParamBook, rules: RuleBook, profile: UserProfile,
                   org: UUID) -> UUID | None:
    """La primera oferta con plan completo: la de la conversación en el plan de una oferta."""
    for candidate in search_candidates(conn, org):
        try:
            full_plan(conn, book, rules, profile, org, candidate.offer_id)
        except (PlanUnavailable, SearchUnavailable, LookupError, ValueError):
            continue
        return candidate.offer_id
    return None


def _conversations(conn: Connection, book: ParamBook, rules: RuleBook, llm: LLMClient, org: UUID,
                   profile: UserProfile | None) -> tuple[dict[str, int], list[str]] | None:
    town = _town(conn, org)
    if not town:
        return None
    offer = _planned_offer(conn, book, rules, profile, org) if profile else None
    chosen = [c for c in CONVERSATIONS if (profile is not None or not c.needs_profile)
              and (offer is not None or not c.offer)]

    def answer(conversation: Conversation, question: str,
               history: list[Message]) -> AgentAnswer:
        if conversation.offer and offer is not None:
            return ask_about_offer(conn, book, llm, org, offer, question, history, profile, rules)
        return ask_in_plan(conn, book, llm, org, question, history, profile,
                           rules if profile else None)

    results: list[TurnResult] = run_conversations(answer, chosen, town)
    m = conversation_metrics(results)
    lines = ["## Conversaciones con el asesor", "",
             f"{len(chosen)} conversaciones, {m['vueltas']} vueltas · herramientas "
             f"{m['herramientas']}/{m['vueltas']} · texto mostrado {m['mostrados']}/{m['vueltas']} "
             f"· a la primera {m['a_la_primera']}/{m['vueltas']} · cifra pedida "
             f"{m['cifra_pedida']}/{m['con_cifra_pedida']} · misma oferta "
             f"{m['misma_oferta']}/{m['con_misma_oferta']} · cifras fuera de marcadores "
             f"{m['cifras_fuera']} · contradicciones {m['contradicciones']}"]
    if len(chosen) < len(CONVERSATIONS):
        lines.append("Sin perfil confirmado o sin oferta con plan: se saltan las que lo necesitan.")
    lines.append("")
    current = None
    for t in results:
        if t.conversation != current:
            current = t.conversation
            lines += [f"### {current}", ""]
        r = t.result
        checks = [f"herramientas {'bien' if r.tools_ok else 'MAL'}",
                  f"{'mostrado' if r.shown else 'NO mostrado'}"
                  f"{' a la primera' if r.first_try else ''}"]
        if t.keys_ok is not None:
            checks.append(f"cifra pedida {'sí' if t.keys_ok else 'NO'}")
        if t.same_offer is not None:
            checks.append(f"misma oferta {'sí' if t.same_offer else 'NO'}")
        lines += [f"**{r.question}** · " + " · ".join(checks)
                  + f" · fallo: {r.failure or '—'} · {r.seconds} s", "", r.text, ""]
        lines += [f"- contradicción: {c}" for c in r.contradictions]
    return m, lines


def _agent(conn: Connection, book: ParamBook, rules: RuleBook, llm: LLMClient, org: UUID,
           profile: UserProfile | None) -> tuple[dict[str, int], list[str]] | None:
    town = _town(conn, org)
    if not town:
        return None
    cases = [c for c in CASES if profile is not None or not c.needs_profile]
    results: list[Result] = run_cases(
        lambda q: ask(conn, book, llm, org, q, profile, rules if profile else None), cases, town)
    lines = ["## Asesor", "", summary(results)]
    if len(cases) < len(CASES):
        lines.append("Sin perfil confirmado: se saltan búsqueda, alquiler y plan.")
    lines.append("")
    for r in results:
        lines += [f"### {r.question}", "",
                  f"herramientas {'bien' if r.tools_ok else 'MAL'} · "
                  f"{'mostrado' if r.shown else 'NO mostrado'}"
                  f"{' a la primera' if r.first_try else ''} · fallo: {r.failure or '—'} · "
                  f"{r.seconds} s", "", r.text, ""]
        lines += [f"- contradicción: {c}" for c in r.contradictions]
    metrics = {"preguntas": len(results), "herramientas": sum(r.tools_ok for r in results),
               "mostrados": sum(r.shown for r in results),
               "a_la_primera": sum(r.first_try for r in results),
               "cifras_fuera": sum(r.invented for r in results),
               "contradicciones": sum(len(r.contradictions) for r in results)}
    return metrics, lines


def _coherence(conn: Connection, book: ParamBook, rules: RuleBook, profile: UserProfile,
               org: UUID) -> tuple[dict[str, int], list[str]]:
    lines = ["## Coherencia del plan", ""]
    plans = incoherent = 0
    for candidate in search_candidates(conn, org):
        try:
            plan = full_plan(conn, book, rules, profile, org, candidate.offer_id)
        except (PlanUnavailable, SearchUnavailable, LookupError, ValueError):
            continue  # no se puede puntuar: lo dice la búsqueda
        plans += 1
        issues = check_plan(plan)
        incoherent += len(issues)
        lines += [f"- {candidate.offer_id.hex[:8]}: {i}" for i in issues]
    lines.insert(2, f"{plans} planes · {incoherent} incoherencias")
    lines.insert(3, "")
    return {"planes": plans, "incoherencias": incoherent}, [*lines, ""]


if __name__ == "__main__":
    sys.exit(main())
