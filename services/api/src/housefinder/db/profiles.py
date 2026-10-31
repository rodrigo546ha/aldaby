"""SQL de organizaciones y perfiles (ADR-0011). Aquí solo viajan bytes cifrados."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import psycopg


@dataclass(frozen=True)
class SealedRow:
    data_enc: bytes
    dek_enc: bytes
    key_id: str
    version: int


def create_organization(conn: psycopg.Connection, name: str, kind: str) -> UUID:
    row = conn.execute(
        "INSERT INTO organizations (name, kind) VALUES (%s, %s) RETURNING id", (name, kind)
    ).fetchone()
    assert_row(row)
    return row[0]


def get_or_create_organization(conn: psycopg.Connection, name: str, kind: str) -> UUID:
    """La primera organización con ese nombre, o una nueva (organización local antes de G8)."""
    conn.execute("SELECT pg_advisory_xact_lock(hashtext('organizations:' || %s))", (name,))
    row = conn.execute(
        "SELECT id FROM organizations WHERE name = %s ORDER BY created_at LIMIT 1", (name,)
    ).fetchone()
    return row[0] if row else create_organization(conn, name, kind)


def insert_profile(
    conn: psycopg.Connection, profile_id: UUID, org_id: UUID, owner_id: str, sealed: SealedRow
) -> None:
    conn.execute(
        """
        INSERT INTO user_profiles (id, org_id, owner_id, data_enc, dek_enc, key_id, enc_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (profile_id, org_id, owner_id, sealed.data_enc, sealed.dek_enc, sealed.key_id,
         sealed.version),
    )


def update_profile(
    conn: psycopg.Connection, profile_id: UUID, org_id: UUID, sealed: SealedRow
) -> bool:
    row = conn.execute(
        """
        UPDATE user_profiles SET data_enc = %s, dek_enc = %s, key_id = %s, enc_version = %s,
                                 updated_at = now()
        WHERE id = %s AND org_id = %s RETURNING id
        """,
        (sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version, profile_id, org_id),
    ).fetchone()
    return row is not None


def get_profile(conn: psycopg.Connection, profile_id: UUID, org_id: UUID) -> SealedRow | None:
    """El perfil solo se devuelve a su organización."""
    row = conn.execute(
        """
        SELECT data_enc, dek_enc, key_id, enc_version FROM user_profiles
        WHERE id = %s AND org_id = %s
        """,
        (profile_id, org_id),
    ).fetchone()
    return SealedRow(bytes(row[0]), bytes(row[1]), row[2], row[3]) if row else None


def profiles_with_old_key(
    conn: psycopg.Connection, current_key_id: str
) -> list[tuple[UUID, UUID, SealedRow]]:
    rows = conn.execute(
        """
        SELECT id, org_id, data_enc, dek_enc, key_id, enc_version FROM user_profiles
        WHERE key_id <> %s
        """,
        (current_key_id,),
    ).fetchall()
    return [(r[0], r[1], SealedRow(bytes(r[2]), bytes(r[3]), r[4], r[5])) for r in rows]


def replace_wrapped_key(
    conn: psycopg.Connection, profile_id: UUID, old_key_id: str, dek_enc: bytes, key_id: str
) -> None:
    conn.execute(
        "UPDATE user_profiles SET dek_enc = %s, key_id = %s WHERE id = %s AND key_id = %s",
        (dek_enc, key_id, profile_id, old_key_id),
    )


def assert_row(row: object) -> None:
    if row is None:
        raise RuntimeError("La inserción no devolvió fila")


def latest_profile_id(conn: psycopg.Connection, org_id: UUID) -> UUID | None:
    """El perfil más reciente de la organización (hasta la autenticación, uno por organización)."""
    row = conn.execute(
        "SELECT id FROM user_profiles WHERE org_id = %s ORDER BY updated_at DESC LIMIT 1",
        (org_id,),
    ).fetchone()
    return row[0] if row else None
