"""SQL de la analítica sin cookies (ADR-0042): recuentos de visitas y pasos del embudo."""

from __future__ import annotations

from datetime import date

import psycopg


def count_view(conn: psycopg.Connection, day: date, path: str, referrer: str,
               source: str) -> None:
    conn.execute(
        """
        INSERT INTO page_views (day, path, referrer, source, views) VALUES (%s, %s, %s, %s, 1)
        ON CONFLICT (day, path, referrer, source) DO UPDATE SET views = page_views.views + 1
        """,
        (day, path, referrer, source),
    )


def views(conn: psycopg.Connection, start: date, end: date,
          path: str | None = None) -> int:
    row = conn.execute(
        "SELECT coalesce(sum(views), 0) FROM page_views WHERE day BETWEEN %s AND %s "
        "AND (%s::text IS NULL OR path = %s)",
        (start, end, path, path),
    ).fetchone()
    return int(row[0]) if row else 0


def top_referrers(conn: psycopg.Connection, start: date, end: date,
                  limit: int = 10) -> list[tuple[str, int]]:
    rows = conn.execute(
        """
        SELECT CASE WHEN source <> '' THEN source || ' (utm)' WHEN referrer <> '' THEN referrer
                    ELSE 'directo' END, sum(views)
        FROM page_views WHERE day BETWEEN %s AND %s AND path = '/'
        GROUP BY 1 ORDER BY 2 DESC LIMIT %s
        """,
        (start, end, limit),
    ).fetchall()
    return [(r[0], int(r[1])) for r in rows]


def funnel_counts(conn: psycopg.Connection, start: date, end: date) -> dict[str, int]:
    """Pasos del embudo de particulares entre dos días (incluidos), hora de Madrid."""
    row = conn.execute(
        """
        WITH bounds AS (
            SELECT (%(start)s::date)::timestamp AT TIME ZONE 'Europe/Madrid' AS since,
                   ((%(end)s::date) + 1)::timestamp AT TIME ZONE 'Europe/Madrid' AS until
        ),
        particulares AS (
            SELECT a.org_id FROM accounts a, bounds b
            WHERE a.role = 'particular' AND a.created_at >= b.since AND a.created_at < b.until
        )
        SELECT
            (SELECT count(*) FROM waitlist w, bounds b
             WHERE w.created_at >= b.since AND w.created_at < b.until),
            (SELECT count(*) FROM waitlist w, bounds b
             WHERE w.kind = 'particular' AND w.created_at >= b.since AND w.created_at < b.until),
            (SELECT count(*) FROM particulares),
            (SELECT count(DISTINCT p.org_id) FROM user_profiles p
             WHERE p.org_id IN (SELECT org_id FROM particulares)),
            (SELECT count(DISTINCT u.org_id) FROM plan_uses u
             WHERE u.org_id IN (SELECT org_id FROM particulares))
        """,
        {"start": start, "end": end},
    ).fetchone()
    assert row is not None
    keys = ("waitlist", "waitlist_particulares", "accounts", "profiles", "plans")
    return dict(zip(keys, (int(v) for v in row), strict=True))
