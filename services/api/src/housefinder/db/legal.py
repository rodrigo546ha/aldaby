"""SQL de la aceptación de los textos legales (ADR-0039)."""

from __future__ import annotations

from uuid import UUID

import psycopg


def accepted_versions(conn: psycopg.Connection, account_id: UUID) -> dict[str, int]:
    """La versión más alta aceptada de cada documento."""
    rows = conn.execute(
        "SELECT document, max(version) FROM legal_acceptances WHERE account_id = %s "
        "GROUP BY document",
        (account_id,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def record_acceptance(conn: psycopg.Connection, account_id: UUID, document: str,
                      version: int) -> None:
    conn.execute(
        "INSERT INTO legal_acceptances (account_id, document, version) VALUES (%s, %s, %s) "
        "ON CONFLICT DO NOTHING",
        (account_id, document, version),
    )
