"""Dependencias compartidas de la API: libros de reglas y de parámetros, cargados una vez."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException

from housefinder.agent.llm import LLMClient, llm_from_env
from housefinder.crypto.envelope import KeyProvider, provider_from_env
from housefinder.db.connection import Connection, DatabaseUnavailable, connect
from housefinder.db.profiles import get_or_create_organization
from housefinder.geo.cartociudad import Geocoded, geocode
from housefinder.geo.catastro import Parcel, find_parcel
from housefinder.offers.link import Resolver, link_client, system_resolve
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.regulation.rules import RuleBook, default_rules_dir
from housefinder.valuation.scenarios import AppreciationReport, appreciation_scenarios


@lru_cache
def get_param_book() -> ParamBook:
    return ParamBook.from_dir(default_params_dir())


@lru_cache
def get_rule_book() -> RuleBook:
    return RuleBook.from_dir(default_rules_dir())


ParamBookDep = Annotated[ParamBook, Depends(get_param_book)]
RuleBookDep = Annotated[RuleBook, Depends(get_rule_book)]


def get_db() -> Iterator[Connection]:
    try:
        with connect() as conn:
            yield conn
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_geocoder() -> Iterator[Callable[[str], Geocoded]]:
    with httpx.Client(headers={"User-Agent": "HouseFinder/0.1 (datos abiertos)"}) as client:
        yield lambda address: geocode(client, address)


DbDep = Annotated[Connection, Depends(get_db)]
GeocoderDep = Annotated[Callable[[str], Geocoded], Depends(get_geocoder)]

DEV_ORG = "Desarrollo local"


def get_org(db: DbDep) -> UUID:
    """Organización de quien llama. Hasta la autenticación (G8), una local de desarrollo."""
    org_id = get_or_create_organization(db, DEV_ORG, "particular")
    db.commit()
    return org_id


def get_parcel_finder() -> Iterator[Callable[[str], Parcel]]:
    with httpx.Client(headers={"User-Agent": "HouseFinder/0.1 (datos abiertos)"}) as client:
        yield lambda ref: find_parcel(client, ref)


def get_scenario_finder(book: ParamBookDep) -> Callable[[str, int, bool], AppreciationReport]:
    """Escenarios de revalorización de un municipio; abre la base solo si se piden."""

    def find(municipality: str, horizon_years: int, new_build: bool) -> AppreciationReport:
        with connect() as conn:
            return appreciation_scenarios(conn, book, municipality, horizon_years, new_build)

    return find


def get_link_client() -> Iterator[httpx.Client]:
    with link_client() as client:
        yield client


def get_resolver() -> Resolver:
    return system_resolve


def get_keys() -> KeyProvider:
    """Clave maestra para los datos personales (ADR-0011). Sin ella, 503 con cómo crearla."""
    try:
        return provider_from_env()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_llm() -> LLMClient:
    try:
        return llm_from_env()
    except ValueError as exc:
        raise HTTPException(status_code=503,
                            detail=f"El modelo no está configurado: {exc}") from exc


OrgDep = Annotated[UUID, Depends(get_org)]
KeysDep = Annotated[KeyProvider, Depends(get_keys)]
LLMDep = Annotated[LLMClient, Depends(get_llm)]
ScenarioFinderDep = Annotated[
    Callable[[str, int, bool], AppreciationReport], Depends(get_scenario_finder)]
ParcelFinderDep = Annotated[Callable[[str], Parcel], Depends(get_parcel_finder)]
LinkClientDep = Annotated[httpx.Client, Depends(get_link_client)]
ResolverDep = Annotated[Resolver, Depends(get_resolver)]
