"""Texto de los PDF de fuentes públicas: pliegos y hojas de lote (ADR-0022, ADR-0037).

Solo PDF con texto; un escaneado se devuelve vacío y quien llama decide. Los documentos del usuario
van por `documents/`, que además hace OCR.
"""

from __future__ import annotations

import io

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 40


class UnreadablePdf(ValueError):
    pass


def pdf_pages(content: bytes, max_pages: int = MAX_PAGES) -> list[str]:
    """Texto de cada página."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    if len(content) > MAX_BYTES:
        raise UnreadablePdf(f"pasa de {MAX_BYTES // (1024 * 1024)} MB")
    if not content.startswith(b"%PDF"):
        raise UnreadablePdf("no es un PDF")
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise UnreadablePdf("está protegido con contraseña")
        if len(reader.pages) > max_pages:
            raise UnreadablePdf(f"tiene más de {max_pages} páginas")
        return [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise UnreadablePdf("está dañado") from exc
