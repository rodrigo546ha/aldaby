"""Marca del profesional: textos, color con contraste y logotipo (F7.3, ADR-0030)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from housefinder.branding.logo import clean_logo
from housefinder.db import branding as sql
from housefinder.db.connection import Connection

COLOR = re.compile(r"^#[0-9a-f]{6}$")
MIN_CONTRAST = Decimal("4.5")  # WCAG AA, texto normal sobre blanco
LIMITS = {"display_name": 80, "contact": 120, "intro": 600}
LABELS = {"display_name": "El nombre", "contact": "El contacto", "intro": "La presentación"}


class BrandingError(ValueError):
    """La marca no vale; el mensaje dice por qué."""


@dataclass(frozen=True)
class Branding:
    display_name: str | None = None
    contact: str | None = None
    color: str | None = None
    intro: str | None = None
    logo_png: bytes | None = None

    @property
    def empty(self) -> bool:
        return not any((self.display_name, self.contact, self.intro, self.logo_png))


def load(conn: Connection, org_id: UUID) -> Branding:
    row = sql.get_branding(conn, org_id)
    if row is None:
        return Branding()
    return Branding(row.display_name, row.contact, row.color, row.intro, row.logo_png)


def save_texts(conn: Connection, org_id: UUID, display_name: str | None, contact: str | None,
               color: str | None, intro: str | None) -> None:
    values = {"display_name": _text(display_name), "contact": _text(contact),
              "intro": _text(intro, keep_lines=True)}
    for name, value in values.items():
        if value is not None and len(value) > LIMITS[name]:
            raise BrandingError(f"{LABELS[name]} puede tener {LIMITS[name]} caracteres como "
                                "mucho")
    sql.save_texts(conn, org_id, values["display_name"], values["contact"], check_color(color),
                   values["intro"])


def save_logo(conn: Connection, org_id: UUID, data: bytes | None) -> None:
    sql.save_logo(conn, org_id, clean_logo(data) if data else None)


def check_color(color: str | None) -> str | None:
    if not color:
        return None
    color = color.strip().lower()
    if not COLOR.match(color):
        raise BrandingError("El color tiene que ser #RRGGBB (por ejemplo #1f5f8b)")
    ratio = contrast_on_white(color)
    if ratio < MIN_CONTRAST:
        shown = str(ratio.quantize(Decimal("0.1"))).replace(".", ",")
        raise BrandingError(f"Ese color es demasiado claro sobre blanco (contraste {shown}:1; "
                            "hace falta 4,5:1)")
    return color


def contrast_on_white(color: str) -> Decimal:
    """Contraste WCAG 2 entre el color y el blanco: (1 + 0,05) / (L + 0,05)."""
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    return Decimal(str(round(1.05 / (luminance + 0.05), 4)))


def _text(value: str | None, keep_lines: bool = False) -> str | None:
    if value is None:
        return None
    if keep_lines:
        lines = [" ".join(line.split()) for line in value.strip().splitlines()]
        value = "\n".join(lines)
    else:
        value = " ".join(value.split())
    return value or None
