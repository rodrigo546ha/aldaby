"""SQL de los feeds de agencias (ADR-0038). La URL solo viaja cifrada."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from housefinder.db.profiles import SealedRow


@dataclass(frozen=True)
class FeedRow:
    id: UUID
    org_id: UUID
    agency_name: str
    scope: str  # 'organizacion' | 'todos'
    consent_on: date
    consent_ref: str
    active: bool
    sealed: SealedRow


_COLUMNS = ("id, org_id, agency_name, scope, consent_on, consent_ref, active, "
            "url_enc, dek_enc, key_id, enc_version")


def insert_feed(conn: psycopg.Connection, feed_id: UUID, org_id: UUID, agency_name: str,
                scope: str, consent_on: date, consent_ref: str, sealed: SealedRow) -> None:
    conn.execute(
        """
        INSERT INTO agency_feeds (id, org_id, agency_name, url_enc, dek_enc, key_id, enc_version,
                                  scope, consent_on, consent_ref)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (feed_id, org_id, agency_name, sealed.data_enc, sealed.dek_enc, sealed.key_id,
         sealed.version, scope, consent_on, consent_ref),
    )


def list_feeds(conn: psycopg.Connection, only_active: bool = True) -> list[FeedRow]:
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM agency_feeds WHERE active OR NOT %s ORDER BY created_at",
        (only_active,),
    ).fetchall()
    return [FeedRow(*r[:7], SealedRow(bytes(r[7]), bytes(r[8]), r[9], r[10])) for r in rows]


def deactivate_feed(conn: psycopg.Connection, feed_id: UUID) -> bool:
    row = conn.execute(
        "UPDATE agency_feeds SET active = false WHERE id = %s RETURNING id", (feed_id,)
    ).fetchone()
    return row is not None


def record_run(conn: psycopg.Connection, feed_id: UUID, report: dict[str, Any]) -> None:
    conn.execute(
        "UPDATE agency_feeds SET last_run_at = now(), last_report = %s WHERE id = %s",
        (Jsonb(report), feed_id),
    )


def find_organization(conn: psycopg.Connection, name: str) -> UUID | None:
    """La primera organización con ese nombre (las crea el alta de cuentas, ADR-0028)."""
    row = conn.execute(
        "SELECT id FROM organizations WHERE name = %s ORDER BY created_at LIMIT 1", (name,)
    ).fetchone()
    return row[0] if row else None


@dataclass(frozen=True)
class FeedStatus:
    id: UUID
    agency_name: str
    scope: str
    consent_on: date
    consent_ref: str
    created_at: datetime
    last_run_at: datetime | None
    last_report: dict[str, Any] | None


def org_feeds(conn: psycopg.Connection, org_id: UUID) -> list[FeedStatus]:
    """Los feeds activos de una organización con su último informe; nunca la URL."""
    rows = conn.execute(
        """
        SELECT id, agency_name, scope, consent_on, consent_ref, created_at, last_run_at,
               last_report
        FROM agency_feeds WHERE org_id = %s AND active ORDER BY created_at
        """,
        (org_id,),
    ).fetchall()
    return [FeedStatus(*r) for r in rows]


def deactivate_org_feed(conn: psycopg.Connection, feed_id: UUID, org_id: UUID) -> bool:
    row = conn.execute(
        "UPDATE agency_feeds SET active = false WHERE id = %s AND org_id = %s AND active "
        "RETURNING id",
        (feed_id, org_id),
    ).fetchone()
    return row is not None
