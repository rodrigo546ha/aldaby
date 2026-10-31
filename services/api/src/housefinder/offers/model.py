"""Oferta normalizada y contrato de un canal (G5).

Un canal descarga lo que publica su fuente (`RawItem`, que se guarda siempre tal cual) y lo
convierte en ofertas normalizadas. Lo que no sabe leer con reglas fiables lo deja como texto con
`extraction_status = 'pendiente'`: la extracción con el LLM (F6.1) y la confirmación del usuario
vienen después, nunca se adivina aquí.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal, Protocol

import httpx

OfferKind = Literal["anuncio", "lote", "enlace"]
ExtractionStatus = Literal["no_aplica", "pendiente", "extraida", "confirmada"]


@dataclass(frozen=True)
class RawItem:
    external_id: str  # identificador estable en la fuente: BOE-B-2026-35273
    url: str
    published_on: date | None
    raw: dict[str, Any]  # lo recibido, serializable en JSON

    @property
    def sha256(self) -> str:
        canonical = json.dumps(self.raw, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class NormalizedOffer:
    external_id: str
    kind: OfferKind
    url: str
    title: str | None = None
    published_on: date | None = None
    description: str | None = None
    asking_price: Decimal | None = None
    auction_min_bid: Decimal | None = None  # tipo de licitación en una subasta
    deposit_required: Decimal | None = None
    address: str | None = None
    cadastral_ref: str | None = None
    municipality: str | None = None  # para comprobar la geocodificación
    province: str | None = None  # fuera de la zona cubierta, no se geocodifica
    built_area_m2: Decimal | None = None
    lon: float | None = None  # si el canal ya trae el punto
    lat: float | None = None
    extraction_status: ExtractionStatus = "no_aplica"
    extracted: dict[str, Any] = field(default_factory=dict)

    @property
    def locatable(self) -> bool:
        return (self.lon is not None and self.lat is not None) or bool(
            self.address or self.cadastral_ref
        )


class Channel(Protocol):
    name: str  # 'boe_seccion_v'
    source_id: str  # fila de `sources`

    def fetch(self, client: httpx.Client) -> Iterator[RawItem]: ...

    def parse(self, item: RawItem) -> list[NormalizedOffer]: ...
