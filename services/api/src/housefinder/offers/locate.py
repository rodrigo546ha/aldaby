"""Ubicar una oferta: por referencia catastral (Catastro, ADR-0016; en el País Vasco y Navarra, su
catastro foral, ADR-0032), por polígono y parcela (Catastro, ADR-0031) y, si no, por dirección
(CartoCiudad con caché, ADR-0009).

Un resultado no se acepta a ciegas. CartoCiudad devolvió para «Carretera M-119 21, Alcalá de
Henares» la «CALLE ALCALA HENARES 119, 30720 Santiago de la Ribera», en Murcia: leyó el municipio
como nombre de calle. Por eso el punto tiene que caer en una sección censal cargada (la zona que
cubrimos) y, si la oferta dice su municipio, la dirección encontrada tiene que ser de ese
municipio. Si no, se prueba la siguiente vía o la oferta se queda sin ubicar.

Antes de preguntar fuera, la provincia: una oferta que dice ser de una provincia sin secciones
cargadas no se manda a ningún servicio. Si un servicio falla, se sigue con la siguiente vía y, sin
punto, la oferta se queda sin ubicar con el motivo y a la espera de otro intento; el trabajo sigue
(ADR-0031).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import yaml

from housefinder.db.connection import Connection
from housefinder.db.sections import latest_vintage, loaded_provinces, section_at
from housefinder.geo.cartociudad import AddressNotFound, AddressTooVague, Geocoded
from housefinder.geo.catastro import CatastroUnavailable, Parcel, ParcelNotFound
from housefinder.geo.foral import FORAL, NAVARRA, SERVICES, foral_key, navarra_key
from housefinder.geo.http import failure
from housefinder.geo.names import fold, place_key
from housefinder.offers.ingest import Locator, Point, Unlocated
from housefinder.offers.model import NormalizedOffer
from housefinder.territory.service import (
    Location,
    locate_address,
    locate_foral_parcel,
    locate_parcel,
)

# Referencia de una finca rústica: (provincia, municipio, polígono, parcela) → 14 caracteres.
RusticFinder = Callable[[str, str, str, str], str]
IN_PARENS = re.compile(r"\(([^()]+)\)\s*$")
PROVINCE_PREFIX = re.compile(r"^(?:provincia|comunidad(?: foral| autonoma)?) de ")
POLYGON = re.compile(r"\bpol[ií]gono\s*(?:n[º°o.]*\s*)?(\d+)\b", re.IGNORECASE)
PARCEL = re.compile(r"\bparcela\s*(?:n[º°o.]*\s*)?(\d+)\b", re.IGNORECASE)
SEVERAL = re.compile(r"\b(?:parcelas|pol[ií]gonos)\b", re.IGNORECASE)
# «polígono ciento cuatro, parcela siete» (BOE-B-2026-32279): el número en letra tras la palabra.
_WORD = r"(?!pol[ií]gono\b|parcela\b)[^\W\d_]+"
SPELLED = re.compile(rf"\b(pol[ií]gono|parcela)(\s+(?:n[º°o.]*\s*)?)({_WORD}(?:\s+{_WORD})*)",
                     re.IGNORECASE)
NUMBER_WORDS = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13,
    "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21, "veintiuna": 21,
    "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30, "cuarenta": 40,
    "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100,
    "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600, "setecientos": 700, "setecientas": 700,
    "ochocientos": 800, "ochocientas": 800, "novecientos": 900, "novecientas": 900, "mil": 1000,
}
# Para CartoCiudad: «nº 5» es «5», y sin el tipo de vía encuentra lo que no conoce por su tipo
# («Callejuela del Cuartel 2, Frechilla» no; «Cuartel 2, Frechilla» sí).
NUMBER_SIGN = re.compile(r"\b(?:n(?:\.\s*)?[º°o]\.?|núm\.?|número)\s*(?=\d)", re.IGNORECASE)
VIA_TYPE = re.compile(
    r"^(?:calle|c/|avenida|avda\.?|plaza|pza\.?|paseo|callejuela|calleja|callejón|camino|"
    r"carretera|ctra\.?|travesía|ronda|glorieta|pasaje|cuesta|costanilla)\s+"
    r"(?:(?:de la|de los|de las|del|de)\s+)?", re.IGNORECASE)
ALL_PARENS = re.compile(r"\([^()]*\)")
NUMBER_PART = re.compile(r"\d+\s*[A-Za-z]?")


@dataclass(frozen=True)
class Provinces:
    """Relación de provincias del INE (`data/offers/provincias.yaml`): nombre → código."""

    codes: dict[str, str]
    names: dict[str, str] = field(default_factory=dict)  # código → nombre del INE

    def code(self, name: str) -> str | None:
        return self.codes.get(_province(name))

    def name(self, code: str) -> str | None:
        return self.names.get(code)


def load_provinces(path: Path | None = None) -> Provinces:
    data = yaml.safe_load((path or default_provinces_path()).read_text(encoding="utf-8"))
    codes: dict[str, str] = {}
    names: dict[str, str] = {}
    for code, literal in data["provinces"].items():
        base, _, article = str(literal).split("/")[0].partition(",")
        names[str(code)] = f"{article.strip()} {base}".strip()  # «Balears, Illes» → «Illes Balears»
        for name in str(literal).split("/"):  # «Alicante/Alacant»
            base, _, article = name.partition(",")  # «Coruña, A»
            codes[_province(base)] = str(code)
            if article.strip():
                codes[_province(f"{article} {base}")] = str(code)
    return Provinces(codes, names)


def default_provinces_path() -> Path:
    """services/api/data/offers/provincias.yaml"""
    return Path(__file__).resolve().parents[3] / "data" / "offers" / "provincias.yaml"


@dataclass(frozen=True)
class Zone:
    """Provincias con secciones censales cargadas: fuera de ellas un punto se descarta."""

    loaded: frozenset[str]  # códigos INE de provincia
    provinces: Provinces = field(default_factory=load_provinces)

    def outside(self, offer: NormalizedOffer) -> str | None:
        """La provincia que dice la oferta, si se sabe cuál es y no tiene secciones cargadas.
        None si es de la zona, no lo dice o el nombre no está en la relación del INE (entonces
        decide la cartografía, después de ubicarla)."""
        for stated in (offer.province, stated_province(offer.municipality)):
            code = self.provinces.code(stated) if stated else None
            if code is not None and code not in self.loaded:
                return stated
        return None


def load_zone(conn: Connection) -> Zone:
    vintage = latest_vintage(conn)
    return Zone(loaded_provinces(conn, vintage) if vintage is not None else frozenset())


def offer_locator(
    conn: Connection,
    geocoder: Callable[[str], Geocoded],
    parcels: Callable[[str], Parcel] | None = None,
    rustic: RusticFinder | None = None,
    zone: Zone | None = None,
    municipalities: Callable[[str], frozenset[str]] | None = None,
    foral: Callable[[str, str], Parcel] | None = None,
) -> Locator:
    covered = zone or load_zone(conn)

    def province_code(offer: NormalizedOffer) -> str | None:
        stated = offer.province or stated_province(offer.municipality)
        return covered.provinces.code(stated) if stated else None

    def in_municipality(name: str, lon: float, lat: float, named: bool,
                        pending: list[str]) -> bool:
        """El municipio de la oferta: por el nombre que da el servicio o, si no casa (nombres
        bilingües: «Castellón de la Plana» y «CASTELLO DE LA PLANA»), por el código INE de la
        sección del punto entre los de los lugares que se llaman como dice la oferta."""
        if named:
            return True
        vintage = latest_vintage(conn)
        hit = section_at(conn, lon, lat, vintage) if vintage is not None else None
        if municipalities is None or hit is None:
            return False
        try:
            codes = municipalities(municipality_name(name))
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            pending.append(f"CartoCiudad no responde al comprobar el municipio: {failure(exc)}")
            return False
        return hit.municipality in codes

    def at_parcel(offer: NormalizedOffer, ref: str, notes: list[str],
                  pending: list[str]) -> Point | None:
        assert parcels is not None
        try:
            found = locate_parcel(conn, ref, parcels)
        except CatastroUnavailable as exc:
            pending.append(str(exc))
            return None
        except ParcelNotFound as exc:
            notes.append(f"{ref}: {exc}")
            return None
        return checked(offer, found, ref, "catastro", notes, pending)

    def at_foral(offer: NormalizedOffer, province: str, key: str, notes: list[str],
                 pending: list[str]) -> Point | None:
        if foral is None:
            return None
        try:
            found = locate_foral_parcel(conn, province, key, foral)
        except CatastroUnavailable as exc:
            pending.append(str(exc))
            return None
        except ParcelNotFound as exc:
            notes.append(f"{key}: {exc}")
            return None
        return checked(offer, found, key, SERVICES[province].source_id, notes, pending)

    def checked(offer: NormalizedOffer, found: Location, ref: str, source: str,
                notes: list[str], pending: list[str]) -> Point | None:
        if not _covered(conn, found.lon, found.lat):
            pending.append(f"la parcela {ref} cae fuera de las secciones cargadas")
            return None
        if offer.municipality and not in_municipality(
                offer.municipality, found.lon, found.lat,
                parcel_in_municipality(offer.municipality, found.matched), pending):
            notes.append(f"la parcela {ref} es de otro municipio: {found.matched}")
            return None
        return Point(found.lon, found.lat, source)

    def by_parcel(offer: NormalizedOffer, notes: list[str], pending: list[str]) -> Point | None:
        if not offer.cadastral_ref:
            return None
        province = province_code(offer)
        key = foral_key(province, offer.cadastral_ref)
        if key is not None:
            return at_foral(offer, *key, notes, pending)
        if province in FORAL:
            notes.append(f"{offer.cadastral_ref}: forma de referencia del catastro de "
                         f"{SERVICES[province].territory} que no se conoce")
            return None
        if parcels is None:
            return None
        return at_parcel(offer, offer.cadastral_ref, notes, pending)

    def by_navarra(offer: NormalizedOffer, municipality: str, rural: tuple[str, str],
                   notes: list[str], pending: list[str]) -> Point | None:
        if foral is None or municipalities is None:
            return None
        try:
            codes = {c for c in municipalities(municipality) if c.startswith("31")}
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            pending.append(f"CartoCiudad no responde al buscar el municipio: {failure(exc)}")
            return None
        if len(codes) != 1:
            notes.append(f"{municipality}: {len(codes)} municipios de Navarra con ese nombre")
            return None
        return at_foral(offer, "31", navarra_key(codes.pop(), *rural), notes, pending)

    def province_of(municipality: str, pending: list[str]) -> str | None:
        """La provincia de un municipio que el anuncio no la dice: la de los lugares de CartoCiudad
        que se llaman así, si son todos de la misma (BOE-B-2026-32279, Campillo de Llerena)."""
        if municipalities is None:
            return None
        try:
            codes = municipalities(municipality)
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            pending.append(f"CartoCiudad no responde al buscar el municipio: {failure(exc)}")
            return None
        prefixes = {code[:2] for code in codes}
        return covered.provinces.name(prefixes.pop()) if len(prefixes) == 1 else None

    def by_polygon(offer: NormalizedOffer, notes: list[str], pending: list[str]) -> Point | None:
        rural = polygon_and_parcel(offer.address or "")
        municipality = municipality_name(offer.municipality or "")
        if rural is None or not municipality:
            return None
        province = offer.province or stated_province(offer.municipality) or \
            province_of(municipality, pending)
        if not province:
            return None
        code = covered.provinces.code(province)
        if code == NAVARRA.province:
            return by_navarra(offer, municipality, rural, notes, pending)
        if code in FORAL or parcels is None or rustic is None:
            return None  # el polígono y parcela de los catastros vascos no está comprobado
        try:
            ref = rustic(province, municipality, *rural)
        except CatastroUnavailable as exc:
            pending.append(str(exc))
            return None
        except ParcelNotFound as exc:
            notes.append(f"polígono {rural[0]}, parcela {rural[1]}: {exc}")
            return None
        return at_parcel(offer, ref, notes, pending)

    def by_address(offer: NormalizedOffer, notes: list[str], pending: list[str]) -> Point | None:
        """Cada forma de la dirección (`address_queries`) hasta que una da un punto del
        municipio; si ninguna, el motivo de la última."""
        missed: str | None = None
        for query in address_queries(offer):
            try:
                found = locate_address(conn, query, geocoder)
            except AddressNotFound:
                missed = "CartoCiudad no encuentra la dirección"
                continue
            except AddressTooVague as exc:
                missed = f"CartoCiudad: {exc}"
                continue
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                pending.append(f"CartoCiudad no responde: {failure(exc)}")
                return None
            if not _covered(conn, found.lon, found.lat):
                pending.append(
                    f"CartoCiudad la sitúa fuera de las secciones cargadas: {found.matched}")
                return None
            if offer.municipality and not in_municipality(
                    offer.municipality, found.lon, found.lat,
                    same_municipality(offer.municipality, found.matched), pending):
                missed = f"CartoCiudad la sitúa en otro municipio: {found.matched}"
                continue
            return Point(found.lon, found.lat, "cartociudad")
        if missed is not None:
            notes.append(missed)
        return None

    def locate(offer: NormalizedOffer) -> Point | Unlocated | None:
        province = covered.outside(offer)
        if province is not None:
            return Unlocated(f"provincia sin secciones cargadas: «{province}»", retry=True)
        notes: list[str] = []
        # Lo que otro intento puede resolver: un servicio que no responde, o un punto fuera de las
        # secciones cargadas (se ubica cuando se carguen; la consulta ya queda en la caché).
        pending: list[str] = []
        for way in (by_parcel, by_polygon, by_address):
            point = way(offer, notes, pending)
            if point is not None:
                return point
        if not notes and not pending:
            return None
        return Unlocated("; ".join(pending + notes), retry=bool(pending))

    return locate


def _covered(conn: Connection, lon: float, lat: float) -> bool:
    """El punto cae en una sección censal de la última cartografía cargada."""
    vintage = latest_vintage(conn)
    return vintage is not None and section_at(conn, lon, lat, vintage) is not None


def address_queries(offer: NormalizedOffer) -> list[str]:
    """La dirección como la busca CartoCiudad: «calle número, municipio», sin la provincia, sin
    «nº», sin paréntesis y sin el municipio repetido. Con la provincia detrás, CartoCiudad no
    encuentra «Paseo de la Marina 5, Garrucha»; con «Donostia» solo, da la avenida de Navarra de
    Milagro (Navarra): el municipio va entero. Después, la misma sin el tipo de vía y, por último,
    la dirección tal como llegó."""
    address = (offer.address or "").strip()
    if not address:
        return []
    town = municipality_name(offer.municipality) if offer.municipality else None
    drop = {place_key(name) for name in (town, offer.province,
                                         stated_province(offer.municipality)) if name}
    kept: list[str] = []
    for part in (NUMBER_SIGN.sub("", p).strip() for p in ALL_PARENS.sub("", address).split(",")):
        if not part or place_key(part) in drop:
            continue
        if kept and NUMBER_PART.fullmatch(part):  # «Plaza Cuartel, 6» → «Plaza Cuartel 6»
            kept[-1] += f" {part}"
            continue
        kept.append(part)
    street = " ".join(", ".join(kept).split())
    bare = VIA_TYPE.sub("", street, count=1)
    queries = [street, bare] if bare and bare != street else [street]
    queries = [f"{q}, {town}" if town else q for q in queries if q] + [address]
    return list(dict.fromkeys(queries))


def polygon_and_parcel(text: str) -> tuple[str, str] | None:
    """Polígono y parcela de una finca rústica («parcela 14, polígono 501», también en letra).
    None si falta uno o el texto nombra más de uno (varias parcelas en un lote)."""
    text = SPELLED.sub(_in_digits, text)
    if SEVERAL.search(text):
        return None
    polygons = set(POLYGON.findall(text))
    parcels = set(PARCEL.findall(text))
    if len(polygons) != 1 or len(parcels) != 1:
        return None
    return polygons.pop(), parcels.pop()


def _in_digits(found: re.Match[str]) -> str:
    """«polígono ciento cuatro» → «polígono 104»: las palabras de número que siguen; el resto
    queda igual."""
    words = found.group(3).split()
    count = 0
    while count < len(words) and (fold(words[count]) in NUMBER_WORDS or (
            fold(words[count]) == "y" and count + 1 < len(words)
            and fold(words[count + 1]) in NUMBER_WORDS and count > 0)):
        count += 1
    if count == 0:
        return found.group(0)
    total = current = 0
    for word in (fold(w) for w in words[:count] if fold(w) != "y"):
        if word == "mil":
            total += max(current, 1) * 1000
            current = 0
        else:
            current += NUMBER_WORDS[word]
    rest = " ".join(words[count:])
    return f"{found.group(1)}{found.group(2)}{total + current}" + (f" {rest}" if rest else "")


def stated_province(municipality: str | None) -> str | None:
    """La provincia entre paréntesis tras el municipio: «Sahagún (León)» → «León»."""
    found = IN_PARENS.search(municipality or "")
    return found.group(1).strip() if found else None


def municipality_name(municipality: str) -> str:
    """El municipio sin la provincia entre paréntesis."""
    return IN_PARENS.sub("", municipality).strip()


def parcel_in_municipality(expected: str, address: str | None) -> bool:
    """La dirección catastral («CR CAMARMA 21 ALCALA DE HENARES (MADRID)») termina con el
    municipio, antes de la provincia entre paréntesis."""
    if not address:
        return False
    place = place_key(IN_PARENS.sub("", address))
    return any(re.search(rf"(?<!\w){re.escape(wanted)}$", place) is not None
               for wanted in _wanted(expected))


def same_municipality(expected: str, matched: str | None) -> bool:
    """El municipio esperado está en la localidad de la dirección encontrada.

    CartoCiudad devuelve «CALLE MAYOR 1, 28801 Alcalá de Henares»: la localidad va detrás de la
    primera coma. Se compara sin mayúsculas ni tildes y por palabras enteras.
    """
    if not matched or "," not in matched:
        return False
    place = place_key(matched.split(",", 1)[1])
    return any(re.search(rf"(?<!\w){re.escape(wanted)}(?!\w)", place) is not None
               for wanted in _wanted(expected))


def _wanted(expected: str) -> list[str]:
    """Las claves del municipio de la oferta en cualquiera de las lenguas oficiales
    (`geo/names.py`). Si nombra dos («Monforte de Lemos e Pobra de Brollón», un paraje entre
    los dos), vale cualquiera."""
    name = municipality_name(expected)
    names = [name, *re.split(r"\s+(?:y|e|i)\s+", name)]
    return [key for key in dict.fromkeys(place_key(n) for n in names) if key]


def _province(name: str) -> str:
    return PROVINCE_PREFIX.sub("", fold(name))
