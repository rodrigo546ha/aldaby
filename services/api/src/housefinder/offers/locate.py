"""Ubicar una oferta: por referencia catastral (Catastro, ADR-0016) y, si no, por dirección
(CartoCiudad con caché, ADR-0009).

Un resultado no se acepta a ciegas. CartoCiudad devolvió para «Carretera M-119 21, Alcalá de
Henares» la «CALLE ALCALA HENARES 119, 30720 Santiago de la Ribera», en Murcia: leyó el municipio
como nombre de calle. Por eso el punto tiene que caer en una sección censal cargada (la zona que
cubrimos) y, si la oferta dice su municipio, la dirección encontrada tiene que ser de ese
municipio. Si no, se prueba la siguiente vía o la oferta se queda sin ubicar.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

from housefinder.db.connection import Connection
from housefinder.db.sections import latest_vintage, section_at
from housefinder.geo.cartociudad import AddressNotFound, AddressTooVague, Geocoded
from housefinder.geo.catastro import Parcel, ParcelNotFound
from housefinder.offers.ingest import Locator, Point
from housefinder.offers.model import NormalizedOffer
from housefinder.territory.service import locate_address, locate_parcel


def offer_locator(
    conn: Connection,
    geocoder: Callable[[str], Geocoded],
    parcels: Callable[[str], Parcel] | None = None,
) -> Locator:
    def by_parcel(offer: NormalizedOffer) -> Point | None:
        if parcels is None or not offer.cadastral_ref:
            return None
        try:
            found = locate_parcel(conn, offer.cadastral_ref, parcels)
        except ParcelNotFound:
            return None
        if not _covered(conn, found.lon, found.lat):
            return None
        if offer.municipality and not parcel_in_municipality(offer.municipality, found.matched):
            return None
        return Point(found.lon, found.lat, "catastro")

    def by_address(offer: NormalizedOffer) -> Point | None:
        if not offer.address:
            return None
        try:
            found = locate_address(conn, offer.address, geocoder)
        except (AddressNotFound, AddressTooVague):
            return None
        if not _covered(conn, found.lon, found.lat):
            return None
        if offer.municipality and not same_municipality(offer.municipality, found.matched):
            return None
        return Point(found.lon, found.lat, "cartociudad")

    def locate(offer: NormalizedOffer) -> Point | None:
        return by_parcel(offer) or by_address(offer)

    return locate


def _covered(conn: Connection, lon: float, lat: float) -> bool:
    """El punto cae en una sección censal de la última cartografía cargada."""
    vintage = latest_vintage(conn)
    return vintage is not None and section_at(conn, lon, lat, vintage) is not None


def parcel_in_municipality(expected: str, address: str | None) -> bool:
    """La dirección catastral («CR CAMARMA 21 ALCALA DE HENARES (MADRID)») termina con el
    municipio, antes de la provincia entre paréntesis."""
    if not address:
        return False
    place = _fold(re.sub(r"\([^)]*\)\s*$", "", address))
    wanted = _fold(expected)
    return bool(wanted) and re.search(rf"(?<!\w){re.escape(wanted)}$", place) is not None


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
