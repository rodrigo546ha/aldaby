"""Enlace o texto pegado por el usuario: oferta privada, extracción y confirmación (F4.1).

1. `submit_link` descarga la página al momento (`offers/link.py`) y `submit_text` toma el texto
   copiado. Las dos guardan una oferta privada de la organización, `pendiente`, y encolan
   `extract_link`.
2. `extract_link` (trabajo) pasa el texto por el LLM con evidencia comprobada y lo deja `extraida`.
3. `confirm` guarda lo que el usuario acepta o corrige, con el origen de cada valor, y ubica la
   oferta. Solo lo confirmado entra en un cálculo (ADR-0013, ADR-0015).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

from housefinder.agent.extraction import CADASTRAL_REF, LISTING_KINDS, extract_listing
from housefinder.agent.llm import LLMClient
from housefinder.db.connection import Connection
from housefinder.db.jobs import enqueue
from housefinder.db.offers import (
    OfferRow,
    confirm_offer,
    get_private_offer,
    mark_extracted,
    offer_to_extract,
    unlink_offer,
    upsert_offer,
)
from housefinder.offers.ingest import IngestReport, Locator, locate_and_link
from housefinder.offers.link import Resolver, fetch_listing, system_resolve
from housefinder.offers.model import NormalizedOffer, RawItem

CHANNEL = "url_usuario"
JOB_KIND = "extract_link"
MAX_TEXT_CHARS = 60_000  # el texto que se envía al LLM
OPERATIONS = ("venta", "alquiler", "desconocida")


class ConfirmationError(ValueError):
    """Un valor de la confirmación no es válido; el mensaje es para el usuario."""


@dataclass(frozen=True)
class Submitted:
    offer_id: UUID
    created: bool


def submit_link(
    conn: Connection,
    org_id: UUID,
    url: str,
    client: httpx.Client,
    resolve: Resolver = system_resolve,
) -> Submitted:
    page = fetch_listing(client, url, resolve)
    raw = {"source": "enlace", **page.raw()}
    return _store(conn, org_id, page.final_url, page.title, raw, key=page.final_url)


def submit_text(conn: Connection, org_id: UUID, text: str, url: str | None = None) -> Submitted:
    text = text.strip()
    raw = {"source": "texto", "url": url, "text": text,
           "fetched_at": datetime.now(UTC).isoformat()}
    return _store(conn, org_id, url, None, raw, key=f"texto:{text}")


def _store(
    conn: Connection, org_id: UUID, url: str | None, title: str | None, raw: dict[str, Any],
    key: str,
) -> Submitted:
    external_id = hashlib.sha256(f"{org_id}|{key}".encode()).hexdigest()
    row = OfferRow(
        channel=CHANNEL, external_id=external_id, kind="enlace", title=title, url=url,
        published_on=None, description=None, asking_price=None, auction_min_bid=None,
        deposit_required=None, address=None, cadastral_ref=None, built_area_m2=None,
        extraction_status="pendiente", source_id=None, org_id=org_id,
    )
    result = upsert_offer(conn, row, raw, RawItem("", "", None, raw).sha256)
    enqueue(conn, JOB_KIND, {"offer_id": str(result.offer_id)},
            dedupe_key=f"{JOB_KIND}:{result.offer_id}")
    conn.commit()
    return Submitted(result.offer_id, result.created)


def listing_text(raw: Mapping[str, Any]) -> str:
    """Lo que lee el LLM y contra lo que se comprueban las citas."""
    parts = [raw.get("title") or "", raw.get("text") or ""]
    return "\n".join(p for p in parts if p).strip()[:MAX_TEXT_CHARS]


def extract_link(conn: Connection, llm: LLMClient, offer_id: UUID) -> dict[str, Any]:
    """Extrae la oferta si sigue pendiente. Si el LLM falla, el trabajo se reintenta."""
    found = offer_to_extract(conn, offer_id)
    if found is None or found[0] != "pendiente":
        return {"extracted": False}
    checked = extract_listing(llm, listing_text(found[1]))
    mark_extracted(conn, offer_id, {"listing": checked.as_dict()})
    conn.commit()
    return {"extracted": True, "rejected_fields": checked.rejected}


def confirm(
    conn: Connection,
    org_id: UUID,
    offer_id: UUID,
    values: Mapping[str, str | None],
    operation: str | None,
    locate: Locator,
) -> bool:
    """Guarda lo que el usuario confirma y ubica la oferta. False si no es suya o no existe."""
    offer = get_private_offer(conn, offer_id, org_id)
    if offer is None:
        return False
    unknown = set(values) - set(LISTING_KINDS)
    if unknown:
        raise ConfirmationError(f"Campos desconocidos: {', '.join(sorted(unknown))}")
    if operation is not None and operation not in OPERATIONS:
        raise ConfirmationError("La operación tiene que ser venta, alquiler o desconocida")
    proposed = ((offer.extracted or {}).get("listing") or {}).get("fields", {})
    confirmed: dict[str, dict[str, str]] = {}
    parsed: dict[str, Decimal | str] = {}
    for name, kind in LISTING_KINDS.items():
        value = _clean(name, kind, values.get(name))
        if value is None:
            continue
        parsed[name] = value
        suggestion = proposed.get(name, {})
        was = suggestion.get("value") if suggestion.get("status") == "verificado" else None
        origin = "usuario" if was is None else ("extraido" if _same(was, value) else "corregido")
        confirmed[name] = {"value": str(value), "origin": origin}
    extracted = {**(offer.extracted or {}), "confirmed": {
        "operation": operation, "fields": confirmed,
        "confirmed_at": datetime.now(UTC).isoformat()}}
    address = _text(parsed.get("address"))
    municipality = _text(parsed.get("municipality"))
    full_address = ", ".join(p for p in (address, municipality) if p) if address else None
    cadastral_ref = _text(parsed.get("cadastral_ref"))
    built_area = _number(parsed.get("built_area_m2"))
    stored = confirm_offer(
        conn, offer_id, org_id,
        asking_price=_number(parsed.get("price")) if operation == "venta" else None,
        built_area_m2=built_area, address=full_address, cadastral_ref=cadastral_ref,
        extracted=extracted,
    )
    if not stored:
        return False
    if offer.property_id is not None and (offer.address, offer.cadastral_ref) != (
            full_address, cadastral_ref):
        unlink_offer(conn, offer_id)  # la dirección cambió: se vuelve a ubicar
    located = NormalizedOffer(external_id="", kind="enlace", url=offer.url or "",
                              address=full_address, municipality=municipality,
                              cadastral_ref=cadastral_ref,
                              built_area_m2=built_area)
    locate_and_link(conn, offer_id, located, locate, IngestReport())
    conn.commit()
    return True


def _clean(name: str, kind: str, raw_value: str | None) -> Decimal | str | None:
    if raw_value is None or not raw_value.strip():
        return None
    value = " ".join(raw_value.split())
    if kind == "number":
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ConfirmationError(f"{name}: tiene que ser un número (1234.5)") from exc
        if not number.is_finite() or number < 0:
            raise ConfirmationError(f"{name}: tiene que ser un número positivo")
        return number
    if kind == "cadastral":
        ref = value.replace(" ", "").upper()
        if not CADASTRAL_REF.match(ref):
            raise ConfirmationError(f"{name}: la referencia catastral tiene 14 o 20 caracteres")
        return ref
    return value


def _same(was: str, value: Decimal | str) -> bool:
    if isinstance(value, Decimal):
        try:
            return Decimal(was) == value
        except InvalidOperation:
            return False
    return was == value


def _text(value: Decimal | str | None) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: Decimal | str | None) -> Decimal | None:
    return value if isinstance(value, Decimal) else None
