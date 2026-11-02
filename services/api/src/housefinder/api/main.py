"""API HTTP de HouseFinder (fase 1: simuladores; el resto llega por fases)."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from housefinder.api import (
    auth,
    boe,
    branding,
    clients,
    feeds,
    legal,
    offers,
    patrimonio,
    plans,
    profiles,
    search,
    simulate,
    territory,
    valuation,
)
from housefinder.db.connection import DatabaseUnavailable, connect

app = FastAPI(title="HouseFinder API", version="0.1.0")
app.include_router(simulate.router)
app.include_router(territory.router)
app.include_router(offers.router)
app.include_router(boe.router)
app.include_router(patrimonio.router)
app.include_router(feeds.router)
app.include_router(legal.router)
app.include_router(valuation.router)
app.include_router(profiles.router)
app.include_router(search.router)
app.include_router(plans.router)
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(branding.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Para la vigilancia del servidor (ADR-0040): la API y la base responden. Sin datos."""
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
    except DatabaseUnavailable as exc:
        raise HTTPException(503, "La base de datos no responde") from exc
    return {"status": "ok", "commit": os.environ.get("HOUSEFINDER_COMMIT", "local")}
