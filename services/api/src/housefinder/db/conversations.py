"""SQL de las conversaciones con el asesor (ADR-0064). Aquí solo viajan bytes cifrados.

Con oferta, la del plan de esa oferta (`advisor_conversations`); sin ella (`offer_id` None), la
conversación general de «Mi plan» (`advisor_general_conversations`, ADR-0066).
"""

from __future__ import annotations

from uuid import UUID

import psycopg

from housefinder.db.profiles import SealedRow

_COLUMNS = "data_enc, dek_enc, key_id, enc_version"


def _where(offer_id: UUID | None) -> tuple[str, str]:
    """Tabla y condición de la conversación, con o sin oferta."""
    if offer_id is None:
        return "advisor_general_conversations", "org_id = %s AND client_id = %s"
    return "advisor_conversations", "org_id = %s AND client_id = %s AND offer_id = %s"


def _key(org_id: UUID, client_id: UUID, offer_id: UUID | None) -> tuple[UUID, ...]:
    return (org_id, client_id) if offer_id is None else (org_id, client_id, offer_id)


def get_conversation(conn: psycopg.Connection, org_id: UUID, client_id: UUID,
                     offer_id: UUID | None, days: int) -> SealedRow | None:
    """La conversación, si su última pregunta fue hace menos de `days` días."""
    table, where = _where(offer_id)
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM {table} WHERE {where} "
        "AND updated_at > now() - make_interval(days => %s)",
        (*_key(org_id, client_id, offer_id), days),
    ).fetchone()
    return SealedRow(bytes(row[0]), bytes(row[1]), row[2], row[3]) if row else None


def save_conversation(conn: psycopg.Connection, org_id: UUID, client_id: UUID,
                      offer_id: UUID | None, sealed: SealedRow) -> None:
    """Guarda la conversación entera y cuenta el plazo desde ahora."""
    table, _ = _where(offer_id)
    key = "org_id, client_id" if offer_id is None else "org_id, client_id, offer_id"
    values = ", ".join(["%s"] * (len(_key(org_id, client_id, offer_id)) + 4))
    conn.execute(
        f"""
        INSERT INTO {table} ({key}, {_COLUMNS}) VALUES ({values})
        ON CONFLICT ({key}) DO UPDATE SET
            data_enc = EXCLUDED.data_enc, dek_enc = EXCLUDED.dek_enc, key_id = EXCLUDED.key_id,
            enc_version = EXCLUDED.enc_version, updated_at = now()
        """,
        (*_key(org_id, client_id, offer_id), sealed.data_enc, sealed.dek_enc, sealed.key_id,
         sealed.version),
    )


def delete_conversation(conn: psycopg.Connection, org_id: UUID, client_id: UUID,
                        offer_id: UUID | None) -> bool:
    table, where = _where(offer_id)
    return conn.execute(f"DELETE FROM {table} WHERE {where}",
                        _key(org_id, client_id, offer_id)).rowcount > 0


def purge_expired(conn: psycopg.Connection, days: int) -> int:
    """Borra las de todas las organizaciones, con oferta o sin ella, cuya última pregunta tiene
    más de `days` días (lo hace el worker, sin Row-Level Security)."""
    return sum(
        conn.execute(
            f"DELETE FROM {table} WHERE updated_at <= now() - make_interval(days => %s)", (days,)
        ).rowcount
        for table in ("advisor_conversations", "advisor_general_conversations")
    )
