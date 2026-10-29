"""API HTTP de HouseFinder (fase 1: simuladores; el resto llega por fases)."""

from __future__ import annotations

from fastapi import FastAPI

from housefinder.api import simulate, territory

app = FastAPI(title="HouseFinder API", version="0.1.0")
app.include_router(simulate.router)
app.include_router(territory.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
