"""API HTTP de HouseFinder (fase 1: simuladores; el resto llega por fases)."""

from __future__ import annotations

from fastapi import FastAPI

from housefinder.api import (
    auth,
    boe,
    branding,
    clients,
    offers,
    plans,
    profiles,
    search,
    simulate,
    territory,
    valuation,
)

app = FastAPI(title="HouseFinder API", version="0.1.0")
app.include_router(simulate.router)
app.include_router(territory.router)
app.include_router(offers.router)
app.include_router(boe.router)
app.include_router(valuation.router)
app.include_router(profiles.router)
app.include_router(search.router)
app.include_router(plans.router)
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(branding.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
