"""Catálogo de ofertas (ADR-0054): una sola lista de inmuebles, venga del canal que venga.

El usuario piensa en pisos, no en canales. Cada oferta se cuenta igual: qué es y dónde está, cómo se
vende (subasta judicial, administrativa o notarial, venta directa, agencia o su propio anuncio), su
precio o valor de subasta, el depósito, la superficie y, en las subastas del Portal, cuándo
terminan y si consta la posesión. Lo que no decide (identificadores del BOE, sección censal, citas
de la extracción) se queda en el detalle de la fuente. Ninguna cifra se calcula aquí: se copian
las del anuncio.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from housefinder.db.offers import CatalogRow
from housefinder.offers.locate import Provinces

Channel = Literal["subasta_judicial", "subasta_administrativa", "subasta_notarial",
                  "venta_directa", "agencia", "tu_anuncio"]
PriceKind = Literal["precio", "valor_subasta"]

TYPE_LABEL = {
    "vivienda": "Vivienda", "local": "Local", "oficina": "Oficina", "garaje": "Garaje",
    "trastero": "Trastero", "edificio": "Edificio", "suelo": "Suelo", "rustica": "Finca rústica",
    "otro": "Inmueble",
}
SOURCE_NAME = {
    "boe_seccion_v": "BOE",
    "boe_subasta_portal": "Portal de Subastas del BOE",
    "patrimonio_estado": "Patrimonio del Estado",
    "url_usuario": "Tu anuncio",
}
PORTAL_ORIGIN = re.compile(r"^Subasta (judicial|administrativa|notarial)\b")
DAY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
LOWER = {"de", "del", "la", "las", "los", "el", "y", "en", "a", "d'", "l'"}
PARENS = re.compile(r"\s*\([^)]*\)\s*")
NOT_STATED = "no consta"
PARCEL_REF = re.compile(r"^[0-9A-Z]{14}")


@dataclass(frozen=True)
class CatalogItem:
    offer_id: UUID
    channel: Channel
    title: str  # «Vivienda en Almuñécar»
    address: str | None
    place: str | None  # «Almuñécar · Granada»
    property_type: str | None
    price: Decimal | None
    price_kind: PriceKind
    deposit: Decimal | None
    built_area_m2: Decimal | None
    ends_on: date | None  # fin de la subasta (Portal) o del plazo de la venta directa
    auction_state: str | None  # del Portal: «Celebrándose», «Próxima apertura»
    possession: str | None  # del Portal, solo si consta
    habitual_residence: bool | None  # vivienda habitual del deudor, si el Portal lo dice
    published_on: date | None
    status: Literal["publicada", "por_confirmar"]  # un anuncio pegado sin confirmar
    lon: float | None
    lat: float | None
    has_facade: bool  # hay referencia catastral para pedir la foto de fachada
    images: tuple[str, ...]  # las del anuncio pegado (URL del propio anuncio)
    source_name: str
    source_url: str | None
    original_title: str | None  # el título largo de la fuente, para el detalle
    corrected: bool = False  # hay una corrección posterior del anuncio en el BOE
    approximate: bool = False  # el punto es el centro del municipio, no el del inmueble

    @property
    def exact(self) -> bool:
        """Ubicada de verdad: con inmueble y sección (la ortofoto y el plan la usan)."""
        return self.lon is not None and not self.approximate

    @property
    def auction(self) -> bool:
        return self.channel.startswith("subasta_")


def channel_of(row: CatalogRow) -> Channel:
    """Cómo se vende la oferta, que es lo que cambia lo que hay que hacer para comprarla."""
    if row.kind == "enlace":
        return "tu_anuncio"
    if row.channel == "feed_agencia":
        return "agencia"
    if row.channel == "patrimonio_estado":
        return "venta_directa"
    if row.channel == "boe_subasta_portal":
        found = PORTAL_ORIGIN.match(row.title or "")
        origin = found.group(1) if found else "judicial"
        return f"subasta_{origin}"  # type: ignore[return-value]
    return "subasta_administrativa"  # BOE sección V: Hacienda, Seguridad Social, organismos


def _mixed_case(text: str) -> bool:
    """Si ya trae minúsculas («Nº» y «1ª» no cuentan: son abreviaturas)."""
    return any(c.islower() for c in text if c not in "ºª")


def place_name(text: str | None) -> str | None:
    """«ALCOLEA DEL PINAR (Guadalajara)» → «Alcolea del Pinar»."""
    if not text:
        return None
    words = PARENS.sub(" ", text).strip(" ,.").split()
    if not words:
        return None
    if _mixed_case("".join(words)):
        return " ".join(words)  # ya viene escrito con mayúsculas y minúsculas
    out = []
    for i, word in enumerate(words):
        low = word.lower()
        out.append(low if i and low in LOWER else low[:1].upper() + low[1:])
    return " ".join(out)


def _verified(extracted: dict[str, Any], name: str) -> str | None:
    """El dato confirmado por el usuario (anuncio pegado) o, si no, el extraído con su cita."""
    confirmed = (extracted.get("confirmed") or {}).get("fields") or {}
    if isinstance(confirmed.get(name), dict) and confirmed[name].get("value"):
        return str(confirmed[name]["value"])
    field = extracted.get(name)
    if isinstance(field, dict) and field.get("status") == "verificado":
        value = field.get("value")
        return str(value) if value else None
    return None


def _day(text: str | None) -> date | None:
    found = DAY.search(text or "")
    if not found:
        return None
    day, month, year = (int(g) for g in found.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _state(status: Any) -> str | None:
    """«Celebrándose - [Conclusión prevista: …]» → «Celebrándose»."""
    if not isinstance(status, str) or not status.strip():
        return None
    return status.split(" - ")[0].split("[")[0].strip() or None


def _address(text: str | None) -> str | None:
    """«CALLE MERCURIO 36, CUARTO DERECHA» → «Calle Mercurio 36, Cuarto Derecha»."""
    if not text or _mixed_case(text):
        return text
    return place_name(text.replace(",", " , ")).replace(" ,", ",") if text.strip() else None


def _possession(text: str | None) -> str | None:
    """Lo que dice el Portal de la posesión, sin paréntesis: ahí puede ir el nombre del titular."""
    if not text:
        return None
    short = PARENS.sub(" ", text).strip(" .;,")
    return None if not short or short.lower().startswith(NOT_STATED) else short


def _yes_no(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("sí", "si", "no"):
        return value.strip().lower() != "no"
    return None


def catalog_item(row: CatalogRow, provinces: Provinces) -> CatalogItem:
    extracted = row.extracted or {}
    portal = extracted.get("portal") if isinstance(extracted.get("portal"), dict) else {}
    channel = channel_of(row)
    listing = extracted.get("listing") if isinstance(extracted.get("listing"), dict) else {}
    property_type = next((t for t in (extracted.get("property_type"),
                                      listing.get("property_type")) if isinstance(t, str)), None)
    town = place_name(_verified(extracted, "municipality") or row.town)
    province = (provinces.name(row.municipality_code[:2]) if row.municipality_code else None) \
        or place_name(_verified(extracted, "province"))
    if town and province and town.casefold() == province.casefold():
        province = None
    place = " · ".join(p for p in (town, province) if p) or None
    kind_label = TYPE_LABEL.get(property_type or "", "Inmueble")
    title = f"{kind_label} en {town}" if town else (
        row.title if channel in ("tu_anuncio", "agencia") and row.title else kind_label)
    if row.asking_price is not None:
        price, price_kind = row.asking_price, "precio"
    else:
        listed = _verified(extracted, "price")
        price = row.auction_min_bid if row.auction_min_bid is not None else (
            Decimal(listed) if listed else None)
        price_kind = "valor_subasta" if channel.startswith("subasta_") else "precio"
    deposit = row.deposit_required
    if deposit is None and (listed_deposit := _verified(extracted, "deposit")):
        deposit = Decimal(listed_deposit)
    area = row.built_area_m2
    if area is None and (listed_area := _verified(extracted, "built_area_m2")):
        area = Decimal(listed_area)
    possession = portal.get("possession") if isinstance(portal.get("possession"), str) else None
    ref = (row.cadastral_ref or _verified(extracted, "cadastral_ref") or "").replace(" ", "")
    return CatalogItem(
        offer_id=row.id, channel=channel, title=title,
        address=_address(row.address or _verified(extracted, "address")),
        place=place, property_type=property_type, price=price,
        price_kind=price_kind,  # type: ignore[arg-type]
        deposit=deposit, built_area_m2=area,
        ends_on=_day(portal.get("concludes")) or _day(row.deadline),
        possession=_possession(possession),
        auction_state=_state(portal.get("status")),
        habitual_residence=_yes_no(portal.get("habitual_residence")),
        published_on=row.published_on,
        status="por_confirmar" if row.kind == "enlace" and row.extraction_status != "confirmada"
        else "publicada",
        lon=row.lon if row.lon is not None else row.approx_lon,
        lat=row.lat if row.lat is not None else row.approx_lat,
        approximate=row.lon is None and row.approx_lon is not None,
        has_facade=bool(PARCEL_REF.match(ref.upper())),
        images=tuple(str(i) for i in (row.images or []) if str(i).startswith("https://"))[:4],
        source_name=row.source_name if channel == "agencia" and row.source_name
        else SOURCE_NAME.get(row.channel, "Anuncio"),
        source_url=row.url or row.parent_url,
        original_title=row.title,
        corrected=row.corrected,
    )


def parcel_ref(row: CatalogRow) -> str | None:
    """Los 14 caracteres de la parcela, para la foto de fachada."""
    ref = (row.cadastral_ref or _verified(row.extracted or {}, "cadastral_ref") or "")
    ref = ref.replace(" ", "").upper()
    return ref[:14] if PARCEL_REF.match(ref) else None
