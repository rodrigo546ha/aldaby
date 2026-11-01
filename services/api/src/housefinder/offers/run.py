"""Canales de oferta como trabajos (ADR-0010)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx

from housefinder.agent.llm import LLMClient
from housefinder.db.connection import connect
from housefinder.db.offers import link_corrections
from housefinder.db.review_tasks import mark_issue_read, read_issues
from housefinder.db.sections import SourceRecord, upsert_source
from housefinder.geo.cartociudad import Geocoded, geocode
from housefinder.geo.catastro import Parcel, find_parcel, find_rustic_parcel
from housefinder.offers.channels import boe_subastas, boe_v
from housefinder.offers.extract import extract_pending
from housefinder.offers.ingest import IngestReport, ingest
from housefinder.offers.locate import RusticFinder, offer_locator
from housefinder.offers.pasted import extract_link

ISSUES = "offers_boe_v"  # días del BOE ya leídos por este canal
AUCTION_ISSUES = "offers_boe_subastas"


def run_boe_v(
    conninfo: str,
    client: httpx.Client,
    today: date,
    days: int = 7,
    geocoder: Callable[[str], Geocoded] | None = None,
    parcels: Callable[[str], Parcel] | None = None,
) -> dict[str, Any]:
    """Lee los días del BOE de los últimos `days` que este canal no ha leído aún.

    Las correcciones se enlazan con el anuncio que corrigen (F4.4); el informe dice cuáles se
    resolvieron y cómo, y cuáles no.
    """
    total = IngestReport()
    linked = 0
    corrections: list[dict[str, Any]] = []
    with connect(conninfo) as conn:
        upsert_source(conn, SourceRecord(boe_v.SOURCE_ID, boe_v.SOURCE_NAME, boe_v.LICENSE_URL,
                                         boe_v.LICENSE, datetime.now(UTC)))
        conn.commit()
        done = read_issues(conn, ISSUES)
        locate = offer_locator(conn, geocoder or (lambda address: geocode(client, address)),
                               parcels or (lambda ref: find_parcel(client, ref)))
        for offset in range(days):
            day = today - timedelta(days=offset)
            if day.isoformat() in done:
                continue
            channel = boe_v.BoeSectionV([day])
            report = ingest(conn, channel, channel.fetch(client), locate)
            linked += link_corrections(conn, boe_v.NAME)
            conn.commit()
            corrections += [log.__dict__ for log in channel.corrections]
            if day in channel.days_found or day < today:
                mark_issue_read(conn, ISSUES, day.isoformat(), report.items, report.offers_new)
                conn.commit()
            for key, value in report.as_dict().items():
                setattr(total, key, getattr(total, key) + value)
    return {**total.as_dict(), "corrections_linked": linked, "corrections": corrections}


def run_boe_auctions(conninfo: str, client: httpx.Client, today: date,
                     days: int = 7) -> dict[str, Any]:
    """Avisos de subastas judiciales de Madrid de los días del BOE aún no leídos (ADR-0017)."""
    seats = boe_subastas.load_court_seats()
    total = IngestReport()
    unparsed: list[str] = []
    with connect(conninfo) as conn:
        upsert_source(conn, SourceRecord(boe_subastas.SOURCE_ID, boe_subastas.SOURCE_NAME,
                                         boe_v.LICENSE_URL, boe_v.LICENSE, datetime.now(UTC)))
        conn.commit()
        done = read_issues(conn, AUCTION_ISSUES)
        for offset in range(days):
            day = today - timedelta(days=offset)
            if day.isoformat() in done:
                continue
            channel = boe_subastas.BoeAuctions([day], seats)
            report = ingest(conn, channel, channel.fetch(client), lambda offer: None)
            unparsed += channel.unparsed
            if day in channel.days_found or day < today:
                mark_issue_read(conn, AUCTION_ISSUES, day.isoformat(), report.items,
                                report.offers_new)
                conn.commit()
            for key, value in report.as_dict().items():
                setattr(total, key, getattr(total, key) + value)
    return {**total.as_dict(), "unparsed": unparsed, "court_seats_verified": seats.verified}


def extract_boe_v(
    conninfo: str,
    client: httpx.Client,
    llm: LLMClient,
    limit: int = 20,
    geocoder: Callable[[str], Geocoded] | None = None,
    parcels: Callable[[str], Parcel] | None = None,
    only: list[str] | None = None,
    rustic: RusticFinder | None = None,
) -> dict[str, Any]:
    """Extrae los lotes de hasta `limit` anuncios pendientes del BOE (ADR-0013); con `only`,
    solo esos (BOE-B-…). Antes, vuelve a ubicar los lotes que esperaban otro intento (ADR-0031);
    `unlocated` lista los que se quedan sin ubicar, con el motivo."""
    with connect(conninfo) as conn:
        locate = offer_locator(conn, geocoder or (lambda address: geocode(client, address)),
                               parcels or (lambda ref: find_parcel(client, ref)),
                               rustic or (lambda *args: find_rustic_parcel(client, *args)))
        return extract_pending(conn, llm, boe_v.NAME, locate, limit, only).as_dict()


def extract_pasted(conninfo: str, llm: LLMClient, offer_id: UUID) -> dict[str, Any]:
    """Extrae una oferta pegada por el usuario (F4.1)."""
    with connect(conninfo) as conn:
        return extract_link(conn, llm, offer_id)
