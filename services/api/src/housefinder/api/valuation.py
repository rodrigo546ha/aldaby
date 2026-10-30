"""Renta y precio estimados de un inmueble (F5.3, F5.4, ADR-0018).

La API solo traduce: localiza la dirección si hace falta y devuelve las `Figure` del servicio de
`housefinder.valuation`, con su rango, sus fuentes, sus avisos y las citas de las fuentes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from housefinder.api.deps import DbDep, GeocoderDep, ParamBookDep
from housefinder.api.figures import FigureOut, figure_out
from housefinder.geo.cartociudad import AddressNotFound, AddressTooVague
from housefinder.territory.service import locate_address
from housefinder.valuation.service import OutsideCoverage, value_property

router = APIRouter(tags=["valoración"])


class ValuationResponse(BaseModel):
    lon: float
    lat: float
    matched_address: str | None  # dirección encontrada: el usuario debe confirmarla
    section_code: str  # seccionado de 2021, el del SERPAVI
    rent_level: Literal["seccion", "distrito", "municipio"]
    figures: dict[str, FigureOut]
    notes: list[str]
    attribution: list[str]


@router.get("/valuation")
def get_valuation(
    db: DbDep,
    book: ParamBookDep,
    geocoder: GeocoderDep,
    area_m2: Annotated[Decimal, Query(gt=0, le=2000, description="Superficie construida en m²")],
    typology: Literal["colectiva", "unifamiliar"] = "colectiva",
    new_build: bool = False,
    address: str | None = Query(default=None, max_length=300),
    lon: float | None = Query(default=None, ge=-180, le=180),
    lat: float | None = Query(default=None, ge=-90, le=90),
) -> ValuationResponse:
    if address is not None and (lon is not None or lat is not None):
        raise HTTPException(status_code=422, detail="Indica la dirección o lon y lat, no ambas")
    matched = None
    try:
        if address is not None:
            location = locate_address(db, address, geocoder)
            lon, lat, matched = location.lon, location.lat, location.matched
        elif lon is None or lat is None:
            raise HTTPException(status_code=422, detail="Indica la dirección o lon y lat")
        report = value_property(db, book, lon, lat, area_m2, typology, new_build)
    except AddressTooVague as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (AddressNotFound, OutsideCoverage) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="El geocodificador no responde") from exc
    return ValuationResponse(
        lon=lon, lat=lat, matched_address=matched, section_code=report.section_code,
        rent_level=report.level,  # type: ignore[arg-type]
        figures={f.key: figure_out(f) for f in report.figures},
        notes=report.notes, attribution=report.attribution,
    )
