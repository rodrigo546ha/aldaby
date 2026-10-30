"""Vigilancia del BOE y del BOCM como trabajos (F2.6, ADR-0010).

Lee los boletines que aún no se han leído, aplica los filtros de vigilancia y abre una tarea
de revisión por publicación. Repetir una ejecución no duplica tareas ni vuelve a descargar
boletines leídos.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

import httpx

from housefinder.db.connection import connect
from housefinder.db.review_tasks import NewTask, mark_issue_read, open_task, read_issues
from housefinder.ingestion.bocm import (
    BocmItem,
    Pace,
    bulletin_key,
    fetch_bulletin_items,
    fetch_bulletins,
)
from housefinder.ingestion.boe import fetch_sumario, iter_items
from housefinder.watch.rules import Publication, WatchRules, load_rules, match


def boe_publications(payload: Any, day: date) -> list[Publication]:
    return [
        Publication("boe", i.identifier, i.title, i.url_html or i.url_pdf or "", day, i.section,
                    department=i.department)
        for i in iter_items(payload, day)
    ]


def bocm_publications(items: Iterable[BocmItem]) -> list[Publication]:
    return [
        Publication("bocm", i.identifier, i.title, i.url, i.published_on, i.section,
                    part=i.part, department=i.body)
        for i in items
    ]


def tasks_for(publications: Iterable[Publication], rules: WatchRules) -> list[NewTask]:
    tasks: list[NewTask] = []
    for pub in publications:
        found = match(pub, rules)
        if found is None:
            continue
        tasks.append(NewTask(pub.source, pub.identifier, pub.published_on, pub.title, pub.url,
                             pub.section, pub.department or pub.part, found.tags,
                             found.rule_ids, found.notes))
    return tasks


def watch_boe(
    conninfo: str, client: httpx.Client, today: date, days: int = 7,
    rules: WatchRules | None = None,
) -> dict[str, Any]:
    """Sumarios del BOE de los últimos `days` días que no se hayan leído."""
    rules = rules or load_rules()
    read = opened = 0
    with connect(conninfo, autocommit=True) as conn:
        done = read_issues(conn, "boe")
        for offset in range(days):
            day = today - timedelta(days=offset)
            if day.isoformat() in done:
                continue
            payload = fetch_sumario(day, client)
            if payload is None:
                if day < today:  # domingo o festivo; hoy puede no haber salido aún
                    mark_issue_read(conn, "boe", day.isoformat(), 0, 0)
                continue
            pubs = boe_publications(payload, day)
            new = sum(open_task(conn, t) is not None for t in tasks_for(pubs, rules))
            mark_issue_read(conn, "boe", day.isoformat(), len(pubs), new)
            read, opened = read + 1, opened + new
    return {"days_read": read, "tasks_opened": opened}


def watch_bocm(
    conninfo: str, client: httpx.Client, rules: WatchRules | None = None,
    pace: Pace | None = None,
) -> dict[str, Any]:
    """Boletines del BOCM del RSS de sumarios que no se hayan leído (10 s entre peticiones)."""
    rules = rules or load_rules()
    pace = pace or Pace()
    read = opened = 0
    with connect(conninfo, autocommit=True) as conn:
        done = read_issues(conn, "bocm")
        for bulletin in fetch_bulletins(client, pace):
            key = bulletin_key(bulletin)
            if key in done:
                continue
            pubs = bocm_publications(fetch_bulletin_items(client, bulletin, pace))
            new = sum(open_task(conn, t) is not None for t in tasks_for(pubs, rules))
            mark_issue_read(conn, "bocm", key, len(pubs), new)
            read, opened = read + 1, opened + new
    return {"bulletins_read": read, "tasks_opened": opened}
