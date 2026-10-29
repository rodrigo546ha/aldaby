"""Línea de órdenes de la cola (ADR-0010).

    python -m housefinder.jobs worker [--once] [--poll 5]
    python -m housefinder.jobs enqueue KIND [--payload JSON] [--dedupe-key CLAVE]
    python -m housefinder.jobs schedule NOMBRE KIND --every SEGUNDOS [--payload JSON]
    python -m housefinder.jobs status
"""

from __future__ import annotations

import argparse
import json
import logging

from housefinder.db.connection import connect
from housefinder.db.jobs import enqueue, upsert_schedule
from housefinder.db.migrate import database_url
from housefinder.jobs.handlers import build_handlers
from housefinder.jobs.worker import Worker


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m housefinder.jobs")
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("worker", help="ejecuta trabajos")
    w.add_argument("--once", action="store_true", help="una sola vuelta")
    w.add_argument("--poll", type=float, default=5.0, help="segundos de espera sin trabajos")
    e = sub.add_parser("enqueue", help="encola un trabajo")
    e.add_argument("kind")
    e.add_argument("--payload", default="{}")
    e.add_argument("--dedupe-key")
    s = sub.add_parser("schedule", help="crea o cambia una programación")
    s.add_argument("name")
    s.add_argument("kind")
    s.add_argument("--every", type=int, required=True, help="segundos entre ejecuciones")
    s.add_argument("--payload", default="{}")
    sub.add_parser("status", help="trabajos por estado y últimos fallos")
    args = parser.parse_args()

    url = database_url()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    handlers = build_handlers(url)

    if args.command == "worker":
        worker = Worker(url, handlers)
        if args.once:
            job = worker.run_once()
            print(f"Ejecutado el trabajo {job.id} ({job.kind})" if job else "Sin trabajos listos")
        else:
            worker.run_forever(args.poll)
        return 0

    with connect(url, autocommit=True) as conn:
        if args.command == "enqueue":
            if args.kind not in handlers:
                parser.error(f"Tipo desconocido: {args.kind} (hay {', '.join(sorted(handlers))})")
            job_id = enqueue(conn, args.kind, json.loads(args.payload),
                             dedupe_key=args.dedupe_key)
            print(f"Encolado el trabajo {job_id}" if job_id else "Ya había una copia viva")
        elif args.command == "schedule":
            if args.kind not in handlers:
                parser.error(f"Tipo desconocido: {args.kind}")
            upsert_schedule(conn, args.name, args.kind, json.loads(args.payload), args.every)
            print(f"Programación «{args.name}» guardada")
        else:
            counts = conn.execute(
                "SELECT status, count(*) FROM jobs GROUP BY status ORDER BY status"
            ).fetchall()
            if not counts:
                print("Sin trabajos en la cola")
            for status, count in counts:
                print(f"{status}: {count}")
            for job_id, kind, error in conn.execute(
                "SELECT id, kind, last_error FROM jobs WHERE status = 'fallido' "
                "ORDER BY updated_at DESC LIMIT 5"
            ):
                print(f"  fallido {job_id} ({kind}): {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
