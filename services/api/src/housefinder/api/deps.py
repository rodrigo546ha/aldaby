"""Dependencias compartidas de la API: libros de reglas y de parámetros, cargados una vez."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request

from housefinder.accounts.service import Session, session
from housefinder.agent.llm import LLMClient, llm_from_env
from housefinder.crypto.envelope import KeyProvider, provider_from_env
from housefinder.db.clients import client_ids, client_in_org
from housefinder.db.connection import Connection, DatabaseUnavailable, connect
from housefinder.db.profiles import get_or_create_organization
from housefinder.geo.cartociudad import Geocoded, geocode, municipality_codes
from housefinder.geo.catastro import Parcel, find_parcel
from housefinder.geo.foral import find_foral_parcel
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


API_ROLE = "housefinder_api"  # sin privilegios de propietario: le aplica Row-Level Security


def get_db() -> Iterator[Connection]:
    try:
        with connect() as conn:
            conn.execute(f"SET ROLE {API_ROLE}")  # ADR-0028: las políticas por organización
            yield conn
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_geocoder() -> Iterator[Callable[[str], Geocoded]]:
    with httpx.Client(headers={"User-Agent": "HouseFinder/0.1 (datos abiertos)"}) as client:
        yield lambda address: geocode(client, address)


DbDep = Annotated[Connection, Depends(get_db)]
GeocoderDep = Annotated[Callable[[str], Geocoded], Depends(get_geocoder)]

DEV_ORG = "Desarrollo local"
SESSION_COOKIE = "hf_sesion"


def get_session(request: Request, db: DbDep) -> Session | None:
    """La sesión de la cookie, si sigue vigente (ADR-0028)."""
    current = session(db, request.cookies.get(SESSION_COOKIE))
    db.commit()  # la sesión se alarga
    return current


SessionDep = Annotated[Session | None, Depends(get_session)]


def get_org(db: DbDep, current: SessionDep) -> UUID:
    """Organización de quien llama: la de su sesión, nunca la que diga el cliente. Sin sesión,
    401, salvo en el Mac con `HOUSEFINDER_DEV_ORG=1` (la organización local de desarrollo)."""
    if current is not None:
        org_id = current.org_id
    elif os.environ.get("HOUSEFINDER_DEV_ORG") == "1":
        org_id = get_or_create_organization(db, DEV_ORG, "particular")
    else:
        raise HTTPException(status_code=401, detail="Inicia sesión para seguir")
    db.execute("SELECT set_config('app.org_id', %s, false)", (str(org_id),))
    db.commit()
    return org_id


def get_parcel_finder() -> Iterator[Callable[[str], Parcel]]:
    with httpx.Client(headers={"User-Agent": "HouseFinder/0.1 (datos abiertos)"}) as client:
        yield lambda ref: find_parcel(client, ref)


def get_foral_finder() -> Iterator[Callable[[str, str], Parcel]]:
    with httpx.Client(headers={"User-Agent": "HouseFinder/0.1 (datos abiertos)"}) as client:
        yield lambda province, key: find_foral_parcel(client, province, key)


def get_municipality_finder() -> Iterator[Callable[[str], frozenset[str]]]:
    with httpx.Client(headers={"User-Agent": "HouseFinder/0.1 (datos abiertos)"}) as client:
        yield lambda name: municipality_codes(client, name)


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
ForalFinderDep = Annotated[Callable[[str, str], Parcel], Depends(get_foral_finder)]
MunicipalityFinderDep = Annotated[Callable[[str], frozenset[str]],
                                  Depends(get_municipality_finder)]
LinkClientDep = Annotated[httpx.Client, Depends(get_link_client)]
ResolverDep = Annotated[Resolver, Depends(get_resolver)]


CLIENT_COOKIE = "hf_cliente"


def active_client(request: Request, db: Connection, org: UUID) -> UUID | None:
    """El cliente de la cookie si es de la organización; si no, el único que tenga (ADR-0029)."""
    raw = request.cookies.get(CLIENT_COOKIE)
    try:
        wanted = UUID(raw) if raw else None
    except ValueError:
        wanted = None
    if wanted is not None and client_in_org(db, wanted, org):
        return wanted
    ids = client_ids(db, org)
    return ids[0] if len(ids) == 1 else None


def get_client(request: Request, db: DbDep, org: OrgDep) -> UUID:
    """Cliente activo del profesional: perfil, búsqueda, plan y asesor trabajan con él."""
    client = active_client(request, db, org)
    if client is None:
        detail = ("Elige un cliente en la barra de arriba" if client_ids(db, org)
                  else "Crea primero un cliente en Clientes")
        raise HTTPException(status_code=409, detail=detail)
    return client


ClientDep = Annotated[UUID, Depends(get_client)]
