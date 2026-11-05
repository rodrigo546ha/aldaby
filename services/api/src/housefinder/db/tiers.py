"""SQL de los niveles (ADR-0041, ADR-0065): tipo de organización, planes usados y consultas al
asesor de hoy."""

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


# Consultas al asesor por día (ADR-0065). El día es el natural de Madrid.
_TODAY = "(now() AT TIME ZONE 'Europe/Madrid')::date"


def take_advisor_use(conn: psycopg.Connection, org_id: UUID, limit: int) -> bool:
    """Suma una consulta de hoy si no se ha llegado a `limit`. Comprobar y sumar es una sola
    sentencia: dos peticiones a la vez no pueden pasarse. Devuelve si se ha sumado."""
    if limit <= 0:
        return False
    row = conn.execute(
        f"""
        INSERT INTO advisor_uses (org_id, day, uses) VALUES (%s, {_TODAY}, 1)
        ON CONFLICT (org_id, day) DO UPDATE SET uses = advisor_uses.uses + 1
        WHERE advisor_uses.uses < %s
        RETURNING uses
        """,
        (org_id, limit),
    ).fetchone()
    return row is not None


def advisor_uses_today(conn: psycopg.Connection, org_id: UUID) -> int:
    row = conn.execute(
        f"SELECT uses FROM advisor_uses WHERE org_id = %s AND day = {_TODAY}", (org_id,)
    ).fetchone()
    return int(row[0]) if row else 0


def purge_old_advisor_uses(conn: psycopg.Connection) -> int:
    """Borra los contadores de días anteriores de todas las organizaciones (lo hace el worker)."""
    return conn.execute(f"DELETE FROM advisor_uses WHERE day < {_TODAY}").rowcount
