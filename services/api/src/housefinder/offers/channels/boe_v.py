"""Canal BOE, sección V (F4.4): anuncios de venta o subasta de inmuebles del Estado.

Del sumario diario se toman los anuncios de la sección V cuyo título habla de vender o subastar
inmuebles, y de cada uno se descarga su texto en XML. El texto es libre y muy variado (lotes con
o sin numerar, referencias catastrales a veces, Madrid citado como sede de un registro y no como
ubicación), así que cada anuncio se guarda entero con la extracción pendiente: los lotes los
extraerá el LLM con su evidencia (F6.1). Ver docs/research/f4-volumen-boe.md.

Las correcciones de errores de esos anuncios no se extraen como anuncios nuevos: se enlazan con el
anuncio que corrigen (F4.4, `offers/corrections.py`) y, si ese anuncio no estaba guardado, se
guarda también.

Reutilización: condiciones de la Agencia Estatal BOE (citar la fuente con enlace y no
desnaturalizar el sentido).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from housefinder.ingestion.boe import KEYWORDS, BoeItem, fetch_sumario, iter_items
from housefinder.offers.corrections import (
    Resolution,
    is_sale_correction,
    parse_citation,
    resolve,
)
from housefinder.offers.model import NormalizedOffer, RawItem

NAME = "boe_seccion_v"
SOURCE_ID = "boe-seccion-v"
SOURCE_NAME = "BOE, sección V: anuncios de venta y subasta de inmuebles"
LICENSE = ("Condiciones de reutilización de la Agencia Estatal BOE (licencia tipo de 27/06/2024): "
           "citar la fuente con enlace a boe.es y no desnaturalizar el sentido")
LICENSE_URL = "https://www.boe.es/informacion/aviso_legal/index.php"
XML_URL = "https://www.boe.es/diario_boe/xml.php?id={id}"
HTML_URL = "https://www.boe.es/diario_boe/txt.php?id={id}"
METADATA = ("identificador", "departamento", "titulo", "fecha_publicacion", "seccion",
            "subseccion", "numero_anuncio")


def is_property_sale(section: str, title: str) -> bool:
    return section.startswith("5") and KEYWORDS.search(title) is not None


def parse_announcement(xml: bytes) -> dict[str, Any]:
    """Metadatos y párrafos del texto de un anuncio en XML."""
    root = ET.fromstring(xml)
    meta = root.find("metadatos")
    if meta is None:
        raise ValueError("El anuncio no tiene metadatos")
    text = root.find("texto")
    paragraphs = [] if text is None else [
        " ".join("".join(p.itertext()).split()) for p in text if "".join(p.itertext()).strip()
    ]
    return {"metadatos": {k: (meta.findtext(k) or "").strip() for k in METADATA},
            "texto": paragraphs}


@dataclass(frozen=True)
class CorrectionLog:
    correction: str  # BOE-B-… de la corrección
    original: str | None  # BOE-B-… del anuncio corregido, si se resolvió
    method: str  # cómo se resolvió, o por qué no
    kept: bool  # se guarda (corrige una venta de inmuebles)


class BoeSectionV:
    name = NAME
    source_id = SOURCE_ID

    def __init__(self, days: list[date]) -> None:
        self.days = days
        self.days_found: set[date] = set()  # días con BOE publicado
        self.corrections: list[CorrectionLog] = []
        self._sumarios: dict[date, list[BoeItem]] = {}

    def fetch(self, client: httpx.Client) -> Iterator[RawItem]:
        for day in self.days:
            payload = fetch_sumario(day, client)
            if payload is None:
                continue
            self.days_found.add(day)
            items = list(iter_items(payload, day))
            self._sumarios[day] = items
            for item in items:
                if item.section.startswith("5") and is_sale_correction(item.title):
                    yield from self._correction(client, item)
                elif is_property_sale(item.section, item.title):
                    yield self._announcement(client, item)

    def _announcement(self, client: httpx.Client, item: BoeItem) -> RawItem:
        response = client.get(XML_URL.format(id=item.identifier), timeout=60)
        response.raise_for_status()
        return RawItem(item.identifier, HTML_URL.format(id=item.identifier), item.published_on,
                       parse_announcement(response.content))

    def _correction(self, client: httpx.Client, item: BoeItem) -> Iterator[RawItem]:
        response = client.get(XML_URL.format(id=item.identifier), timeout=60)
        response.raise_for_status()
        announcement = parse_announcement(response.content)
        text = " ".join(announcement["texto"])
        citation = parse_citation(text, item.published_on)
        found = (resolve(item, text, citation, self._items_of(client, citation.published_on))
                 if citation else Resolution(None, "no cita un BOE anterior"))
        original = found.original
        sale = is_property_sale(item.section, item.title) or (
            original is not None and is_property_sale(original.section, original.title))
        self.corrections.append(CorrectionLog(item.identifier,
                                              original.identifier if original else None,
                                              found.method, sale))
        if not sale:
            return  # corrige la venta de otra cosa (vehículos, material…)
        if original is not None:
            yield self._announcement(client, original)  # por si no estaba guardado
        corrige = {"boe": original.identifier if original else None, "metodo": found.method,
                   "cita": citation.text if citation else None}
        yield RawItem(item.identifier, HTML_URL.format(id=item.identifier), item.published_on,
                      {**announcement, "corrige": corrige})

    def _items_of(self, client: httpx.Client, day: date) -> list[BoeItem]:
        if day not in self._sumarios:
            payload = fetch_sumario(day, client)
            self._sumarios[day] = [] if payload is None else list(iter_items(payload, day))
        return self._sumarios[day]

    def parse(self, item: RawItem) -> list[NormalizedOffer]:
        meta = item.raw["metadatos"]
        return [NormalizedOffer(
            external_id=item.external_id,
            kind="anuncio",
            url=item.url,
            title=meta.get("titulo") or None,
            published_on=item.published_on,
            description="\n".join(item.raw["texto"]) or None,
            # Una corrección no trae lotes nuevos: se enlaza con el anuncio que corrige.
            extraction_status="no_aplica" if "corrige" in item.raw else "pendiente",
        )]
