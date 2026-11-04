"""Canales de oferta como trabajos (ADR-0010)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx

from housefinder.agent.llm import LLMClient
from housefinder.db.connection import connect
from housefinder.db.offers import link_corrections, portal_states, rss_dates, unlocated_lots
from housefinder.db.review_tasks import mark_issue_read, read_issues
from housefinder.db.sections import SourceRecord, upsert_source
from housefinder.geo.cartociudad import Geocoded, geocode, municipality_codes
from housefinder.geo.catastro import CadastralUnit, Parcel, find_parcel, find_rustic_parcel
from housefinder.geo.foral import find_foral_parcel
from housefinder.offers.channels import boe_subastas, boe_v, patrimonio, subastas_portal
from housefinder.offers.extract import extract_pending, relocated_offer
from housefinder.offers.ingest import IngestReport, ingest, locate_and_link
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
                               parcels or (lambda ref: find_parcel(client, ref)),
                               municipalities=lambda name: municipality_codes(client, name),
                               foral=lambda province, key: find_foral_parcel(client, province, key))
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


def run_boe_portal(
    conninfo: str,
    client: httpx.Client,
    province: str = "28",
    geocoder: Callable[[str], Geocoded] | None = None,
    parcels: Callable[[str], Parcel] | None = None,
    units: Callable[[str], CadastralUnit] | None = None,
    pause_s: float = subastas_portal.PAUSE_S,
) -> dict[str, Any]:
    """Subastas de inmuebles del Portal del BOE nuevas o cambiadas, como lotes ubicados
    (ADR-0053)."""
    with connect(conninfo) as conn:
        upsert_source(conn, SourceRecord(subastas_portal.SOURCE_ID, subastas_portal.SOURCE_NAME,
                                         boe_v.LICENSE_URL, boe_v.LICENSE, datetime.now(UTC)))
        conn.commit()
        locate = offer_locator(conn, geocoder or (lambda address: geocode(client, address)),
                               parcels or (lambda ref: find_parcel(client, ref)),
                               municipalities=lambda name: municipality_codes(client, name),
                               foral=lambda province, key: find_foral_parcel(client, province, key))
        channel = subastas_portal.PortalAuctions(portal_states(conn, subastas_portal.NAME),
                                                 province, units, pause_s)
        report = ingest(conn, channel, channel.fetch(client), locate)
    return {**report.as_dict(), "unchanged": channel.unchanged, "postponed": channel.postponed,
            "failed": channel.failed}


def run_patrimonio(conninfo: str, client: httpx.Client,
                   pdf_reader: Callable[[bytes], list[str]] = patrimonio.pdf_pages
                   ) -> dict[str, Any]:
    """Ventas directas del Patrimonio del Estado nuevas o cambiadas (ADR-0037). Se ubican al
    extraer sus lotes, como los anuncios del BOE."""
    with connect(conninfo) as conn:
        upsert_source(conn, SourceRecord(patrimonio.SOURCE_ID, patrimonio.SOURCE_NAME,
                                         patrimonio.LICENSE_URL, patrimonio.LICENSE,
                                         datetime.now(UTC)))
        conn.commit()
        channel = patrimonio.PatrimonioEstado(rss_dates(conn, patrimonio.NAME), pdf_reader)
        report = ingest(conn, channel, channel.fetch(client), lambda offer: None)
    return {**report.as_dict(), "unchanged": channel.unchanged, "disallowed": channel.disallowed,
            "unreadable": channel.unreadable}


def extract_boe_v(
    conninfo: str,
    client: httpx.Client,
    llm: LLMClient,
    limit: int = 20,
    geocoder: Callable[[str], Geocoded] | None = None,
    parcels: Callable[[str], Parcel] | None = None,
    only: list[str] | None = None,
    rustic: RusticFinder | None = None,
    municipalities: Callable[[str], frozenset[str]] | None = None,
    foral: Callable[[str, str], Parcel] | None = None,
    recheck: bool = False,
    channel: str = boe_v.NAME,
) -> dict[str, Any]:
    """Extrae los lotes de hasta `limit` anuncios pendientes del canal, el BOE si no se dice otro
    (ADR-0013; ventas directas del Patrimonio, ADR-0037); con `only`,
    solo esos (BOE-B-…). Antes, vuelve a ubicar los lotes que esperaban otro intento (ADR-0031);
    `unlocated` lista los que se quedan sin ubicar, con el motivo. Con `recheck`, vuelve a comprobar
    sin el LLM lo que el modelo propuso para los anuncios ya extraídos (ADR-0033)."""
    with connect(conninfo) as conn:
        locate = offer_locator(conn, geocoder or (lambda address: geocode(client, address)),
                               parcels or (lambda ref: find_parcel(client, ref)),
                               rustic or (lambda *args: find_rustic_parcel(client, *args)),
                               municipalities=municipalities or (
                                   lambda name: municipality_codes(client, name)),
                               foral=foral or (
                                   lambda province, key: find_foral_parcel(client, province, key)))
        return extract_pending(conn, llm, channel, locate, limit, only, recheck).as_dict()


def extract_pasted(conninfo: str, llm: LLMClient, offer_id: UUID) -> dict[str, Any]:
    """Extrae una oferta pegada por el usuario (F4.1)."""
    with connect(conninfo) as conn:
        return extract_link(conn, llm, offer_id)


def relocate_unlocated(conninfo: str, client: httpx.Client,
                       geocoder: Callable[[str], Geocoded] | None = None) -> dict[str, Any]:
    """Vuelve a ubicar todos los lotes públicos sin inmueble, con la dirección limpia y, si aun
    así no se puede, con el centro de su municipio como punto aproximado (ADR-0054)."""
    from housefinder.offers.boe_portal import offer_from_record

    located = approximate = still = 0
    with connect(conninfo) as conn:
        locate = offer_locator(
            conn, geocoder or (lambda address: geocode(client, address)),
            lambda ref: find_parcel(client, ref),
            rustic=lambda province, municipality, polygon, parcel: find_rustic_parcel(
                client, province, municipality, polygon, parcel),
            municipalities=lambda name: municipality_codes(client, name),
            foral=lambda province, key: find_foral_parcel(client, province, key))
        report = IngestReport()
        for item in unlocated_lots(conn):
            offer = relocated_offer(item.lot)
            if item.channel == subastas_portal.NAME:
                record = next((r for r in item.raw.get("lots") or []
                               if r.get("external_id") == item.lot.external_id), None)
                if record is None:
                    continue
                offer = offer_from_record(record)
            missed = locate_and_link(conn, item.lot.id, offer, locate, report)
            if missed is None:
                located += 1
            elif missed.approx is not None:
                approximate += 1
            else:
                still += 1
            conn.commit()
    return {"located": located, "approximate": approximate, "unlocated": still}
