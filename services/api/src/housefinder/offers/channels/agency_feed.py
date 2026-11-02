"""Canal de feeds de agencias en formato Kyero v3 (ADR-0038).

La agencia nos cede su cartera y nos da el enlace del feed que genera su CRM. El feed es una foto
completa: cada inmueble en venta es una oferta `anuncio` con los datos que da la propia agencia,
sin LLM. No se guardan los contactos (pueden ser de una persona) ni las URL de las fotos (sus
derechos quedan para la consulta legal); de las fotos, solo cuántas hay.

La URL no se guarda en este módulo ni sale en ningún informe: puede llevar credenciales.
"""

from __future__ import annotations

import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from uuid import UUID

import httpx

from housefinder.offers.model import NormalizedOffer, RawItem

NAME = "feed_agencia"
AGENT = "HouseFinder"
MAX_BYTES = 50 * 1024 * 1024
CATASTRAL_REF = re.compile(r"[0-9A-Z]{20}")
SPAIN = {"", "spain", "espana"}
# El tipo de Kyero es texto libre del CRM; se traduce al de la extracción por palabras clave, en
# este orden (lo más concreto primero: «warehouse» no es una casa). Lo que no casa, 'otro'.
TYPES: list[tuple[str, re.Pattern[str]]] = [
    ("garaje", re.compile(r"\b(garage|garaje|parking|aparcamiento|plaza de garaje)\b")),
    ("trastero", re.compile(r"\b(storage|trastero|storeroom)\b")),
    ("oficina", re.compile(r"\b(office|oficina|despacho)\b")),
    ("local", re.compile(r"\b(commercial|local|shop|tienda|nave|warehouse|industrial|retail"
                         r"|restaurant|restaurante|bar)\b")),
    ("edificio", re.compile(r"\b(building|edificio)\b")),
    ("rustica", re.compile(r"\b(rustica|rustic land|agricultural|agricola|finca rustica)\b")),
    ("suelo", re.compile(r"\b(plot|land|solar|parcela|terreno|urban plot)\b")),
    ("vivienda", re.compile(r"\b(apartment|apartamento|flat|piso|penthouse|atico|duplex|studio"
                            r"|estudio|house|casa|villa|chalet|townhouse|town house|adosado"
                            r"|pareado|bungalow|cortijo|masia|finca|planta baja|loft|vivienda"
                            r"|country house|home)\b")),
]


class FeedUnavailable(RuntimeError):
    """El feed no se pudo leer: no se retira nada (una caída no vacía la cartera)."""


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def property_type(kyero_type: str) -> str:
    folded = fold(kyero_type)
    return next((name for name, words in TYPES if words.search(folded)), "otro")


def _text(element: ET.Element, path: str) -> str:
    return " ".join((element.findtext(path) or "").split())


def _decimal(text: str) -> Decimal | None:
    try:
        value = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None
    return value if value.is_finite() and value > 0 else None


def _flag(text: str) -> bool:
    return text.strip() == "1"


def _by_language(element: ET.Element, tag: str) -> dict[str, str]:
    node = element.find(tag)
    children = list(node) if node is not None else []
    return {child.tag: " ".join((child.text or "").split())
            for child in children if (child.text or "").strip()}


def listing(element: ET.Element) -> dict[str, Any]:
    """Un `<property>` como diccionario. Solo se copian los campos de la lista: los contactos
    (`email`, `contact_number`, `whatsapp_number`), las fotos y los vídeos no (ADR-0038)."""
    by_language = _by_language(element, "desc")
    urls = _by_language(element, "url")
    images = element.find("images")
    raw: dict[str, Any] = {
        "id": _text(element, "id"), "date": _text(element, "date"), "ref": _text(element, "ref"),
        "price": _text(element, "price"), "currency": _text(element, "currency"),
        "price_freq": _text(element, "price_freq"),
        "part_ownership": _text(element, "part_ownership"),
        "leasehold": _text(element, "leasehold"), "new_build": _text(element, "new_build"),
        "type": _text(element, "type"), "town": _text(element, "town"),
        "province": _text(element, "province"), "country": _text(element, "country"),
        "latitude": _text(element, "location/latitude"),
        "longitude": _text(element, "location/longitude"),
        "location_detail": _text(element, "location_detail"),
        "beds": _text(element, "beds"), "baths": _text(element, "baths"),
        "pool": _text(element, "pool"), "built": _text(element, "surface_area/built"),
        "plot": _text(element, "surface_area/plot"),
        "energy_consumption": _text(element, "energy_rating/consumption"),
        "energy_emissions": _text(element, "energy_rating/emissions"),
        "catastral": _text(element, "catastral").replace(" ", "").upper(),
        "desc": by_language, "url": urls,
        "features": [_text(f, ".") for f in element.iterfind("features/feature")],
        "images": len(images.findall("image")) if images is not None else 0,
    }
    return {key: value for key, value in raw.items() if value not in ("", [], {})}


def skip_reason(raw: dict[str, Any]) -> str | None:
    """Por qué un inmueble del feed no es una oferta de venta que podamos usar."""
    if not raw.get("id"):
        return "sin_id"
    if raw.get("price_freq") != "sale":
        return "alquiler"
    if raw.get("currency", "EUR").upper() != "EUR":
        return "otra_moneda"
    if fold(raw.get("country", "")) not in SPAIN:
        return "fuera_de_espana"
    if _flag(raw.get("part_ownership", "")) or _flag(raw.get("leasehold", "")):
        return "propiedad_parcial"
    if _decimal(raw.get("price", "")) is None:
        return "sin_precio"
    return None


def parse_feed(content: bytes) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Los inmuebles en venta del feed y, aparte, cuántos se saltan y por qué."""
    if b"<!DOCTYPE" in content[:4096] or b"<!ENTITY" in content[:65536]:
        raise FeedUnavailable("el feed declara un DOCTYPE o entidades: no se lee")
    kept: list[dict[str, Any]] = []
    skipped: Counter[str] = Counter()
    try:
        for _, element in ET.iterparse(io.BytesIO(content), events=("end",)):
            if element.tag != "property":
                continue
            raw = listing(element)
            element.clear()
            reason = skip_reason(raw)
            if reason:
                skipped[reason] += 1
            else:
                kept.append(raw)
    except ET.ParseError as exc:
        raise FeedUnavailable(f"XML no válido: {exc}") from exc
    return kept, skipped


def robots_for(client: httpx.Client, url: str) -> RobotFileParser:
    """El `robots.txt` del servidor del feed, sin las credenciales de la URL."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    origin = urlunsplit((parts.scheme, host + (f":{parts.port}" if parts.port else ""),
                         "/robots.txt", "", ""))
    parser = RobotFileParser()
    response = client.get(origin, timeout=30)
    if response.status_code in (401, 403):
        parser.disallow_all = True
    elif response.status_code >= 400:
        parser.allow_all = True
    else:
        parser.parse(response.text.splitlines())
    return parser


def download(client: httpx.Client, url: str) -> bytes:
    chunks: list[bytes] = []
    size = 0
    try:
        with client.stream("GET", url, timeout=120) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise FeedUnavailable(f"el feed pasa de {MAX_BYTES // (1024 * 1024)} MB")
                chunks.append(chunk)
    except httpx.HTTPError as exc:
        raise FeedUnavailable(f"no se pudo descargar ({type(exc).__name__})") from exc
    return b"".join(chunks)


def _public(url: str) -> str:
    """La URL sin usuario ni contraseña, para comprobarla con el robots.txt."""
    parts = urlsplit(url)
    netloc = (parts.hostname or "") + (f":{parts.port}" if parts.port else "")
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, ""))


class AgencyFeed:
    name = NAME

    def __init__(self, feed_id: UUID, url: str) -> None:
        self.feed_id = feed_id
        self.source_id = f"feed-agencia-{feed_id}"
        self._url = url
        self.skipped: Counter[str] = Counter()

    def __repr__(self) -> str:  # nunca la URL
        return f"AgencyFeed({self.feed_id})"

    def fetch(self, client: httpx.Client) -> Iterator[RawItem]:
        """Descarga y lee el feed entero antes de devolver nada: si falla, `FeedUnavailable`."""
        robots = robots_for(client, self._url)
        if not robots.can_fetch(AGENT, _public(self._url)):
            raise FeedUnavailable("el robots.txt del servidor del feed no deja leerlo")
        listings, self.skipped = parse_feed(download(client, self._url))
        items = [RawItem(f"{self.feed_id}:{raw['id']}", _listing_url(raw), _day(raw), raw)
                 for raw in listings]
        yield from items

    def parse(self, item: RawItem) -> list[NormalizedOffer]:
        raw = item.raw
        kind = property_type(raw.get("type", ""))
        town = raw.get("town")
        label = raw.get("type", "").strip().capitalize() or "Inmueble"
        ref = raw.get("catastral", "")
        lon, lat = _point(raw)
        return [NormalizedOffer(
            external_id=item.external_id,
            kind="anuncio",
            url=item.url,
            title=f"{label} en {town}" if town else label,
            published_on=item.published_on,
            description=_description(raw),
            asking_price=_decimal(raw.get("price", "")),
            cadastral_ref=ref if CATASTRAL_REF.fullmatch(ref) else None,
            municipality=town,
            province=raw.get("province"),
            built_area_m2=_decimal(raw.get("built", "")),
            lon=lon,
            lat=lat,
            extraction_status="no_aplica",
            extracted={"property_type": kind, "feed": {
                key: raw[key] for key in ("type", "ref", "beds", "baths", "pool", "plot",
                                          "new_build", "features", "location_detail",
                                          "energy_consumption", "energy_emissions", "images")
                if key in raw}},
        )]


def _listing_url(raw: dict[str, Any]) -> str:
    urls: dict[str, str] = raw.get("url", {})
    return urls.get("es") or urls.get("en") or next(iter(urls.values()), "")


def _description(raw: dict[str, Any]) -> str | None:
    texts: dict[str, str] = raw.get("desc", {})
    return texts.get("es") or texts.get("en") or next(iter(texts.values()), None)


def _day(raw: dict[str, Any]) -> date | None:
    try:
        return datetime.strptime(raw.get("date", ""), "%Y-%m-%d %H:%M:%S").date()
    except ValueError:
        return None


def _point(raw: dict[str, Any]) -> tuple[float | None, float | None]:
    """La coordenada si es de España (península, islas, Ceuta y Melilla); si no, ninguna."""
    try:
        lat, lon = float(raw.get("latitude", "")), float(raw.get("longitude", ""))
    except ValueError:
        return None, None
    if 27.0 <= lat <= 44.5 and -18.5 <= lon <= 4.5:
        return lon, lat
    return None, None
