"""SQL de los clientes de un profesional (F7.2, ADR-0029). El nombre viaja cifrado."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import psycopg

from housefinder.db.profiles import SealedRow


@dataclass(frozen=True)
class ClientRow:
    id: UUID
    sealed: SealedRow
    has_profile: bool


def insert_client(conn: psycopg.Connection, client_id: UUID, org_id: UUID,
                  sealed: SealedRow) -> None:
    conn.execute(
        "INSERT INTO clients (id, org_id, name_enc, dek_enc, key_id, enc_version) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (client_id, org_id, sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version),
    )


def list_clients(conn: psycopg.Connection, org_id: UUID) -> list[ClientRow]:
    """Los clientes de la organización, en el orden en que se dieron de alta."""
    rows = conn.execute(
        """
        SELECT c.id, c.name_enc, c.dek_enc, c.key_id, c.enc_version,
               EXISTS (SELECT 1 FROM user_profiles p WHERE p.client_id = c.id)
        FROM clients c WHERE c.org_id = %s ORDER BY c.created_at
        """,
        (org_id,),
    ).fetchall()
    return [ClientRow(r[0], SealedRow(bytes(r[1]), bytes(r[2]), r[3], r[4]), r[5])
            for r in rows]


def client_in_org(conn: psycopg.Connection, client_id: UUID, org_id: UUID) -> bool:
    row = conn.execute("SELECT 1 FROM clients WHERE id = %s AND org_id = %s",
                       (client_id, org_id)).fetchone()
    return row is not None


def delete_client(conn: psycopg.Connection, client_id: UUID, org_id: UUID) -> bool:
    """Borra el cliente con sus perfiles y su entrevista (ON DELETE CASCADE)."""
    row = conn.execute("DELETE FROM clients WHERE id = %s AND org_id = %s RETURNING id",
                       (client_id, org_id)).fetchone()
    return row is not None


def client_ids(conn: psycopg.Connection, org_id: UUID) -> list[UUID]:
    rows = conn.execute("SELECT id FROM clients WHERE org_id = %s ORDER BY created_at",
                        (org_id,)).fetchall()
    return [r[0] for r in rows]
