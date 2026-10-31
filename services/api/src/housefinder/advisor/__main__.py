"""Pregunta al agente desde la terminal, para probarlo en desarrollo (ADR-0019).

    python -m housefinder.advisor preguntar "¿Cuál de mis ofertas se alquilaría mejor?"

Usa el LLM de `.env` (ADR-0014) y las ofertas de la organización local de desarrollo. Las cifras
salen como [clave = valor unidad]: la web las formatea con `<FigureView>`.
"""

from __future__ import annotations

import argparse
import sys

from housefinder.advisor.tools import ask
from housefinder.agent.llm import llm_from_env
from housefinder.agent.references import FigureSegment
from housefinder.db.connection import connect
from housefinder.db.profiles import get_or_create_organization
from housefinder.params.book import ParamBook, default_params_dir

DEV_ORG = "Desarrollo local"  # la misma que usa la API hasta la autenticación (G8)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.advisor")
    sub = parser.add_subparsers(dest="command", required=True)
    question = sub.add_parser("preguntar", help="una pregunta sobre tus ofertas")
    question.add_argument("texto")
    args = parser.parse_args()

    llm = llm_from_env()
    book = ParamBook.from_dir(default_params_dir())
    with connect() as conn:
        org = get_or_create_organization(conn, DEV_ORG, "particular")
        conn.commit()
        answer = ask(conn, book, llm, org, args.texto)
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
        print("".join(
            f"[{s.figure.key}{'' if s.part == 'value' else ':' + s.part} = "
            f"{_part(s)} {s.figure.unit}]" if isinstance(s, FigureSegment) else s.text
            for s in answer.segments))
    for note in answer.notes:
        print(f"  aviso: {note}")
    return 0 if answer.failure is None else 1


def _part(segment: FigureSegment) -> str:
    f = segment.figure
    return {"value": f"{f.value}", "low": f"{f.low}", "high": f"{f.high}",
            "range": f"{f.value} ({f.low}–{f.high})"}[segment.part]


if __name__ == "__main__":
    raise SystemExit(main())
