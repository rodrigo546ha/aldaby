"""Ingesta del sumario diario del BOE (datos abiertos).

Objetivo de la fase 4: detectar cada día los anuncios de venta o subasta de
inmuebles (sección V, sobre todo V-B: Seguridad Social, INVIED, Patrimonio del
Estado, ayuntamientos...).

Esquema comprobado con sumarios reales (tests/fixtures/boe/): `data.sumario.diario` (una
o varias ediciones; la extraordinaria va aparte) → `seccion` → `departamento` → `epigrafe` →
`item`. Cada nivel puede ser una lista o un objeto suelto, y con pocos elementos la API mete
un nivel `texto` en medio. Por eso el recorrido busca los objetos con `identificador` y
`titulo` y arrastra la sección y el departamento en los que aparecen.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

SUMARIO_URL = "https://www.boe.es/datosabiertos/api/boe/sumario/{yyyymmdd}"

# Venta o subasta y un bien inmueble, en cualquier orden («exclusión de una finca de la subasta»).
# «Bienes patrimoniales»: las subastas del Patrimonio del Estado, casi siempre inmuebles
# (docs/research/f4-filtro-seccion-v.md).
_SALE = r"subasta|enajenaci[oó]n|venta"
_PROPERTY = (r"inmuebles?|viviendas?|fincas?|locale?s?|pisos?|solar(?:es)?|parcelas?|terrenos?|"
             r"edificios?|naves?|garajes?|trasteros?|bienes patrimoniales")
KEYWORDS = re.compile(
    rf"\b(?:{_SALE})\b.*\b(?:{_PROPERTY})\b|\b(?:{_PROPERTY})\b.*\b(?:{_SALE})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BoeItem:
    identifier: str
    title: str
    url_pdf: str | None
    url_html: str | None
    published_on: date
    section: str = ""  # código de sección: '1', '3', '5B'…
    department: str = ""
    pages: tuple[int, int] | None = None  # páginas del diario (las del año, correlativas)


def fetch_sumario(day: date, client: httpx.Client | None = None) -> dict[str, Any] | None:
    """Sumario del día, o None si ese día no hay BOE (domingos y festivos dan 404)."""
    c = client or httpx.Client(timeout=30, headers={"Accept": "application/json"})
    resp = c.get(SUMARIO_URL.format(yyyymmdd=day.strftime("%Y%m%d")),
                 headers={"Accept": "application/json"})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


SKIP_KEYS = {"url_pdf", "url_html", "url_xml", "metadatos", "sumario_diario"}


def iter_items(
    payload: Any, day: date, section: str = "", department: str = "", key: str = ""
) -> Iterator[BoeItem]:
    """Todas las disposiciones del sumario, con su sección y departamento.

    El contexto sale de la clave bajo la que aparece cada objeto: lo que cuelga de `seccion`
    es una sección y lo de `departamento`, un departamento; los `texto` intermedios se cruzan.
    """
    if isinstance(payload, list):
        for value in payload:
            yield from iter_items(value, day, section, department, key)
        return
    if not isinstance(payload, dict):
        return
    if isinstance(payload.get("identificador"), str) and isinstance(payload.get("titulo"), str):
        yield BoeItem(
            identifier=payload["identificador"],
            title=" ".join(payload["titulo"].split()),
            url_pdf=_text(payload.get("url_pdf")),
            url_html=_text(payload.get("url_html")),
            published_on=day,
            section=section,
            department=department,
            pages=_pages(payload.get("url_pdf")),
        )
        return
    if key == "seccion":
        section = str(payload.get("codigo", section))
    elif key == "departamento":
        department = str(payload.get("nombre", department))
    for child_key, value in payload.items():
        if child_key not in SKIP_KEYS:
            yield from iter_items(value, day, section, department, child_key)


def property_sale_items(payload: Any, day: date) -> list[BoeItem]:
    """Anuncios que parecen ventas o subastas de inmuebles."""
    return [item for item in iter_items(payload, day) if KEYWORDS.search(item.title)]


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("texto") or value.get("url")
    return value if isinstance(value, str) else None


def _pages(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, dict):
        return None
    try:
        return int(value["pagina_inicial"]), int(value["pagina_final"])
    except (KeyError, TypeError, ValueError):
        return None
