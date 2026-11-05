"""API HTTP de HouseFinder (fase 1: simuladores; el resto llega por fases)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware

from housefinder.api import (
    analytics,
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
    sources,
    territory,
    valuation,
    waitlist,
)
from housefinder.db.connection import DatabaseUnavailable, close_pools, connect


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    close_pools()  # las conexiones del pool (ADR-0058)


app = FastAPI(title="HouseFinder API", version="0.1.0", lifespan=lifespan)
# Las respuestas de cifras son JSON muy repetitivo (fórmulas y fuentes): comprimidas pesan diez
# veces menos. Solo las de más de 1 KB, y solo si el navegador lo acepta.
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.include_router(simulate.router)
app.include_router(territory.router)
app.include_router(offers.router)
app.include_router(boe.router)
app.include_router(patrimonio.router)
app.include_router(feeds.router)
app.include_router(legal.router)
app.include_router(waitlist.router)
app.include_router(analytics.router)
app.include_router(valuation.router)
app.include_router(profiles.router)
app.include_router(search.router)
app.include_router(plans.router)
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(branding.router)
app.include_router(sources.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Para la vigilancia del servidor (ADR-0040): la API y la base responden. Sin datos."""
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
    except DatabaseUnavailable as exc:
        raise HTTPException(503, "La base de datos no responde") from exc
    return {"status": "ok", "commit": os.environ.get("HOUSEFINDER_COMMIT", "local")}
