"""Tipos de trabajo registrados (ADR-0010). Cada uno recibe el `payload` y es idempotente."""

from __future__ import annotations

from typing import Any

from housefinder.ingestion import ine_adrh, ine_sections
from housefinder.jobs.worker import Handler


def build_handlers(conninfo: str) -> dict[str, Handler]:
    def sections(payload: dict[str, Any]) -> dict[str, Any]:
        return ine_sections.load(int(payload["year"]), str(payload["province"]), conninfo)

    def adrh(payload: dict[str, Any]) -> dict[str, Any]:
        return ine_adrh.load(str(payload["province"]), int(payload.get("last_years", 10)),
                             conninfo)

    return {"ine_sections": sections, "ine_adrh": adrh}
