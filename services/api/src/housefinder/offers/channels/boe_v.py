"""Canal BOE, sección V (F4.4): anuncios de venta o subasta de inmuebles del Estado.

Del sumario diario se toman los anuncios de la sección V cuyo título habla de vender o subastar
inmuebles, y de cada uno se descarga su texto en HTML (`txt.php`). No el XML (`xml.php`): el
`robots.txt` del BOE lo prohíbe, y también algunos documentos concretos, que no se descargan.
El texto es libre y muy variado (lotes con o sin numerar, referencias catastrales a veces,
Madrid citado como sede de un registro y no como ubicación), así que cada anuncio se guarda entero
con la extracción pendiente: los lotes los extraerá el LLM con su evidencia (F6.1). Ver
docs/research/f4-volumen-boe.md.

Las correcciones de errores de esos anuncios no se extraen como anuncios nuevos: se enlazan con el
anuncio que corrigen (F4.4, `offers/corrections.py`) y, si ese anuncio no estaba guardado, se
guarda también.

Reutilización: condiciones de la Agencia Estatal BOE (citar la fuente con enlace y no
desnaturalizar el sentido).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from typing import Any
from urllib.robotparser import RobotFileParser

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
HTML_URL = "https://www.boe.es/diario_boe/txt.php?id={id}"
ROBOTS_URL = "https://www.boe.es/robots.txt"
AGENT = "HouseFinder"
VOID_TAGS = {"br", "img", "hr", "wbr", "input", "meta", "link", "col", "area", "source"}


def is_property_sale(section: str, title: str) -> bool:
    return section.startswith("5") and KEYWORDS.search(title) is not None


def parse_announcement(html: bytes) -> dict[str, Any]:
    """Metadatos y párrafos del texto de un anuncio, de su página `txt.php`: cada elemento de
    primer nivel de `div#textoxslt` (párrafo o tabla) es un párrafo, como en el XML."""
    page = _TextPage()
    page.feed(html.decode("utf-8", errors="replace"))
    page.close()
    if not page.paragraphs and not page.meta.get("identificador"):
        raise ValueError("La página no tiene el texto de un anuncio del BOE")
    return {"metadatos": page.meta, "texto": page.paragraphs}


class _TextPage(HTMLParser):
    """Título (`h3.documento-tit`), departamento y referencia (`div.metadatos`) y párrafos."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.paragraphs: list[str] = []
        self._depth = 0  # dentro de div#textoxslt: niveles abiertos (0 = fuera)
        self._block: list[str] | None = None
        self._capture: str | None = None  # campo de metadatos que se está leyendo
        self._label = ""
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self._depth:
            if tag in VOID_TAGS:
                if self._block is not None:
                    self._block.append(" ")
                return
            self._depth += 1
            if self._depth == 2:
                self._block = []
            return
        if tag == "div" and attributes.get("id") == "textoxslt":
            self._depth = 1
        elif tag == "h3" and "documento-tit" in (attributes.get("class") or ""):
            self._start("titulo")
        elif tag == "dt":
            self._start("dt")
        elif tag == "dd":
            field = {"Departamento:": "departamento", "Referencia:": "identificador"}
            self._start(field.get(self._label, "dd"))

    def handle_endtag(self, tag: str) -> None:
        if self._depth:
            if tag in VOID_TAGS:
                return
            self._depth -= 1
            if self._depth == 1 and self._block is not None:
                text = " ".join("".join(self._block).split())
                if text:
                    self.paragraphs.append(text)
                self._block = None
            return
        if self._capture is not None and tag in ("h3", "dt", "dd"):
            text = " ".join("".join(self._buffer).split())
            if self._capture == "dt":
                self._label = text
            elif self._capture != "dd":
                self.meta[self._capture] = text
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._block is not None:
            self._block.append(data)
        elif self._capture is not None:
            self._buffer.append(data)

    def _start(self, field: str) -> None:
        self._capture = field
        self._buffer = []


def boe_robots(client: httpx.Client) -> RobotFileParser:
    """El `robots.txt` del BOE, leído una vez por ejecución."""
    response = client.get(ROBOTS_URL, timeout=60)
    response.raise_for_status()
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser


def fetch_announcement(client: httpx.Client, item: BoeItem,
                       robots: RobotFileParser) -> dict[str, Any] | None:
    """El anuncio de su página de texto, con los metadatos del sumario; None si el `robots.txt`
    del BOE no permite descargarlo."""
    url = HTML_URL.format(id=item.identifier)
    if not robots.can_fetch(AGENT, url):
        return None
    response = client.get(url, timeout=60)
    response.raise_for_status()
    announcement = parse_announcement(response.content)
    announcement["metadatos"] = {
        "identificador": item.identifier, "titulo": item.title,
        "departamento": item.department, "fecha_publicacion": item.published_on.isoformat(),
        "seccion": item.section, **{k: v for k, v in announcement["metadatos"].items() if v},
    }
    return announcement


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
        self.disallowed: list[str] = []  # anuncios que el robots.txt del BOE no deja descargar
        self._sumarios: dict[date, list[BoeItem]] = {}
        self._robots: RobotFileParser | None = None

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
                    yield from self._announcement(client, item)

    def _document(self, client: httpx.Client, item: BoeItem) -> dict[str, Any] | None:
        if self._robots is None:
            self._robots = boe_robots(client)
        announcement = fetch_announcement(client, item, self._robots)
        if announcement is None:
            self.disallowed.append(item.identifier)
        return announcement

    def _announcement(self, client: httpx.Client, item: BoeItem) -> Iterator[RawItem]:
        announcement = self._document(client, item)
        if announcement is not None:
            yield RawItem(item.identifier, HTML_URL.format(id=item.identifier),
                          item.published_on, announcement)

    def _correction(self, client: httpx.Client, item: BoeItem) -> Iterator[RawItem]:
        announcement = self._document(client, item)
        if announcement is None:
            return
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
            yield from self._announcement(client, original)  # por si no estaba guardado
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
