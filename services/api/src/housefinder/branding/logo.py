"""Logotipo del profesional: se abre, se reduce y se vuelve a codificar en PNG (ADR-0030).

Se guarda siempre la imagen reescrita, nunca el fichero subido: así no viaja al PDF nada que no
sean píxeles. Solo PNG y JPEG; SVG no, porque puede cargar recursos externos.
"""

from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError

MAX_BYTES = 2 * 1024 * 1024
MAX_SIZE = (600, 200)  # ancho y alto máximos del logotipo guardado
MAX_PIXELS = 25_000_000  # contra imágenes que estallan al descomprimirlas
FORMATS = {"PNG", "JPEG"}


class LogoError(ValueError):
    """El logotipo no vale; el mensaje dice por qué."""


def clean_logo(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise LogoError("El logotipo puede pesar 2 MB como mucho")
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in FORMATS:
                raise LogoError("El logotipo tiene que ser PNG o JPEG")
            image.load()
            picture = image.convert("RGBA")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise LogoError("No se puede leer la imagen: sube un PNG o un JPEG") from exc
    picture.thumbnail(MAX_SIZE)
    out = io.BytesIO()
    picture.save(out, format="PNG", optimize=True)
    return out.getvalue()
