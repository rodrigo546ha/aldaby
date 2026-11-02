"""SQL del nivel gratuito de los particulares (ADR-0040): tipo de organización y planes usados."""

from __future__ import annotations

from uuid import UUID

import psycopg


def organization_kind(conn: psycopg.Connection, org_id: UUID) -> str | None:
    row = conn.execute("SELECT kind FROM organizations WHERE id = %s", (org_id,)).fetchone()
    return row[0] if row else None


def used_plans(conn: psycopg.Connection, org_id: UUID) -> set[UUID]:
    rows = conn.execute("SELECT offer_id FROM plan_uses WHERE org_id = %s", (org_id,)).fetchall()
    return {r[0] for r in rows}


def record_plan_use(conn: psycopg.Connection, org_id: UUID, offer_id: UUID) -> None:
    conn.execute(
        "INSERT INTO plan_uses (org_id, offer_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (org_id, offer_id),
    )
