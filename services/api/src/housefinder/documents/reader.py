"""Texto de un documento del usuario: PDF con texto, PDF escaneado o foto (ADR-0021).

Todo en local y en memoria: el documento no se guarda. Una página de PDF con poco texto se pasa a
imagen y se lee con Tesseract en español; una foto, igual. Solo este módulo importa las bibliotecas
de PDF y de OCR.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 10
MIN_PAGE_TEXT = 30  # caracteres: con menos, la página es un escaneo
OCR_DPI = 300
OCR_LANG = "spa"
Method = Literal["texto", "pdf", "ocr", "pdf+ocr"]


class UnreadableDocument(ValueError):
    """El documento no se puede leer; el mensaje es para el usuario y no repite su contenido."""


class OcrUnavailable(UnreadableDocument):
    pass


@dataclass(frozen=True)
class DocumentText:
    text: str
    method: Method
    pages: int


def read_text(text: str) -> DocumentText:
    return DocumentText(text.strip(), "texto", 1)


def read_document(content: bytes, max_pages: int = MAX_PAGES) -> DocumentText:
    if len(content) > MAX_BYTES:
        raise UnreadableDocument("El documento pasa de 10 MB")
    if content.startswith(b"%PDF"):
        return _pdf(content, max_pages=max_pages)
    if content.startswith((b"\x89PNG", b"\xff\xd8\xff")):
        return DocumentText(_ocr(_image(content)), "ocr", 1)
    raise UnreadableDocument("Solo se leen PDF, JPG y PNG")


def _pdf(content: bytes, max_pages: int = MAX_PAGES) -> DocumentText:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise UnreadableDocument("El PDF está protegido con contraseña: descárgalo sin ella")
        pages = reader.pages
        if len(pages) > max_pages:
            raise UnreadableDocument(f"El PDF tiene más de {max_pages} páginas")
        texts = [(page.extract_text() or "").strip() for page in pages]
    except PdfReadError as exc:
        raise UnreadableDocument("El PDF está dañado o no es un PDF") from exc
    scanned = [i for i, t in enumerate(texts) if len(t) < MIN_PAGE_TEXT]
    if scanned:
        images = _render(content, scanned)
        for index, image in zip(scanned, images, strict=True):
            texts[index] = _ocr(image)
    method: Method = "pdf" if not scanned else ("ocr" if len(scanned) == len(texts) else "pdf+ocr")
    return DocumentText("\n\n".join(t for t in texts if t), method, len(texts))


def _render(content: bytes, indexes: list[int]) -> list[object]:
    import pypdfium2

    pdf = pypdfium2.PdfDocument(content)
    try:
        return [pdf[i].render(scale=OCR_DPI / 72).to_pil() for i in indexes]
    finally:
        pdf.close()


def _image(content: bytes) -> object:
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        image = Image.open(io.BytesIO(content))
        return ImageOps.exif_transpose(image).convert("RGB")  # fotos del móvil giradas
    except (UnidentifiedImageError, OSError) as exc:
        raise UnreadableDocument("La imagen está dañada") from exc


def _ocr(image: object) -> str:
    import pytesseract

    try:
        return str(pytesseract.image_to_string(image, lang=OCR_LANG)).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailable(
            "Para leer escaneos y fotos hace falta Tesseract: "
            "`brew install tesseract tesseract-lang`"
        ) from exc
    except pytesseract.TesseractError as exc:
        raise OcrUnavailable(
            "Tesseract no tiene el idioma español: `brew install tesseract-lang`"
        ) from exc
