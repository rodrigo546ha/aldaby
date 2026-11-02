"""Lectura diaria de los feeds de agencias (ADR-0038).

Cada feed es una foto completa: lo nuevo se guarda, lo que cambió se pone al día (y se vuelve a
ubicar si se movió), lo que vuelve se reactiva y lo que falta se retira. Si el feed no se puede
leer, no se retira nada. El informe nunca lleva la URL.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from housefinder.crypto.envelope import KeyProvider
from housefinder.db.agency_feeds import record_run
from housefinder.db.connection import Connection, connect
from housefinder.db.offers import (
    OfferRow,
    refresh_listing,
    retire_missing,
    stored_listing,
    upsert_offer,
)
from housefinder.db.sections import SourceRecord, upsert_source
from housefinder.feeds.registry import Feed, active_feeds
from housefinder.geo.cartociudad import Geocoded, geocode, municipality_codes
from housefinder.geo.catastro import Parcel, find_parcel
from housefinder.geo.foral import find_foral_parcel
from housefinder.offers.channels.agency_feed import NAME, AgencyFeed, FeedUnavailable
from housefinder.offers.ingest import IngestReport, Locator, locate_and_link
from housefinder.offers.locate import offer_locator


def license_text(feed: Feed) -> str:
    reach = ("solo los usuarios de su organización" if feed.scope == "organizacion"
             else "todos los usuarios de Aldaby")
    return (f"Cesión de {feed.agency_name}: consentimiento del {feed.consent_on.isoformat()} "
            f"({feed.consent_ref}); lo ven {reach}")


def run_feed(conn: Connection, client: httpx.Client, feed: Feed,
             locate: Locator) -> dict[str, Any]:
    channel = AgencyFeed(feed.id, feed.url)
    upsert_source(conn, SourceRecord(channel.source_id, f"Feed de {feed.agency_name}", "",
                                     license_text(feed), datetime.now(UTC)))
    try:
        items = list(channel.fetch(client))
    except FeedUnavailable as exc:
        report: dict[str, Any] = {"error": str(exc)}
        record_run(conn, feed.id, report)
        conn.commit()
        return report
    links = IngestReport()
    counts = {"new": 0, "changed": 0, "unchanged": 0, "without_location": 0}
    kept: list[str] = []
    for item in items:
        offer = channel.parse(item)[0]
        row = OfferRow(
            channel=NAME, external_id=offer.external_id, kind="anuncio", title=offer.title,
            url=offer.url or None, published_on=offer.published_on,
            description=offer.description, asking_price=offer.asking_price,
            auction_min_bid=None, deposit_required=None, address=None,
            cadastral_ref=offer.cadastral_ref, built_area_m2=offer.built_area_m2,
            extraction_status="no_aplica", source_id=channel.source_id, org_id=feed.offers_org,
            extracted=offer.extracted,
        )
        before = stored_listing(conn, NAME, offer.external_id)
        result = upsert_offer(conn, row, item.raw, item.sha256)
        if result.created:
            counts["new"] += 1
        else:
            moved = before is not None and before != (
                offer.cadastral_ref, item.raw.get("latitude"), item.raw.get("longitude"))
            refresh_listing(conn, result.offer_id, row, moved)
            counts["changed" if result.raw_changed else "unchanged"] += 1
        if not offer.locatable:
            counts["without_location"] += 1
        locate_and_link(conn, result.offer_id, offer, locate, links)
        kept.append(offer.external_id)
    report = {"listings": len(items), **counts,
              "retired": retire_missing(conn, NAME, channel.source_id, kept),
              "located": links.located, "properties_new": links.properties_new,
              "properties_matched": links.properties_matched,
              "skipped": dict(channel.skipped)}
    record_run(conn, feed.id, report)
    conn.commit()
    return report


def run_feeds(conninfo: str, client: httpx.Client, keys: KeyProvider,
              geocoder: Callable[[str], Geocoded] | None = None,
              parcels: Callable[[str], Parcel] | None = None) -> dict[str, Any]:
    """Lee todos los feeds activos. El informe va por feed, con la agencia y sin la URL."""
    reports: list[dict[str, Any]] = []
    with connect(conninfo) as conn:
        locate = offer_locator(conn, geocoder or (lambda address: geocode(client, address)),
                               parcels or (lambda ref: find_parcel(client, ref)),
                               municipalities=lambda name: municipality_codes(client, name),
                               foral=lambda province, key: find_foral_parcel(client, province, key))
        feeds, locked = active_feeds(conn, keys)
        for feed in feeds:
            reports.append({"feed": str(feed.id), "agency": feed.agency_name,
                            **run_feed(conn, client, feed, locate)})
        reports += [{"feed": str(feed_id), "error": "no se puede descifrar la URL: falta su clave"}
                    for feed_id in locked]
    return {"feeds": reports}
