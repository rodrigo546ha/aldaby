"""Tareas de revisión de la vigilancia del BOE y del BOCM (F2.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import psycopg

STATUSES = ("abierta", "descartada", "aplicada")


@dataclass(frozen=True)
class NewTask:
    source: str
    external_id: str
    published_on: date
    title: str
    url: str
    section: str
    department: str
    tags: tuple[str, ...]
    rule_ids: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class TaskRow:
    id: int
    source: str
    external_id: str
    published_on: date
    title: str
    url: str
    tags: list[str]
    rule_ids: list[str]
    notes: list[str]
    status: str


def open_task(conn: psycopg.Connection, task: NewTask) -> int | None:
    """Abre la tarea. None si esa publicación ya tenía una."""
    row = conn.execute(
        """
        INSERT INTO review_tasks (source, external_id, published_on, title, url, section,
                                  department, tags, rule_ids, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source, external_id) DO NOTHING
        RETURNING id
        """,
        (task.source, task.external_id, task.published_on, task.title, task.url, task.section,
         task.department, list(task.tags), list(task.rule_ids), list(task.notes)),
    ).fetchone()
    return int(row[0]) if row else None


def read_issues(conn: psycopg.Connection, source: str) -> set[str]:
    rows = conn.execute("SELECT issue_id FROM watch_issues WHERE source = %s", (source,))
    return {r[0] for r in rows}


def mark_issue_read(
    conn: psycopg.Connection, source: str, issue_id: str, items: int, tasks: int
) -> None:
    conn.execute(
        """
        INSERT INTO watch_issues (source, issue_id, items, tasks) VALUES (%s, %s, %s, %s)
        ON CONFLICT (source, issue_id) DO UPDATE SET
            read_at = now(), items = EXCLUDED.items, tasks = EXCLUDED.tasks
        """,
        (source, issue_id, items, tasks),
    )


def list_tasks(conn: psycopg.Connection, status: str = "abierta") -> list[TaskRow]:
    rows = conn.execute(
        """
        SELECT id, source, external_id, published_on, title, url, tags, rule_ids, notes, status
        FROM review_tasks WHERE status = %s ORDER BY published_on, id
        """,
        (status,),
    ).fetchall()
    return [TaskRow(*r) for r in rows]


def decide(
    conn: psycopg.Connection, task_id: int, status: str, decided_by: str, note: str | None
) -> bool:
    """Cierra una tarea. False si no existe."""
    if status not in STATUSES[1:]:
        raise ValueError(f"Estado de cierre no válido: {status!r} (descartada o aplicada)")
    row = conn.execute(
        """
        UPDATE review_tasks SET status = %s, decided_by = %s, decided_at = now(),
                                decision_note = %s
        WHERE id = %s RETURNING id
        """,
        (status, decided_by, note, task_id),
    ).fetchone()
    return row is not None
