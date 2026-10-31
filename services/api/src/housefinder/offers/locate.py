"""Ubicar una oferta: por referencia catastral (Catastro, ADR-0016) y, si no, por dirección
(CartoCiudad con caché, ADR-0009).

Un resultado no se acepta a ciegas. CartoCiudad devolvió para «Carretera M-119 21, Alcalá de
Henares» la «CALLE ALCALA HENARES 119, 30720 Santiago de la Ribera», en Murcia: leyó el municipio
como nombre de calle. Por eso el punto tiene que caer en una sección censal cargada (la zona que
cubrimos) y, si la oferta dice su municipio, la dirección encontrada tiene que ser de ese
municipio. Si no, se prueba la siguiente vía o la oferta se queda sin ubicar.

Antes de preguntar fuera, la provincia: un lote que dice ser de otra provincia (`data/offers/
zona.yaml`) no se manda a ningún servicio. Si CartoCiudad falla (un 500 con una parcela de Sahagún,
León, el 2026-10-30), la oferta se queda sin ubicar y el trabajo sigue: si no, el reintento
repetiría la extracción de todo el lote con el LLM. En los dos casos se avisa con el motivo.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml

from housefinder.db.connection import Connection
from housefinder.db.sections import latest_vintage, section_at
from housefinder.geo.cartociudad import AddressNotFound, AddressTooVague, Geocoded
from housefinder.geo.catastro import Parcel, ParcelNotFound
from housefinder.offers.ingest import Locator, Point
from housefinder.offers.model import NormalizedOffer
from housefinder.territory.service import locate_address, locate_parcel

# Oferta que se queda sin ubicar por algo que no es la dirección (fuera de la zona, servicio caído)
# y su motivo, para el informe del trabajo.
Miss = Callable[[NormalizedOffer, str], None]
PROVINCE_IN_PARENS = re.compile(r"\(([^()]+)\)\s*$")
PROVINCE_PREFIX = re.compile(r"^(?:provincia|comunidad(?: autonoma)?) de ")


@dataclass(frozen=True)
class Zone:
    provinces: frozenset[str]  # nombres sin mayúsculas ni tildes

    @classmethod
    def of(cls, names: Iterable[str]) -> Zone:
        return cls(frozenset(_province(name) for name in names))

    def outside(self, offer: NormalizedOffer) -> str | None:
        """La provincia que dice la oferta, si no es de la zona. None si es de la zona o no lo
        dice (entonces decide la cartografía, después de ubicarla)."""
        in_parens = PROVINCE_IN_PARENS.search(offer.municipality or "")
        for stated in (offer.province, in_parens.group(1) if in_parens else None):
            if stated and _province(stated) not in self.provinces:
                return stated
        return None


def load_zone(path: Path | None = None) -> Zone:
    data = yaml.safe_load((path or default_zone_path()).read_text(encoding="utf-8"))
    return Zone.of(str(name) for name in data["provinces"].values())


def default_zone_path() -> Path:
    """services/api/data/offers/zona.yaml"""
    return Path(__file__).resolve().parents[3] / "data" / "offers" / "zona.yaml"


def offer_locator(
    conn: Connection,
    geocoder: Callable[[str], Geocoded],
    parcels: Callable[[str], Parcel] | None = None,
    on_miss: Miss | None = None,
    zone: Zone | None = None,
) -> Locator:
    covered = zone or load_zone()

    def missed(offer: NormalizedOffer, reason: str) -> None:
        if on_miss is not None:
            on_miss(offer, reason)

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
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            missed(offer, f"CartoCiudad no responde: {_failure(exc)}")
            return None
        if not _covered(conn, found.lon, found.lat):
            return None
        if offer.municipality and not same_municipality(offer.municipality, found.matched):
            return None
        return Point(found.lon, found.lat, "cartociudad")

    def locate(offer: NormalizedOffer) -> Point | None:
        province = covered.outside(offer)
        if province is not None:
            missed(offer, f"fuera de la zona cubierta: provincia «{province}»")
            return None
        return by_parcel(offer) or by_address(offer)

    return locate


def _covered(conn: Connection, lon: float, lat: float) -> bool:
    """El punto cae en una sección censal de la última cartografía cargada."""
    vintage = latest_vintage(conn)
    return vintage is not None and section_at(conn, lon, lat, vintage) is not None


def _failure(exc: Exception) -> str:
    """Sin la URL: lleva la dirección consultada."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, json.JSONDecodeError):
        return "respuesta que no es JSON"
    return type(exc).__name__


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


def _province(name: str) -> str:
    return PROVINCE_PREFIX.sub("", _fold(name))


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())
