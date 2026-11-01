"""Geocodificador de CartoCiudad (ADR-0009).

Método `find`: devuelve el mejor candidato para un texto. Solo se aceptan resultados con
precisión de portal o, con aviso, de calle; el resto no basta para elegir una sección censal.
Condiciones: servicio gratuito citando «CC BY 4.0 www.scne.es/productos.html#CartoCiudad».
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import httpx

from housefinder.geo.names import place_key

FIND_URL = "https://www.cartociudad.es/geocoder/api/geocoder/find"
CANDIDATES_URL = "https://www.cartociudad.es/geocoder/api/geocoder/candidates"
SOURCE_ID = "cartociudad-geocoder"
SOURCE_NAME = "Geocodificador de CartoCiudad (IGN, CNIG)"
ATTRIBUTION = "CC BY 4.0 www.scne.es/productos.html#CartoCiudad"
LICENSE_URL = "https://www.cartociudad.es/web/portal/faq"
EXACT = "portal"
STREET = "callejero"
ACCEPTED = {EXACT, STREET}
PLACES = {"Municipio", "poblacion"}  # candidatos que son un municipio o un núcleo de población


class AddressNotFound(LookupError):
    """El geocodificador no encuentra la dirección."""


class AddressTooVague(ValueError):
    """La dirección se encuentra, pero no con precisión de portal o calle."""


@dataclass(frozen=True)
class Geocoded:
    lon: float
    lat: float
    match_type: str  # 'portal' o 'callejero'
    matched: str  # dirección encontrada, para que el usuario la confirme
    municipality: str | None  # código INE del municipio
    cadastral_ref: str | None

    @property
    def approximate(self) -> bool:
        return self.match_type != EXACT


def normalize(address: str) -> str:
    """Clave de caché: minúsculas, espacios simples. Conserva las tildes."""
    text = unicodedata.normalize("NFC", address).strip().lower()
    return re.sub(r"\s+", " ", text)


def query_text(address: str) -> str:
    """Sin comillas dobles ni barras invertidas: CartoCiudad lee la consulta como JSON y responde
    un 500 con ellas (comprobado el 2026-11-01, ADR-0031)."""
    return " ".join(re.sub(r'["\\]', "", address).split())


def parse_find(payload: Any) -> Geocoded:
    if not isinstance(payload, dict) or payload.get("lat") is None or payload.get("lng") is None:
        raise AddressNotFound("CartoCiudad no encuentra la dirección")
    match_type = str(payload.get("type", ""))
    if match_type not in ACCEPTED:
        raise AddressTooVague(
            f"La dirección solo se localiza como «{match_type}»: indica calle y número"
        )
    return Geocoded(
        lon=float(payload["lng"]),
        lat=float(payload["lat"]),
        match_type=match_type,
        matched=_matched_address(payload),
        municipality=payload.get("muniCode") or None,
        cadastral_ref=payload.get("refCatastral") or None,
    )


def geocode(client: httpx.Client, address: str) -> Geocoded:
    if not address.strip():
        raise AddressNotFound("Dirección vacía")
    response = client.get(FIND_URL, params={"q": query_text(address)}, timeout=20)
    response.raise_for_status()
    if not response.content.strip():
        raise AddressNotFound("CartoCiudad no encuentra la dirección")
    return parse_find(response.json())


def municipality_codes(client: httpx.Client, name: str) -> frozenset[str]:
    """Códigos INE de los municipios que se llaman `name`, en cualquiera de sus lenguas
    («Castelló de la Plana/Castellón de la Plana»), o que tienen un núcleo con ese nombre."""
    text = query_text(name)
    response = client.get(CANDIDATES_URL, params={"q": text, "limit": 10}, timeout=20)
    response.raise_for_status()
    if not response.content.strip():
        return frozenset()
    return parse_municipalities(response.json(), text)


def parse_municipalities(payload: Any, name: str) -> frozenset[str]:
    """Solo el mismo nombre, en cualquiera de las lenguas oficiales (`geo/names.py`):
    `candidates` también trae parecidos («Gironella» para «Gerona») y calles con ese nombre en
    otros municipios. De cada candidato vale su municipio (`muni`) y, si es un lugar, su núcleo:
    para «Algimia de Alfara» no trae el municipio, sino calles y topónimos de «Algímia
    d'Alfara»."""
    wanted = place_key(name)
    codes: set[str] = set()
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or not item.get("muniCode"):
            continue
        muni = str(item.get("muni") or "")
        names = [muni, *muni.split("/")]
        if item.get("type") in PLACES:
            names.append(str(item.get("poblacion") or ""))
        if wanted and wanted in {place_key(n) for n in names}:
            codes.add(str(item["muniCode"]))
    return frozenset(codes)


def _matched_address(payload: dict[str, Any]) -> str:
    street = " ".join(p for p in (payload.get("tip_via"), payload.get("address")) if p)
    number = payload.get("portalNumber")
    if number and not payload.get("noNumber"):
        street += f" {number}{payload.get('extension') or ''}"
    place = payload.get("poblacion") or payload.get("muni") or ""
    postal = payload.get("postalCode") or ""
    return ", ".join(p for p in (street.strip(), f"{postal} {place}".strip()) if p)
