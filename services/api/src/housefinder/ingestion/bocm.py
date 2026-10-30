"""Sumarios del Boletín Oficial de la Comunidad de Madrid (BOCM) para la vigilancia (F2.6).

- `sumarios.rss`: los últimos veinte boletines (fecha, número y página del boletín).
- La página de cada boletín enlaza su sumario en XML: `seccion` → `apartado` → `organismo` →
  `disposicion` (identificador CVE, título y enlaces).

Solo se guardan títulos y enlaces de disposiciones oficiales. Entre petición y petición se esperan
los 10 segundos que pide su `robots.txt` (`Crawl-delay: 10`).
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date

import httpx

BASE = "https://www.bocm.es"
SUMMARIES_RSS = f"{BASE}/sumarios.rss"
BULLETIN_LINK = re.compile(r"/boletin-completo/BOCM-(\d{8})/(\d+)")
SUMMARY_XML = re.compile(r'href="(/boletin/CM_Boletin_BOCM/[^"]+\.xml)"')
CRAWL_DELAY = 10.0  # robots.txt de www.bocm.es: «Crawl-delay: 10»


@dataclass
class Pace:
    """Separa las peticiones al BOCM al menos `seconds` segundos."""

    seconds: float = CRAWL_DELAY
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    _last: float | None = field(default=None, repr=False)

    def wait(self) -> None:
        if self._last is not None:
            remaining = self.seconds - (self.clock() - self._last)
            if remaining > 0:
                self.sleep(remaining)
        self._last = self.clock()


@dataclass(frozen=True)
class Bulletin:
    published_on: date
    number: int
    page_url: str


@dataclass(frozen=True)
class BocmItem:
    identifier: str  # CVE: BOCM-20261029-1
    title: str
    url: str
    published_on: date
    section: str  # 'I. COMUNIDAD DE MADRID'
    part: str  # apartado: 'A) Disposiciones Generales'
    body: str  # organismo


def parse_bulletins(rss: bytes) -> list[Bulletin]:
    """Boletines del RSS de sumarios, del más reciente al más antiguo."""
    root = ET.fromstring(rss)
    result: list[Bulletin] = []
    for item in root.iter("item"):
        link = item.findtext("link") or ""
        match = BULLETIN_LINK.search(link)
        if match is None:
            continue
        day, number = match.groups()
        result.append(Bulletin(date(int(day[:4]), int(day[4:6]), int(day[6:])), int(number),
                               link))
    return result


def summary_xml_url(page_html: str) -> str:
    match = SUMMARY_XML.search(page_html)
    if match is None:
        raise ValueError("La página del boletín no enlaza su sumario en XML")
    return BASE + match.group(1)


def parse_summary(xml: bytes) -> Iterator[BocmItem]:
    root = ET.fromstring(xml)
    raw_day = root.findtext("metadatos/fecha_publicacion") or ""
    if not re.fullmatch(r"\d{4}/\d{2}/\d{2}", raw_day):
        raise ValueError(f"Fecha de publicación no válida en el sumario: {raw_day!r}")
    day = date(int(raw_day[:4]), int(raw_day[5:7]), int(raw_day[8:]))
    for section in root.iter("seccion"):
        for part in _children_or_self(section, "apartado"):
            for body in _children_or_self(part, "organismo"):
                for item in body.iter("disposicion"):
                    identifier = (item.findtext("identificador") or "").strip()
                    if not identifier:
                        continue
                    yield BocmItem(
                        identifier=identifier,
                        title=" ".join((item.findtext("titulo") or "").split()),
                        url=(item.findtext("url_html") or "").strip(),
                        published_on=day,
                        section=section.get("nombre", ""),
                        part=part.get("nombre") or "",
                        body=body.get("nombre") or "",
                    )


def fetch_bulletins(client: httpx.Client, pace: Pace) -> list[Bulletin]:
    """Los últimos veinte boletines, según el RSS de sumarios."""
    pace.wait()
    response = client.get(SUMMARIES_RSS, timeout=60)
    response.raise_for_status()
    return parse_bulletins(response.content)


def fetch_bulletin_items(client: httpx.Client, bulletin: Bulletin,
                         pace: Pace) -> list[BocmItem]:
    """Disposiciones de un boletín: su página da el enlace al sumario en XML."""
    pace.wait()
    page = client.get(bulletin.page_url, timeout=60)
    page.raise_for_status()
    pace.wait()
    xml = client.get(summary_xml_url(page.text), timeout=60)
    xml.raise_for_status()
    return list(parse_summary(xml.content))


def bulletin_key(bulletin: Bulletin) -> str:
    return f"BOCM-{bulletin.published_on:%Y%m%d}-{bulletin.number}"


def _children_or_self(element: ET.Element, tag: str) -> list[ET.Element]:
    """Hijos con esa etiqueta; si no los hay (secciones sin apartados), el propio elemento."""
    children = element.findall(tag)
    return children or [element]
