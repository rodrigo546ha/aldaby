"""Cola de trabajos en PostgreSQL (ADR-0010). Todo el SQL de la cola vive aquí.

Las horas son las de la base (`now()`), para que varios workers compartan reloj.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

LIVE = ("pendiente", "en_curso")
JOB_COLUMNS = "id, kind, payload, attempts, max_attempts, locked_at"


@dataclass(frozen=True)
class Job:
    id: int
    kind: str
    payload: dict[str, Any]
    attempts: int  # incluido el intento en curso
    max_attempts: int
    locked_at: datetime | None

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self.max_attempts


def enqueue(
    conn: psycopg.Connection,
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    run_after: datetime | None = None,
    max_attempts: int = 5,
    dedupe_key: str | None = None,
) -> int | None:
    """Encola un trabajo. Con `dedupe_key`, None si ya hay una copia viva con esa clave."""
    row = conn.execute(
        """
        INSERT INTO jobs (kind, payload, run_after, max_attempts, dedupe_key)
        VALUES (%s, %s, coalesce(%s, now()), %s, %s)
        ON CONFLICT (dedupe_key)
            WHERE dedupe_key IS NOT NULL AND status IN ('pendiente', 'en_curso')
            DO NOTHING
        RETURNING id
        """,
        (kind, Jsonb(payload or {}), run_after, max_attempts, dedupe_key),
    ).fetchone()
    return int(row[0]) if row else None


def claim(conn: psycopg.Connection, worker: str, kinds: list[str]) -> Job | None:
    """Reserva el trabajo listo más antiguo de los tipos indicados (SKIP LOCKED)."""
    row = conn.execute(
        f"""
        UPDATE jobs SET status = 'en_curso', attempts = attempts + 1, locked_at = now(),
                        locked_by = %s, updated_at = now()
        WHERE id = (
            SELECT id FROM jobs
            WHERE status = 'pendiente' AND run_after <= now() AND kind = ANY(%s)
            ORDER BY run_after, id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        RETURNING {JOB_COLUMNS}
        """,
        (worker, kinds),
    ).fetchone()
    return Job(*row) if row else None


def complete(
    conn: psycopg.Connection, job: Job, worker: str, result: dict[str, Any] | None
) -> None:
    with conn.transaction():
        _record_run(conn, job, worker, True, result, None)
        conn.execute(
            """
            UPDATE jobs SET status = 'hecho', locked_at = NULL, locked_by = NULL,
                            last_error = NULL, updated_at = now()
            WHERE id = %s
            """,
            (job.id,),
        )


def fail(
    conn: psycopg.Connection, job: Job, worker: str, error: str, retry_in: timedelta | None
) -> None:
    """Apunta el fallo. Con `retry_in`, vuelve a `pendiente`; sin él, queda `fallido`."""
    with conn.transaction():
        _record_run(conn, job, worker, False, None, error)
        conn.execute(
            """
            UPDATE jobs SET status = %s, run_after = now() + coalesce(%s, interval '0'),
                            locked_at = NULL, locked_by = NULL, last_error = %s,
                            updated_at = now()
            WHERE id = %s
            """,
            ("pendiente" if retry_in is not None else "fallido", retry_in, error, job.id),
        )


def requeue_stale(conn: psycopg.Connection, lease: timedelta) -> list[Job]:
    """Devuelve a la cola los trabajos con el préstamo caducado (worker caído).

    Cuenta como intento fallido; si se agotan los intentos, quedan `fallido`. Devuelve los que
    han quedado `fallido`, para avisar.
    """
    error = "préstamo caducado: el worker no terminó el trabajo"
    with conn.transaction():
        rows = conn.execute(
            """
            WITH stale AS (
                SELECT id, locked_at AS started_at, locked_by AS worker FROM jobs
                WHERE status = 'en_curso' AND locked_at < now() - %s
                FOR UPDATE SKIP LOCKED
            )
            UPDATE jobs SET
                status = CASE WHEN attempts >= max_attempts THEN 'fallido' ELSE 'pendiente' END,
                locked_at = NULL, locked_by = NULL, last_error = %s, updated_at = now()
            FROM stale WHERE jobs.id = stale.id
            RETURNING jobs.id, jobs.kind, jobs.payload, jobs.attempts, jobs.max_attempts,
                      stale.started_at, stale.worker, jobs.status
            """,
            (lease, error),
        ).fetchall()
        failed: list[Job] = []
        for *fields, worker, status in rows:
            job = Job(*fields)
            conn.execute(
                """
                INSERT INTO job_runs (job_id, attempt, worker, started_at, ok, error)
                VALUES (%s, %s, coalesce(%s, 'desconocido'), %s, false, %s)
                """,
                (job.id, job.attempts, worker, job.locked_at, error),
            )
            if status == "fallido":
                failed.append(job)
        return failed


def upsert_schedule(
    conn: psycopg.Connection,
    name: str,
    kind: str,
    payload: dict[str, Any],
    interval_seconds: int,
    first_run_at: datetime | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO job_schedules (name, kind, payload, interval_seconds, next_run_at)
        VALUES (%s, %s, %s, %s, coalesce(%s, now()))
        ON CONFLICT (name) DO UPDATE SET
            kind = EXCLUDED.kind, payload = EXCLUDED.payload,
            interval_seconds = EXCLUDED.interval_seconds, enabled = true
        """,
        (name, kind, Jsonb(payload), interval_seconds, first_run_at),
    )


def disable_schedules_except(conn: psycopg.Connection, names: list[str]) -> list[str]:
    """Desactiva las programaciones activas que no están en `names`; devuelve cuáles."""
    rows = conn.execute(
        """
        UPDATE job_schedules SET enabled = false
        WHERE enabled AND NOT (name = ANY(%s)) RETURNING name
        """,
        (names,),
    ).fetchall()
    return sorted(r[0] for r in rows)


def enqueue_due(conn: psycopg.Connection) -> list[str]:
    """Encola un trabajo por cada programación vencida y mueve su próxima hora.

    La próxima hora avanza en múltiplos del intervalo hasta quedar en el futuro, así que un
    worker parado varios días encola una sola copia (la programación es su `dedupe_key`).
    """
    with conn.transaction():
        due = conn.execute(
            """
            SELECT name, kind, payload FROM job_schedules
            WHERE enabled AND next_run_at <= now()
            FOR UPDATE SKIP LOCKED
            """
        ).fetchall()
        for name, kind, payload in due:
            enqueue(conn, kind, payload, dedupe_key=name)
            conn.execute(
                """
                UPDATE job_schedules SET
                    last_enqueued_at = now(),
                    next_run_at = next_run_at + make_interval(secs => interval_seconds * (
                        floor(extract(epoch FROM now() - next_run_at) / interval_seconds) + 1))
                WHERE name = %s
                """,
                (name,),
            )
        return [name for name, _, _ in due]


def _record_run(
    conn: psycopg.Connection,
    job: Job,
    worker: str,
    ok: bool,
    result: dict[str, Any] | None,
    error: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO job_runs (job_id, attempt, worker, started_at, ok, result, error)
        VALUES (%s, %s, %s, coalesce(%s, now()), %s, %s, %s)
        """,
        (job.id, job.attempts, worker, job.locked_at, ok,
         Jsonb(result) if result is not None else None, error),
    )
