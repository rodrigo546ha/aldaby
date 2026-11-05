"""Canal BOE, sección IV (F4.3, ADR-0017): avisos de subastas judiciales de toda España.

Cada subasta judicial tiene un aviso en la sección IV del BOE, cuyo título es la localidad del
juzgado. Con `all_spain` se guardan los de todos los juzgados (ADR-0053, enmienda del 2026-11-05);
sin él, solo los de las sedes de partidos judiciales de `data/offers/subastas_boe.yaml`. El aviso
solo trae el juzgado, el tipo de subasta, el número del procedimiento y el enlace al Portal; el
usuario abre el enlace y pega el texto del lote (F4.1).

Reutilización: condiciones de la Agencia Estatal BOE (citar la fuente con enlace).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.robotparser import RobotFileParser

import httpx
import yaml

from housefinder.ingestion.boe import fetch_sumario, iter_items
from housefinder.offers.channels.boe_v import HTML_URL, boe_robots, fetch_announcement
from housefinder.offers.model import NormalizedOffer, RawItem

NAME = "boe_subastas_judiciales"
SOURCE_ID = "boe-seccion-iv-subastas"
SOURCE_NAME = "BOE, sección IV: avisos de subastas judiciales del Portal de Subastas"

PORTAL_ID = re.compile(r"https://subastas\.boe\.es/\S*?id=(SUB-[A-Z]{2}-\d{4}-\d+)")
KIND = re.compile(r"Anuncio de subasta (.+?) con número de identificación")
PROCEDURE = re.compile(r"número de identificación ([0-9A-Z/-]+)")
COURT = re.compile(r"^(.*?)\.-\s*Anuncio de subasta")


@dataclass(frozen=True)
class AuctionNotice:
    portal_id: str  # SUB-JA-2026-267866
    portal_url: str
    court: str | None  # «Sección Civil TI Madrid. Plz.n 31»
    kind: str | None  # «judicial en vía de apremio»
    procedure: str | None


@dataclass(frozen=True)
class CourtSeats:
    seats: frozenset[str]  # plegadas: sin tildes ni mayúsculas
    verified: bool
    all_spain: bool = False

    def matches(self, locality: str) -> bool:
        if self.all_spain:
            return True
        return fold(locality) in self.seats


def default_config_path() -> Path:
    """services/api/data/offers/subastas_boe.yaml"""
    return Path(__file__).resolve().parents[4] / "data" / "offers" / "subastas_boe.yaml"


def load_court_seats(path: Path | None = None, all_spain: bool = False) -> CourtSeats:
    if all_spain:
        return CourtSeats(frozenset(), True, all_spain=True)
    data = yaml.safe_load((path or default_config_path()).read_text(encoding="utf-8"))
    return CourtSeats(
        frozenset(fold(s) for s in data["court_seats"]),
        bool(data.get("verified", False)),
        all_spain=bool(data.get("all_spain", False)),
    )


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def parse_notice(text: str) -> AuctionNotice | None:
    """Datos del aviso; None si no enlaza a una subasta del Portal."""
    link = PORTAL_ID.search(text)
    if link is None:
        return None
    court, kind, procedure = COURT.search(text), KIND.search(text), PROCEDURE.search(text)
    return AuctionNotice(
        portal_id=link.group(1),
        portal_url=link.group(0),
        court=court.group(1).strip() if court else None,
        kind=kind.group(1).strip() if kind else None,
        procedure=procedure.group(1).rstrip(".") if procedure else None,
    )


class BoeAuctions:
    name = NAME
    source_id = SOURCE_ID

    def __init__(self, days: list[date], seats: CourtSeats) -> None:
        self.days = days
        self.seats = seats
        self.days_found: set[date] = set()
        self.unparsed: list[str] = []  # avisos sin enlace al Portal
        self.disallowed: list[str] = []  # avisos que el robots.txt del BOE no deja descargar

    def fetch(self, client: httpx.Client) -> Iterator[RawItem]:
        robots: RobotFileParser | None = None
        for day in self.days:
            payload = fetch_sumario(day, client)
            if payload is None:
                continue
            self.days_found.add(day)
            for item in iter_items(payload, day):
                if item.section != "4" or not self.seats.matches(item.title):
                    continue
                if robots is None:
                    robots = boe_robots(client)
                announcement = fetch_announcement(client, item, robots)
                if announcement is None:
                    self.disallowed.append(item.identifier)
                    continue
                notice = parse_notice(" ".join(announcement["texto"]))
                if notice is None:
                    self.unparsed.append(item.identifier)
                    continue
                raw: dict[str, Any] = {**announcement, "aviso": notice.__dict__,
                                       "boe": HTML_URL.format(id=item.identifier)}
                yield RawItem(notice.portal_id, notice.portal_url, day, raw)

    def parse(self, item: RawItem) -> list[NormalizedOffer]:
        notice = item.raw["aviso"]
        kind = notice.get("kind")
        label = f"Subasta {kind}" if kind else "Subasta judicial"
        court = notice.get("court")
        return [NormalizedOffer(
            external_id=item.external_id,
            kind="anuncio",
            url=item.url,
            title=f"{label} · {court}" if court else label,
            published_on=item.published_on,
            description="\n".join(item.raw.get("texto", [])) or None,
            extraction_status="no_aplica",
        )]
