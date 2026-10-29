"""Territorio de una dirección o un punto (F3.6): geocodificación con caché, sección censal
de la última cartografía cargada e indicadores con su fuente.

El geocodificador llega como función para no llamar a la red en los tests (ADR-0009).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from housefinder.core.figures import Figure, SourceRef
from housefinder.db.connection import Connection
from housefinder.db.geocache import CachedGeocode, get_cached, put_cached
from housefinder.db.indicators import indicator_history, indicator_sources
from housefinder.db.sections import (
    SourceRecord,
    latest_vintage,
    section_at,
    section_source,
    stable_vintages,
    upsert_source,
)
from housefinder.geo.cartociudad import (
    ATTRIBUTION,
    FIND_URL,
    LICENSE_URL,
    SOURCE_ID,
    SOURCE_NAME,
    Geocoded,
    normalize,
)
from housefinder.ingestion.ine_sections import LICENSE as INE_LICENSE
from housefinder.territory.figures import STABILITY_TOLERANCE, Context, territory_figures

CACHE_MAX_AGE = timedelta(days=365)
INE_CITATION = "Elaboración propia con datos extraídos del sitio web del INE: www.ine.es"


class SectionNotFound(LookupError):
    """El punto no cae en ninguna sección cargada."""


@dataclass(frozen=True)
class Location:
    lon: float
    lat: float
    query: str | None = None  # dirección pedida
    matched: str | None = None  # dirección encontrada por el geocodificador
    match_type: str | None = None
    cadastral_ref: str | None = None
    from_cache: bool = False


@dataclass(frozen=True)
class TerritoryReport:
    location: Location
    section_code: str
    municipality: str
    vintage: int
    figures: list[Figure]
    series: dict[str, list[Figure]]
    notes: list[str] = field(default_factory=list)
    attribution: list[str] = field(default_factory=list)


def locate_address(
    conn: Connection, address: str, geocoder: Callable[[str], Geocoded]
) -> Location:
    """Coordenadas de una dirección, de la caché si hay una consulta de menos de un año."""
    query = normalize(address)
    cached = get_cached(conn, query, CACHE_MAX_AGE)
    if cached is None:
        found = geocoder(address)
        cached = CachedGeocode(found.lon, found.lat, found.match_type, found.matched,
                               found.municipality, found.cadastral_ref)
        upsert_source(conn, SourceRecord(SOURCE_ID, SOURCE_NAME, FIND_URL, ATTRIBUTION,
                                         datetime.now(UTC), f"Condiciones: {LICENSE_URL}"))
        put_cached(conn, query, cached, SOURCE_ID)
        conn.commit()
        from_cache = False
    else:
        from_cache = True
    return Location(cached.lon, cached.lat, address, cached.matched, cached.match_type,
                    cached.cadastral_ref, from_cache)


def territory_at(conn: Connection, location: Location) -> TerritoryReport:
    vintage = latest_vintage(conn)
    if vintage is None:
        raise SectionNotFound("No hay cartografía de secciones cargada")
    hit = section_at(conn, location.lon, location.lat, vintage)
    if hit is None:
        raise SectionNotFound(
            f"El punto no cae en ninguna sección cargada (cartografía {vintage})"
        )
    stable = stable_vintages(conn, hit.code, vintage, STABILITY_TOLERANCE)
    history = indicator_history(conn, hit.code, stable)
    map_sources = {
        v: SourceRef("dataset", s)
        for v in stable
        if (s := section_source(conn, hit.code, v)) is not None
    }
    geocoded = location.match_type is not None
    ctx = Context(
        code=hit.code,
        vintage=vintage,
        location_sources=(SourceRef("dataset", SOURCE_ID),) if geocoded else (),
        map_sources=map_sources,
        value_sources=indicator_sources(conn, hit.code, stable),
    )
    figures, series, notes = territory_figures(history, stable, ctx)
    if location.match_type is not None and location.match_type != "portal":
        notes.insert(0, "La dirección se localizó sin número: el punto está en el eje de la "
                        "calle y la sección puede ser la de enfrente.")
    if not figures:
        notes.append("La sección no tiene indicadores cargados.")
    attribution = [f"{INE_CITATION} ({INE_LICENSE.split('.')[0]})"]
    if geocoded:
        attribution.append(f"Geocodificación: {ATTRIBUTION}")
    return TerritoryReport(location, hit.code, hit.municipality, vintage, figures, series,
                           notes, attribution)
