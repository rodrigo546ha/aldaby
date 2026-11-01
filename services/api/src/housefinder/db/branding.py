"""SQL de la marca del profesional (F7.3, ADR-0030)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import psycopg


@dataclass(frozen=True)
class BrandingRow:
    display_name: str | None
    contact: str | None
    color: str | None
    intro: str | None
    logo_png: bytes | None


def get_branding(conn: psycopg.Connection, org_id: UUID) -> BrandingRow | None:
    row = conn.execute(
        "SELECT display_name, contact, color, intro, logo_png FROM org_branding WHERE org_id = %s",
        (org_id,),
    ).fetchone()
    if row is None:
        return None
    return BrandingRow(row[0], row[1], row[2], row[3], bytes(row[4]) if row[4] else None)


def save_texts(conn: psycopg.Connection, org_id: UUID, display_name: str | None,
               contact: str | None, color: str | None, intro: str | None) -> None:
    conn.execute(
        """
        INSERT INTO org_branding (org_id, display_name, contact, color, intro)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (org_id) DO UPDATE SET display_name = EXCLUDED.display_name,
            contact = EXCLUDED.contact, color = EXCLUDED.color, intro = EXCLUDED.intro,
            updated_at = now()
        """,
        (org_id, display_name, contact, color, intro),
    )


def save_logo(conn: psycopg.Connection, org_id: UUID, logo_png: bytes | None) -> None:
    conn.execute(
        """
        INSERT INTO org_branding (org_id, logo_png) VALUES (%s, %s)
        ON CONFLICT (org_id) DO UPDATE SET logo_png = EXCLUDED.logo_png, updated_at = now()
        """,
        (org_id, logo_png),
    )
