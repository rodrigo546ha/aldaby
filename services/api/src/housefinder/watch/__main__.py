"""Tareas de revisión de la vigilancia (F2.6).

    python -m housefinder.watch tareas [--estado abierta]
    python -m housefinder.watch decidir ID descartada|aplicada --por NOMBRE [--nota TEXTO]
    python -m housefinder.watch leer boe|bocm [--dias 7]
"""

from __future__ import annotations

import argparse
from datetime import date

import httpx

from housefinder.db.connection import connect
from housefinder.db.migrate import database_url
from housefinder.db.review_tasks import STATUSES, decide, list_tasks
from housefinder.ingestion.ine_sections import USER_AGENT
from housefinder.watch.run import watch_bocm, watch_boe


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.watch")
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("tareas", help="lista las tareas de revisión")
    t.add_argument("--estado", default="abierta", choices=STATUSES)
    d = sub.add_parser("decidir", help="cierra una tarea")
    d.add_argument("id", type=int)
    d.add_argument("estado", choices=STATUSES[1:])
    d.add_argument("--por", required=True, help="quién decide")
    d.add_argument("--nota")
    r = sub.add_parser("leer", help="lee los boletines nuevos ahora")
    r.add_argument("boletin", choices=["boe", "bocm"])
    r.add_argument("--dias", type=int, default=7)
    args = parser.parse_args()
    url = database_url()

    if args.command == "leer":
        with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
            result = (watch_boe(url, client, date.today(), args.dias) if args.boletin == "boe"
                      else watch_bocm(url, client))
        print(result)
        return 0

    with connect(url, autocommit=True) as conn:
        if args.command == "tareas":
            tasks = list_tasks(conn, args.estado)
            if not tasks:
                print(f"Sin tareas {args.estado}s")
            for task in tasks:
                print(f"[{task.id}] {task.published_on} {task.source.upper()} {task.external_id} "
                      f"({', '.join(task.tags)})\n    {task.title}\n    {task.url}")
                for note in task.notes:
                    print(f"    Nota: {note}")
                if task.rule_ids:
                    print(f"    Reglas: {', '.join(task.rule_ids)}")
        elif not decide(conn, args.id, args.estado, args.por, args.nota):
            print(f"No existe la tarea {args.id}")
            return 1
        else:
            print(f"Tarea {args.id}: {args.estado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
