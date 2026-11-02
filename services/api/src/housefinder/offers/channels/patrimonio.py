"""Canal del Patrimonio del Estado (ADR-0037): ventas directas de inmuebles.

Una venta directa es un lote cuya subasta quedó desierta y que se vende por el tipo de salida
durante meses; no se anuncia en el BOE. Las subastas sí, y entran por `boe_seccion_v`, así que aquí
no se leen. De cada venta nueva o cambiada del RSS se descarga su ficha y, de su documentación, las
hojas de lote o la lista de lotes desiertos. El texto se guarda con la extracción pendiente, como
un anuncio del BOE: los lotes los saca el LLM con su cita (ADR-0013).

Reutilización: aviso legal del Ministerio de Hacienda (citar «Origen de los datos: Ministerio de
Hacienda» y la fecha de actualización).
"""

from __future__ import annotations

import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, unquote, urljoin
from urllib.robotparser import RobotFileParser

import httpx

from housefinder.ingestion.public_pdf import UnreadablePdf, pdf_pages
from housefinder.offers.model import NormalizedOffer, RawItem

NAME = "patrimonio_estado"
SOURCE_ID = "patrimonio-estado"
SOURCE_NAME = "Patrimonio del Estado: ventas directas de inmuebles"
LICENSE = ("Aviso legal del Ministerio de Hacienda: reutilización comercial permitida citando "
           "«Origen de los datos: Ministerio de Hacienda» y la fecha de actualización")
LICENSE_URL = "https://www.hacienda.gob.es/es-ES/Paginas/Avisolegal.aspx"
BASE = "https://www.hacienda.gob.es"
FEED_URL = f"{BASE}/_layouts/15/RssVentasDirectas.aspx?hiloId=15"
ROBOTS_URL = f"{BASE}/robots.txt"
AGENT = "HouseFinder"

# Documentos que no describen lo que se vende: formularios, instrucciones, actas…
NOT_DESCRIPTION = re.compile(
    r"solicitud|modelo|declaraci|instrucci|calificaci|plano|calendario|formulario|sobres|cuenta"
    r"|exclusi|acta|folleto|boe")
LOT_SHEET = re.compile(r"(?:^|/)l\d+[-_.]|\blotes?\b")
PAGE_NUMBER = re.compile(r"(?:pagina\s*)?\d{1,3}(?:\s*(?:de|/)\s*\d{1,3})?")


@dataclass(frozen=True)
class FeedItem:
    guid: str
    title: str
    link: str
    description: str
    pub_date: str  # tal como viene: sirve para saber si el elemento cambió

    @property
    def external_id(self) -> str:
        """Ruta de la ficha bajo /Paginas/: «Subastas/DEH-BADAJOZ/Subasta-DEH-Badajoz.aspx»."""
        path = unquote(self.guid)
        return path.split("/Paginas/", 1)[-1]

    @property
    def published_on(self) -> date | None:
        try:
            return parsedate_to_datetime(self.pub_date).date()
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True)
class Document:
    name: str  # el texto del enlace
    url: str  # absoluta


@dataclass(frozen=True)
class Ficha:
    title: str
    fields: dict[str, str]  # etiqueta → valor, sin la documentación
    documents: list[Document]


def parse_feed(content: bytes) -> list[FeedItem]:
    root = ET.fromstring(content)
    return [
        FeedItem((item.findtext("guid") or item.findtext("link") or "").strip(),
                 (item.findtext("title") or "").strip(), (item.findtext("link") or "").strip(),
                 (item.findtext("description") or "").strip(),
                 (item.findtext("pubDate") or "").strip())
        for item in root.iter("item")
    ]


def parse_ficha(html: bytes) -> Ficha:
    page = _FichaPage()
    page.feed(html.decode("utf-8", errors="replace"))
    page.close()
    fields = {k: v for k, v in page.fields.items() if k != "Documentación" and v}
    documents = [Document(text or url.rsplit("/", 1)[-1], urljoin(BASE + "/", url))
                 for url, text in page.links]
    return Ficha(" ".join(page.title.split()), fields, documents)


class _FichaPage(HTMLParser):
    """Título (`h1.titulo`), pares `dt.listaDT`/`dd.listaDD` y enlaces a PDF."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.fields: dict[str, str] = {}
        self.links: list[tuple[str, str]] = []
        self._in: str | None = None  # 'h1' | 'dt' | 'dd'
        self._depth = 0
        self._text: list[str] = []
        self._label = ""
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = (dict(attrs).get("class") or "").split()
        if self._in is None:
            if tag == "h1" and "titulo" in classes:
                self._start("h1")
            elif tag == "dt" and "listaDT" in classes:
                self._start("dt")
            elif tag == "dd" and "listaDD" in classes:
                self._start("dd")
            return
        if tag == self._in:
            self._depth += 1
        elif tag == "p":
            self._text.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            if href.lower().split("?")[0].endswith(".pdf"):
                self._href, self._link_text = href, []

    def handle_endtag(self, tag: str) -> None:
        if self._in is None:
            return
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._link_text).split())))
            self._href = None
        if tag != self._in:
            return
        if self._depth:
            self._depth -= 1
            return
        lines = [" ".join(line.split()) for line in "".join(self._text).split("\n")]
        text = "\n".join(line for line in lines if line)
        if self._in == "h1":
            self.title = text
        elif self._in == "dt":
            self._label = text
        elif self._label:
            self.fields[self._label] = text
        self._in = None

    def handle_data(self, data: str) -> None:
        if self._in is not None:
            self._text.append(data)
        if self._href is not None:
            self._link_text.append(data)

    def _start(self, kind: str) -> None:
        self._in, self._depth, self._text = kind, 0, []


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def describing_documents(ficha: Ficha) -> list[Document]:
    """Los PDF que describen lo que se vende: hojas de lote y listas de lotes desiertos. Nunca el
    pliego de la subasta original, que describe también lotes ya vendidos (ADR-0037)."""
    if ficha.fields.get("Precio") and ficha.fields.get("Superficie"):
        return []  # la ficha ya trae el lote
    chosen = []
    for doc in ficha.documents:
        name = fold(f"{doc.name} {unquote(doc.url).rsplit('/', 1)[-1]}")
        if NOT_DESCRIPTION.search(name) or "pliego" in name:
            continue
        if LOT_SHEET.search(name) or "desierto" in name:
            chosen.append(doc)
    return chosen


def document_lines(pages: list[str]) -> list[str]:
    """Una línea por párrafo, sin cabeceras ni pies que se repiten ni números de página."""
    per_page = [[" ".join(line.split()) for line in page.splitlines()] for page in pages]
    per_page = [[line for line in lines if line] for lines in per_page]
    seen = Counter(line for lines in per_page for line in set(lines))
    limit = max(2, math.ceil(len(pages) / 2)) if len(pages) > 1 else math.inf
    return [line for lines in per_page for line in lines
            if seen[line] < limit and not PAGE_NUMBER.fullmatch(fold(line))]


def ficha_lines(item: FeedItem, ficha: Ficha) -> list[str]:
    lines = [ficha.fields.get("Denominación") or item.title]
    lines += [f"{label}: {value}".replace("\n", " ")
              for label, value in ficha.fields.items()
              if label not in ("Denominación", "Dirección delegación", "Datos de contacto")]
    return lines


def hacienda_robots(client: httpx.Client) -> RobotFileParser:
    response = client.get(ROBOTS_URL, timeout=60)
    response.raise_for_status()
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser


def absolute(url: str) -> str:
    """La URL con espacios y tildes escapados, como la pide el servidor."""
    return quote(url, safe=":/?=&%#")


class PatrimonioEstado:
    name = NAME
    source_id = SOURCE_ID

    def __init__(self, known: dict[str, str] | None = None,
                 pdf_reader: Callable[[bytes], list[str]] = pdf_pages) -> None:
        self.known = known or {}  # external_id → pubDate de lo ya guardado: no se vuelve a bajar
        self.pdf_reader = pdf_reader
        self.unchanged = 0
        self.disallowed: list[str] = []  # URL que el robots.txt no deja leer
        self.unreadable: list[dict[str, str]] = []  # PDF ilegibles o sin texto

    def fetch(self, client: httpx.Client) -> Iterator[RawItem]:
        robots = hacienda_robots(client)
        if not robots.can_fetch(AGENT, FEED_URL):
            self.disallowed.append(FEED_URL)
            return
        response = client.get(FEED_URL, timeout=60)
        response.raise_for_status()
        for item in parse_feed(response.content):
            if self.known.get(item.external_id) == item.pub_date:
                self.unchanged += 1
                continue
            raw = self._item(client, robots, item)
            if raw is not None:
                yield RawItem(item.external_id, absolute(item.link), item.published_on, raw)

    def _item(self, client: httpx.Client, robots: RobotFileParser,
              item: FeedItem) -> dict[str, Any] | None:
        link = absolute(item.link)
        if not robots.can_fetch(AGENT, link):
            self.disallowed.append(link)
            return None
        response = client.get(link, timeout=60)
        response.raise_for_status()
        ficha = parse_ficha(response.content)
        lines = ficha_lines(item, ficha)
        documents: list[dict[str, Any]] = []
        for doc in describing_documents(ficha):
            url = absolute(doc.url)
            entry: dict[str, Any] = {"nombre": doc.name, "url": url}
            documents.append(entry)
            if not robots.can_fetch(AGENT, url):
                self.disallowed.append(url)
                entry["error"] = "robots.txt"
                continue
            try:
                pdf = client.get(url, timeout=120)
                pdf.raise_for_status()
                text = document_lines(self.pdf_reader(pdf.content))
            except (httpx.HTTPError, UnreadablePdf) as exc:
                entry["error"] = str(exc) or type(exc).__name__
                self.unreadable.append({"ficha": item.external_id, "url": url,
                                        "error": entry["error"]})
                continue
            if not text:
                entry["error"] = "sin texto (escaneado)"
                self.unreadable.append({"ficha": item.external_id, "url": url,
                                        "error": entry["error"]})
                continue
            lines += text
        return {
            "rss": {"guid": item.guid, "titulo": item.title,
                    "descripcion": item.description, "pubDate": item.pub_date},
            "ficha": {"titulo": ficha.title, **ficha.fields},
            "documentos": documents,
            "texto": lines,
        }

    def parse(self, item: RawItem) -> list[NormalizedOffer]:
        ficha = item.raw["ficha"]
        return [NormalizedOffer(
            external_id=item.external_id,
            kind="anuncio",
            url=item.url,
            title=ficha.get("Denominación") or ficha.get("titulo") or None,
            published_on=item.published_on,
            description="\n".join(item.raw["texto"]) or None,
            extraction_status="pendiente",
        )]
