"""Ubicar una oferta por su dirección con el geocodificador y su caché (ADR-0009).

Un resultado del geocodificador no se acepta a ciegas. CartoCiudad devolvió para «Carretera
M-119 21, Alcalá de Henares» la «CALLE ALCALA HENARES 119, 30720 Santiago de la Ribera», en Murcia:
leyó el municipio como nombre de calle. Por eso el punto tiene que caer en una sección censal
cargada (la zona que cubrimos) y, si la oferta dice su municipio, el que encontró el geocodificador
tiene que ser ese. Si no, la oferta se queda sin ubicar.

La ubicación por referencia catastral (Catastro) llegará con su propio ADR.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

from housefinder.db.connection import Connection
from housefinder.db.sections import latest_vintage, section_at
from housefinder.geo.cartociudad import AddressNotFound, AddressTooVague, Geocoded
from housefinder.offers.ingest import Locator, Point
from housefinder.offers.model import NormalizedOffer
from housefinder.territory.service import locate_address


def address_locator(conn: Connection, geocoder: Callable[[str], Geocoded]) -> Locator:
    def locate(offer: NormalizedOffer) -> Point | None:
        if not offer.address:
            return None
        try:
            found = locate_address(conn, offer.address, geocoder)
        except (AddressNotFound, AddressTooVague):
            return None
        vintage = latest_vintage(conn)
        if vintage is None or section_at(conn, found.lon, found.lat, vintage) is None:
            return None  # fuera de la zona cubierta
        if offer.municipality and not same_municipality(offer.municipality, found.matched):
            return None
        return Point(found.lon, found.lat, "cartociudad")

    return locate


def same_municipality(expected: str, matched: str | None) -> bool:
    """El municipio esperado está en la localidad de la dirección encontrada.

    CartoCiudad devuelve «CALLE MAYOR 1, 28801 Alcalá de Henares»: la localidad va detrás de la
    primera coma. Se compara sin mayúsculas ni tildes y por palabras enteras.
    """
    if not matched or "," not in matched:
        return False
    place = _fold(matched.split(",", 1)[1])
    wanted = _fold(expected)
    return bool(wanted) and re.search(rf"(?<!\w){re.escape(wanted)}(?!\w)", place) is not None


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())
