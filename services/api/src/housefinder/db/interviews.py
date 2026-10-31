"""SQL de las entrevistas de perfil (ADR-0020). Aquí solo viajan bytes cifrados."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import psycopg

from housefinder.db.profiles import SealedRow


@dataclass(frozen=True)
class InterviewRow:
    sealed: SealedRow
    status: Literal["en_curso", "confirmada"]
    profile_id: UUID | None


def insert_interview(
    conn: psycopg.Connection, interview_id: UUID, org_id: UUID, owner_id: str, sealed: SealedRow
) -> None:
    conn.execute(
        """
        INSERT INTO profile_interviews (id, org_id, owner_id, data_enc, dek_enc, key_id,
                                        enc_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (interview_id, org_id, owner_id, sealed.data_enc, sealed.dek_enc, sealed.key_id,
         sealed.version),
    )


def update_interview(
    conn: psycopg.Connection, interview_id: UUID, org_id: UUID, sealed: SealedRow
) -> None:
    conn.execute(
        """
        UPDATE profile_interviews SET data_enc = %s, dek_enc = %s, key_id = %s, enc_version = %s,
                                      updated_at = now()
        WHERE id = %s AND org_id = %s AND status = 'en_curso'
        """,
        (sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version, interview_id, org_id),
    )


def get_interview(
    conn: psycopg.Connection, interview_id: UUID, org_id: UUID
) -> InterviewRow | None:
    """La entrevista solo se devuelve a su organización."""
    row = conn.execute(
        """
        SELECT data_enc, dek_enc, key_id, enc_version, status, profile_id FROM profile_interviews
        WHERE id = %s AND org_id = %s
        """,
        (interview_id, org_id),
    ).fetchone()
    if row is None:
        return None
    return InterviewRow(SealedRow(bytes(row[0]), bytes(row[1]), row[2], row[3]), row[4], row[5])


def latest_open_interview(conn: psycopg.Connection, org_id: UUID) -> UUID | None:
    row = conn.execute(
        """
        SELECT id FROM profile_interviews WHERE org_id = %s AND status = 'en_curso'
        ORDER BY updated_at DESC LIMIT 1
        """,
        (org_id,),
    ).fetchone()
    return row[0] if row else None


def mark_confirmed(
    conn: psycopg.Connection, interview_id: UUID, org_id: UUID, profile_id: UUID
) -> None:
    conn.execute(
        """
        UPDATE profile_interviews SET status = 'confirmada', profile_id = %s, updated_at = now()
        WHERE id = %s AND org_id = %s
        """,
        (profile_id, interview_id, org_id),
    )


def delete_interview(conn: psycopg.Connection, interview_id: UUID, org_id: UUID) -> bool:
    row = conn.execute(
        "DELETE FROM profile_interviews WHERE id = %s AND org_id = %s RETURNING id",
        (interview_id, org_id),
    ).fetchone()
    return row is not None
