"""Tipos de trabajo registrados (ADR-0010). Cada uno recibe el `payload` y es idempotente."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import httpx

from housefinder.feeds.run import run_feeds
from housefinder.ingestion import ine_adrh, ine_ipc_alquiler, ine_ipv, ine_sections
from housefinder.jobs.worker import Handler
from housefinder.offers.channels import boe_v
from housefinder.offers.run import (
    extract_boe_v,
    extract_pasted,
    run_boe_auctions,
    run_boe_v,
    run_patrimonio,
)
from housefinder.watch.run import watch_bocm, watch_boe


def build_handlers(conninfo: str) -> dict[str, Handler]:
    def sections(payload: dict[str, Any]) -> dict[str, Any]:
        return ine_sections.load(int(payload["year"]), str(payload["province"]), conninfo)

    def adrh(payload: dict[str, Any]) -> dict[str, Any]:
        return ine_adrh.load(str(payload["province"]), int(payload.get("last_years", 10)),
                             conninfo)

    def boe(payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(headers={"User-Agent": ine_sections.USER_AGENT}) as client:
            return watch_boe(conninfo, client, date.today(), int(payload.get("days", 7)))

    def bocm(payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(headers={"User-Agent": ine_sections.USER_AGENT}) as client:
            return watch_bocm(conninfo, client)

    def offers_boe_v(payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(headers={"User-Agent": ine_sections.USER_AGENT}) as client:
            return run_boe_v(conninfo, client, date.today(), int(payload.get("days", 7)))

    def extract_offers(payload: dict[str, Any]) -> dict[str, Any]:
        from housefinder.agent.llm import llm_from_env

        with httpx.Client(headers={"User-Agent": ine_sections.USER_AGENT}) as client:
            return extract_boe_v(conninfo, client, llm_from_env(), int(payload.get("limit", 20)),
                                 only=payload.get("ids"), recheck=bool(payload.get("recheck")),
                                 channel=str(payload.get("channel", boe_v.NAME)))

    def regions(payload: dict[str, Any]) -> list[str]:
        """Una comunidad o, con `todas`, las 19 (ADR-0043): cada carga solo sustituye la suya."""
        region = str(payload.get("region", "todas"))
        return [f"{n:02d}" for n in range(1, 20)] if region == "todas" else [region]

    def price_index(payload: dict[str, Any]) -> dict[str, Any]:
        return {r: ine_ipv.load(r, conninfo) for r in regions(payload)}

    def rent_index(payload: dict[str, Any]) -> dict[str, Any]:
        return {r: ine_ipc_alquiler.load(r, conninfo) for r in regions(payload)}

    def offers_boe_auctions(payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(headers={"User-Agent": ine_sections.USER_AGENT}) as client:
            return run_boe_auctions(conninfo, client, date.today(), int(payload.get("days", 7)))

    def offers_patrimonio(payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(headers={"User-Agent": ine_sections.USER_AGENT}) as client:
            return run_patrimonio(conninfo, client)

    def offers_agency_feeds(payload: dict[str, Any]) -> dict[str, Any]:
        from housefinder.crypto.envelope import provider_from_env

        with httpx.Client(headers={"User-Agent": ine_sections.USER_AGENT}) as client:
            return run_feeds(conninfo, client, provider_from_env)

    def extract_link(payload: dict[str, Any]) -> dict[str, Any]:
        from housefinder.agent.llm import llm_from_env

        return extract_pasted(conninfo, llm_from_env(), UUID(str(payload["offer_id"])))

    return {"ine_sections": sections, "ine_adrh": adrh, "watch_boe": boe, "watch_bocm": bocm,
            "offers_boe_v": offers_boe_v, "extract_offers": extract_offers,
            "extract_link": extract_link, "offers_boe_auctions": offers_boe_auctions,
            "offers_patrimonio": offers_patrimonio, "offers_agency_feeds": offers_agency_feeds,
            "ine_ipv": price_index,
            "ine_ipc_alquiler": rent_index}
