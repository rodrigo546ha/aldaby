"""Tipos de trabajo registrados (ADR-0010). Cada uno recibe el `payload` y es idempotente."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from housefinder.ingestion import ine_adrh, ine_sections
from housefinder.jobs.worker import Handler
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

    return {"ine_sections": sections, "ine_adrh": adrh, "watch_boe": boe, "watch_bocm": bocm}
