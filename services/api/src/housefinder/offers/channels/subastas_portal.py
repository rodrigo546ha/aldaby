"""Canal del Portal de Subastas del BOE (ADR-0049, ADR-0053): subastas de inmuebles como lotes.

Busca las subastas de inmuebles de una provincia celebrándose y en próxima apertura y descarga las
pestañas de las nuevas o de las que cambiaron de estado o de fecha de conclusión. Cada lote es una
oferta pública con el valor de subasta como tipo. Con la referencia catastral completa, la
superficie construida y el uso salen del Catastro (`Consulta_DNPRC`); se piden aquí, al descargar,
para que `parse` no salga a la red. Los documentos y la extracción con IA no se leen aquí: son
caros y van bajo demanda.

Reutilización: «Fuente: Agencia Estatal Boletín Oficial del Estado» (aviso legal del BOE).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from housefinder.geo.catastro import CadastralUnit, ParcelNotFound, find_unit
from housefinder.offers import boe_portal
from housefinder.offers.model import NormalizedOffer, RawItem

NAME = "boe_subasta_portal"
SOURCE_ID = "boe-portal-subastas"
SOURCE_NAME = "Portal de Subastas de la Agencia Estatal BOE"
STATUSES = ("EJ", "PU")  # celebrándose y próxima apertura
PAGE_HITS = 500  # una página con todas: Madrid tenía 67 el 2026-11-04
MAX_AUCTIONS = 100  # por ejecución: el resto, al día siguiente
PAUSE_S = 1.0  # entre subastas: cada una son cinco o seis páginas del Portal


def search_state(result: boe_portal.AuctionSearchResult) -> str:
    """Lo que, si cambia en la búsqueda, hace volver a descargar la subasta."""
    return f"{result.status or ''}|{result.conclusion_date or ''}"


@dataclass
class PortalAuctions:
    """`known`: estado de la búsqueda de cada subasta ya guardada (`portal_states`)."""

    known: dict[str, str]
    province: str = "28"
    units: Callable[[str], CadastralUnit] | None = None  # Catastro; None: con el mismo cliente
    pause_s: float = PAUSE_S
    limit: int = MAX_AUCTIONS
    name: str = NAME
    source_id: str = SOURCE_ID
    unchanged: int = 0
    postponed: int = 0  # por encima del límite
    failed: list[str] = field(default_factory=list)  # subastas que el Portal no devolvió

    def fetch(self, client: httpx.Client) -> Iterator[RawItem]:
        units = self.units or (lambda ref: find_unit(client, ref))
        seen: set[str] = set()
        fetched = 0
        for status in STATUSES:
            results = boe_portal.search_boe_auctions(
                client, province=self.province, status=status, goods_type="I",
                page_hits=PAGE_HITS)
            for result in results:
                if result.portal_id in seen:
                    continue
                seen.add(result.portal_id)
                state = search_state(result)
                if self.known.get(result.portal_id) == state:
                    self.unchanged += 1
                    continue
                if fetched >= self.limit:
                    self.postponed += 1
                    continue
                if fetched:
                    time.sleep(self.pause_s)
                fetched += 1
                try:
                    auction = boe_portal.scrape_auction(client, result.portal_id)
                except (httpx.HTTPError, ValueError):
                    self.failed.append(result.portal_id)
                    continue
                records = boe_portal.lot_records(auction, result)
                yield RawItem(
                    external_id=auction.portal_id, url=auction.portal_url, published_on=None,
                    raw={"search": {**result.__dict__, "state": state}, "lots": records,
                         "catastro": _units(records, units), "html": auction.raw_html})

    def parse(self, item: RawItem) -> list[NormalizedOffer]:
        catastro = item.raw.get("catastro") or {}
        return [boe_portal.offer_from_record(record, catastro.get(record["cadastral_ref"] or ""))
                for record in item.raw.get("lots") or []]


def _units(records: list[dict[str, Any]],
           units: Callable[[str], CadastralUnit]) -> dict[str, dict[str, Any]]:
    """Superficie y uso de cada referencia completa de los lotes; las que no se encuentran, no."""
    found: dict[str, dict[str, Any]] = {}
    for ref in {r["cadastral_ref"] for r in records if r.get("cadastral_ref")}:
        try:
            unit = units(ref)
        except ParcelNotFound:
            continue
        found[ref] = {"ref": unit.ref, "built_area_m2": str(unit.built_area_m2),
                      "use": unit.use, "built_year": unit.built_year,
                      "source": "Dirección General del Catastro (Consulta_DNPRC)"}
    return found
