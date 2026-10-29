"""Canales de oferta como trabajos (ADR-0010)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from housefinder.agent.llm import LLMClient
from housefinder.db.connection import connect
from housefinder.db.review_tasks import mark_issue_read, read_issues
from housefinder.db.sections import SourceRecord, upsert_source
from housefinder.geo.cartociudad import Geocoded, geocode
from housefinder.offers.channels import boe_v
from housefinder.offers.extract import extract_pending
from housefinder.offers.ingest import IngestReport, ingest
from housefinder.offers.locate import address_locator

ISSUES = "offers_boe_v"  # días del BOE ya leídos por este canal


def run_boe_v(
    conninfo: str,
    client: httpx.Client,
    today: date,
    days: int = 7,
    geocoder: Callable[[str], Geocoded] | None = None,
) -> dict[str, Any]:
    """Lee los días del BOE de los últimos `days` que este canal no ha leído aún."""
    total = IngestReport()
    with connect(conninfo) as conn:
        upsert_source(conn, SourceRecord(boe_v.SOURCE_ID, boe_v.SOURCE_NAME, boe_v.LICENSE_URL,
                                         boe_v.LICENSE, datetime.now(UTC)))
        conn.commit()
        done = read_issues(conn, ISSUES)
        locate = address_locator(conn, geocoder or (lambda address: geocode(client, address)))
        for offset in range(days):
            day = today - timedelta(days=offset)
            if day.isoformat() in done:
                continue
            channel = boe_v.BoeSectionV([day])
            report = ingest(conn, channel, channel.fetch(client), locate)
            if day in channel.days_found or day < today:
                mark_issue_read(conn, ISSUES, day.isoformat(), report.items, report.offers_new)
                conn.commit()
            for key, value in report.as_dict().items():
                setattr(total, key, getattr(total, key) + value)
    return total.as_dict()


def extract_boe_v(
    conninfo: str,
    client: httpx.Client,
    llm: LLMClient,
    limit: int = 20,
    geocoder: Callable[[str], Geocoded] | None = None,
) -> dict[str, Any]:
    """Extrae los lotes de hasta `limit` anuncios pendientes del BOE (ADR-0013)."""
    with connect(conninfo) as conn:
        locate = address_locator(conn, geocoder or (lambda address: geocode(client, address)))
        return extract_pending(conn, llm, boe_v.NAME, locate, limit).as_dict()
