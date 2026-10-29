"""Ubicar una oferta por su dirección con el geocodificador y su caché (ADR-0009).

La ubicación por referencia catastral (Catastro) llegará con su propio ADR.
"""

from __future__ import annotations

from collections.abc import Callable

from housefinder.db.connection import Connection
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
        return Point(found.lon, found.lat, "cartociudad")

    return locate
