"""Ingesta del sumario diario del BOE (datos abiertos).

Objetivo de la fase 4: detectar cada día los anuncios de venta o subasta de
inmuebles (sección V, sobre todo V-B: Seguridad Social, INVIED, Patrimonio del
Estado, ayuntamientos...).

PENDIENTE DE VERIFICAR en la fase 4: la URL y la estructura exacta de la API de
datos abiertos del BOE. El recorrido del JSON es deliberadamente tolerante
(busca cualquier objeto con "titulo") hasta fijar el esquema con un ejemplo real
guardado en tests/fixtures/.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

SUMARIO_URL = "https://www.boe.es/datosabiertos/api/boe/sumario/{yyyymmdd}"

KEYWORDS = re.compile(
    r"\b(subasta|enajenaci[oó]n|venta)\b.*\b(inmueble|vivienda|finca|local|piso)s?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BoeItem:
    identifier: str
    title: str
    url_pdf: str | None
    url_html: str | None
    published_on: date


def fetch_sumario(day: date, client: httpx.Client | None = None) -> dict[str, Any]:
    c = client or httpx.Client(timeout=30, headers={"Accept": "application/json"})
    resp = c.get(SUMARIO_URL.format(yyyymmdd=day.strftime("%Y%m%d")))
    resp.raise_for_status()
    return resp.json()


def iter_items(payload: Any, day: date) -> Iterator[BoeItem]:
    """Recorre el JSON y devuelve todo objeto con título (esquema por fijar)."""
    if isinstance(payload, dict):
        if "titulo" in payload and isinstance(payload["titulo"], str):
            yield BoeItem(
                identifier=str(payload.get("identificador", "")),
                title=payload["titulo"],
                url_pdf=_text(payload.get("url_pdf")),
                url_html=_text(payload.get("url_html")),
                published_on=day,
            )
        for value in payload.values():
            yield from iter_items(value, day)
    elif isinstance(payload, list):
        for value in payload:
            yield from iter_items(value, day)


def property_sale_items(payload: Any, day: date) -> list[BoeItem]:
    """Anuncios que parecen ventas o subastas de inmuebles."""
    return [item for item in iter_items(payload, day) if KEYWORDS.search(item.title)]


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("texto") or value.get("url")
    return value if isinstance(value, str) else None
