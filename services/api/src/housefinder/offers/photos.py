"""Imagen de una oferta para la web (ADR-0054): fachada del Catastro u ortofoto del PNOA.

No se guarda en la base de datos ni en disco: se descarga cuando alguien la pide, se reduce a un
tamaño de tarjeta y se guarda en memoria un tiempo. La ortofoto lleva marcado el punto del
inmueble, para saber cuál es entre los edificios de alrededor.
"""

from __future__ import annotations

import io
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Literal

from PIL import Image, ImageDraw, UnidentifiedImageError

PhotoKind = Literal["fachada", "aerea"]
MAX_WIDTH = 640
QUALITY = 78
CACHE_SIZE = 300
CACHE_SECONDS = 24 * 3600
MARK = (227, 169, 43)  # latón de la marca (--brass)


class PhotoCache:
    """Caché en memoria por clave, con caducidad. Guarda también que no hay foto (None)."""

    def __init__(self, size: int = CACHE_SIZE, seconds: float = CACHE_SECONDS,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._items: OrderedDict[str, tuple[float, bytes | None]] = OrderedDict()
        self._size = size
        self._seconds = seconds
        self._clock = clock

    def get(self, key: str, load: Callable[[], bytes | None]) -> bytes | None:
        now = self._clock()
        hit = self._items.get(key)
        if hit is not None and now - hit[0] < self._seconds:
            self._items.move_to_end(key)
            return hit[1]
        value = load()
        self._items[key] = (now, value)
        self._items.move_to_end(key)
        while len(self._items) > self._size:
            self._items.popitem(last=False)
        return value


def card_image(data: bytes, mark_center: bool = False) -> bytes | None:
    """La imagen reducida a `MAX_WIDTH` en JPEG; con `mark_center`, un anillo en el centro.

    None si no es una imagen que Pillow sepa leer.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            out = img.convert("RGB")
    except (UnidentifiedImageError, OSError):
        return None
    if out.width > MAX_WIDTH:
        out = out.resize((MAX_WIDTH, round(out.height * MAX_WIDTH / out.width)),
                         Image.Resampling.LANCZOS)
    if mark_center:
        draw = ImageDraw.Draw(out)
        cx, cy = out.width / 2, out.height / 2
        for radius, width, color in ((15, 7, (255, 255, 255)), (15, 4, MARK)):
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                         outline=color, width=width)
        draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=MARK)
    buffer = io.BytesIO()
    out.save(buffer, "JPEG", quality=QUALITY, optimize=True)
    return buffer.getvalue()
