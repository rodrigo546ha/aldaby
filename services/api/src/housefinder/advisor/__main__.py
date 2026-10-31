"""Pregunta al agente desde la terminal, para probarlo en desarrollo (ADR-0019).

    python -m housefinder.advisor preguntar "¿Cuál de mis ofertas se alquilaría mejor?"
    python -m housefinder.advisor evaluar --salida banco.md   # banco de preguntas (F6.0)

Usa el LLM de `.env` (ADR-0014) y las ofertas de la organización local de desarrollo. Las cifras
salen como [clave = valor unidad]: la web las formatea con `<FigureView>`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

from housefinder.advisor.evaluation import CASES, run_cases, summary
from housefinder.advisor.tools import ask
from housefinder.agent.llm import LLMClient, llm_from_env
from housefinder.agent.references import FigureSegment, OfferSegment, Segment
from housefinder.crypto.envelope import provider_from_env
from housefinder.db.connection import Connection, connect
from housefinder.db.offers import list_private_offers
from housefinder.db.profiles import get_or_create_organization, latest_profile_id
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.profiles import store
from housefinder.profiles.model import UserProfile
from housefinder.regulation.rules import RuleBook, default_rules_dir

DEV_ORG = "Desarrollo local"  # la misma que usa la API hasta la autenticación (G8)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.advisor")
    sub = parser.add_subparsers(dest="command", required=True)
    question = sub.add_parser("preguntar", help="una pregunta sobre tus ofertas")
    question.add_argument("texto")
    bench = sub.add_parser("evaluar", help="banco de preguntas con el modelo de .env")
    bench.add_argument("--salida", type=Path, help="informe en Markdown con cada texto")
    args = parser.parse_args()

    llm = llm_from_env()
    book = ParamBook.from_dir(default_params_dir())
    with connect() as conn:
        org = get_or_create_organization(conn, DEV_ORG, "particular")
        conn.commit()
        if args.command == "evaluar":
            return _evaluate(conn, book, llm, org, args.salida)
        profile, rules = _profile(conn, org)
        answer = ask(conn, book, llm, org, args.texto, profile, rules)
    for step in answer.steps:
        print(f"· {step.tool}: {'bien' if step.ok else 'error'}", file=sys.stderr)
    for number, problems in enumerate(answer.rejected, 1):
        print(f"· texto rechazado {number}: {' | '.join(problems)}", file=sys.stderr)
    if answer.segments is None:
        print(f"Sin explicación ({answer.failure}"
              f"{': ' + answer.detail if answer.detail else ''}). Cifras obtenidas:")
        for key, figure in answer.figures.items():
            print(f"  [{key} = {figure.value} {figure.unit}]")
    else:
        print("".join(_shown(s) for s in answer.segments))
    for note in answer.notes:
        print(f"  aviso: {note}")
    return 0 if answer.failure is None else 1


def _evaluate(conn: Connection, book: ParamBook, llm: LLMClient, org: UUID,
              output: Path | None) -> int:
    town = next((((o.extracted or {}).get("confirmed") or {}).get("fields", {})
                 .get("municipality", {}).get("value")
                 for o in list_private_offers(conn, org) if o.property_id is not None), None)
    if not town:
        print("Hace falta una oferta confirmada, ubicada y con municipio.", file=sys.stderr)
        return 1
    results = run_cases(lambda q: ask(conn, book, llm, org, q), CASES, town)
    model = os.environ.get("LLM_MODEL_ID")
    lines = [f"# Banco del agente con {model}", "", summary(results), ""]
    for r in results:
        lines += [f"## {r.question}", "",
                  f"herramientas {'bien' if r.tools_ok else 'MAL'} · "
                  f"{'mostrado' if r.shown else 'NO mostrado'}"
                  f"{' a la primera' if r.first_try else ''} · fallo: {r.failure or '—'} · "
                  f"{r.seconds} s", "", r.text, ""]
    report = "\n".join(lines)
    print(report)
    if output:
        output.write_text(report, encoding="utf-8")
    return 0


def _profile(conn: Connection, org: UUID) -> tuple[UserProfile | None, RuleBook | None]:
    """El perfil confirmado, si hay clave maestra y perfil: sin él, buscar_ofertas lo dice."""
    profile_id = latest_profile_id(conn, org)
    try:
        keys = provider_from_env()
    except FileNotFoundError:
        return None, None
    if profile_id is None:
        return None, None
    return store.load(conn, keys, profile_id, org), RuleBook.from_dir(default_rules_dir())


def _shown(segment: Segment) -> str:
    if isinstance(segment, FigureSegment):
        part = "" if segment.part == "value" else ":" + segment.part
        return f"[{segment.figure.key}{part} = {_part(segment)} {segment.figure.unit}]"
    if isinstance(segment, OfferSegment):
        return f"[oferta {segment.label}]"
    return segment.text


def _part(segment: FigureSegment) -> str:
    f = segment.figure
    return {"value": f"{f.value}", "low": f"{f.low}", "high": f"{f.high}",
            "range": f"{f.value} ({f.low}–{f.high})"}[segment.part]


if __name__ == "__main__":
    raise SystemExit(main())
