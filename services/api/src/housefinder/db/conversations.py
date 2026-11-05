"""SQL de las conversaciones con el asesor (ADR-0064). Aquí solo viajan bytes cifrados."""

from __future__ import annotations

from uuid import UUID

import psycopg

from housefinder.db.profiles import SealedRow


def get_conversation(conn: psycopg.Connection, org_id: UUID, client_id: UUID, offer_id: UUID,
                     days: int) -> SealedRow | None:
    """La conversación, si su última pregunta fue hace menos de `days` días."""
    row = conn.execute(
        """
        SELECT data_enc, dek_enc, key_id, enc_version FROM advisor_conversations
        WHERE org_id = %s AND client_id = %s AND offer_id = %s
          AND updated_at > now() - make_interval(days => %s)
        """,
        (org_id, client_id, offer_id, days),
    ).fetchone()
    return SealedRow(bytes(row[0]), bytes(row[1]), row[2], row[3]) if row else None


def save_conversation(conn: psycopg.Connection, org_id: UUID, client_id: UUID, offer_id: UUID,
                      sealed: SealedRow) -> None:
    """Guarda la conversación entera y cuenta el plazo desde ahora."""
    conn.execute(
        """
        INSERT INTO advisor_conversations (org_id, client_id, offer_id, data_enc, dek_enc, key_id,
                                           enc_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (org_id, client_id, offer_id) DO UPDATE SET
            data_enc = EXCLUDED.data_enc, dek_enc = EXCLUDED.dek_enc, key_id = EXCLUDED.key_id,
            enc_version = EXCLUDED.enc_version, updated_at = now()
        """,
        (org_id, client_id, offer_id, sealed.data_enc, sealed.dek_enc, sealed.key_id,
         sealed.version),
    )


def delete_conversation(conn: psycopg.Connection, org_id: UUID, client_id: UUID,
                        offer_id: UUID) -> bool:
    return conn.execute(
        "DELETE FROM advisor_conversations WHERE org_id = %s AND client_id = %s AND offer_id = %s",
        (org_id, client_id, offer_id),
    ).rowcount > 0


def purge_expired(conn: psycopg.Connection, days: int) -> int:
    """Borra las de todas las organizaciones cuya última pregunta tiene más de `days` días (lo
    hace el worker, sin Row-Level Security)."""
    return conn.execute(
        "DELETE FROM advisor_conversations WHERE updated_at <= now() - make_interval(days => %s)",
        (days,),
    ).rowcount
