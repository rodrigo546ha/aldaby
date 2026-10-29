"""Territorio de una dirección (F3.6): sección censal, renta, población y tendencias.

Cada valor es una `Figure` con su fuente (`SourceRef(kind="dataset")`). La API solo traduce:
el cálculo está en `housefinder.territory`.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from housefinder.api.deps import DbDep, GeocoderDep
from housefinder.api.figures import FigureOut, figure_out
from housefinder.geo.cartociudad import AddressNotFound, AddressTooVague
from housefinder.territory.service import (
    Location,
    SectionNotFound,
    locate_address,
    territory_at,
)

router = APIRouter(tags=["territorio"])


class LocationOut(BaseModel):
    lon: float
    lat: float
    query: str | None
    matched: str | None  # dirección encontrada: el usuario debe confirmarla
    match_type: str | None
    cadastral_ref: str | None


class SectionOut(BaseModel):
    code: str
    municipality: str
    vintage: int  # año de la cartografía (seccionado a 1 de enero)


class TerritoryResponse(BaseModel):
    location: LocationOut
    section: SectionOut
    figures: dict[str, FigureOut]
    series: dict[str, list[FigureOut]]
    notes: list[str]
    attribution: list[str]


@router.get("/territory")
def get_territory(
    db: DbDep,
    geocoder: GeocoderDep,
    address: str | None = Query(default=None, max_length=300),
    lon: float | None = Query(default=None, ge=-180, le=180),
    lat: float | None = Query(default=None, ge=-90, le=90),
) -> TerritoryResponse:
    if address is not None and (lon is not None or lat is not None):
        raise HTTPException(status_code=422, detail="Indica la dirección o lon y lat, no ambas")
    try:
        if address is not None:
            location = locate_address(db, address, geocoder)
        elif lon is not None and lat is not None:
            location = Location(lon, lat)
        else:
            raise HTTPException(status_code=422, detail="Indica la dirección o lon y lat")
        report = territory_at(db, location)
    except AddressTooVague as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (AddressNotFound, SectionNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="El geocodificador no responde") from exc

    loc = report.location
    return TerritoryResponse(
        location=LocationOut(lon=loc.lon, lat=loc.lat, query=loc.query, matched=loc.matched,
                             match_type=loc.match_type, cadastral_ref=loc.cadastral_ref),
        section=SectionOut(code=report.section_code, municipality=report.municipality,
                           vintage=report.vintage),
        figures={f.key: figure_out(f) for f in report.figures},
        series={k: [figure_out(f) for f in v] for k, v in report.series.items()},
        notes=report.notes,
        attribution=report.attribution,
    )
