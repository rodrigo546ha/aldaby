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
from housefinder.accounts.tiers import free_tier, plans_left
from housefinder.agent.llm import LLMClient, llm_from_env
from housefinder.crypto.envelope import KeyProvider, provider_from_env
from housefinder.db.clients import client_ids, client_in_org
from housefinder.db.connection import Connection, DatabaseUnavailable, connect, pooled
from housefinder.db.legal import accepted_versions
from housefinder.db.profiles import get_or_create_organization
from housefinder.db.tiers import record_plan_use, used_plans
from housefinder.geo.cartociudad import Geocoded, geocode, municipality_codes
from housefinder.geo.catastro import Parcel, find_parcel
from housefinder.geo.foral import find_foral_parcel
from housefinder.legal.documents import load as legal_documents
from housefinder.legal.documents import pending
from housefinder.offers.link import Resolver, link_client, system_resolve
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.profiles import clients
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
    """Una conexión del pool (ADR-0058). Al devolverla se borran el rol y `app.org_id`."""
    try:
        with pooled() as conn:
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
LEGAL_PENDING = (
    "Acepta las condiciones de uso, la política de privacidad y el contrato de "
    "encargo del tratamiento para seguir"
)
SESSION_COOKIE = "hf_sesion"


def get_session(request: Request, db: DbDep) -> Session | None:
    """La sesión de la cookie, si sigue vigente (ADR-0028)."""
    current = session(db, request.cookies.get(SESSION_COOKIE))
    db.commit()  # la sesión se alarga
    return current


SessionDep = Annotated[Session | None, Depends(get_session)]


def pending_legal(db: Connection, account_id: UUID, role: str) -> list[str]:
    """Textos legales cuya versión vigente la cuenta aún no ha aceptado (ADR-0039); dependen del
    rol: el particular no firma el encargo (ADR-0041)."""
    return pending(legal_documents(), accepted_versions(db, account_id), role)


def get_org(db: DbDep, current: SessionDep) -> UUID:
    """Organización de quien llama: la de su sesión, nunca la que diga el cliente. Sin sesión,
    401, salvo en el Mac con `HOUSEFINDER_DEV_ORG=1` (la organización local de desarrollo). Con
    textos legales sin aceptar, 403 (ADR-0039)."""
    if current is not None:
        if pending_legal(db, current.account_id, current.role):
            raise HTTPException(status_code=403, detail=LEGAL_PENDING)
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


def get_photo_client() -> Iterator[httpx.Client]:
    """Cliente para las imágenes públicas de un inmueble (ADR-0054)."""
    with httpx.Client(headers={"User-Agent": "HouseFinder/0.1 (datos abiertos)"}) as client:
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
        raise HTTPException(
            status_code=503, detail=f"El modelo no está configurado: {exc}"
        ) from exc


def get_optional_llm() -> LLMClient | None:
    try:
        return llm_from_env()
    except ValueError:
        return None


OrgDep = Annotated[UUID, Depends(get_org)]
KeysDep = Annotated[KeyProvider, Depends(get_keys)]
LLMDep = Annotated[LLMClient, Depends(get_llm)]
OptionalLlmDep = Annotated[LLMClient | None, Depends(get_optional_llm)]
ScenarioFinderDep = Annotated[
    Callable[[str, int, bool], AppreciationReport], Depends(get_scenario_finder)
]
ParcelFinderDep = Annotated[Callable[[str], Parcel], Depends(get_parcel_finder)]
ForalFinderDep = Annotated[Callable[[str, str], Parcel], Depends(get_foral_finder)]
MunicipalityFinderDep = Annotated[Callable[[str], frozenset[str]], Depends(get_municipality_finder)]
LinkClientDep = Annotated[httpx.Client, Depends(get_link_client)]
PhotoClientDep = Annotated[httpx.Client, Depends(get_photo_client)]
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


def is_particular(current: Session | None) -> bool:
    """Lo decide el rol de la cuenta, no el tipo de organización: la organización local de
    desarrollo es de tipo particular pero trabaja como un profesional, sin límites."""
    return current is not None and current.role == "particular"


def get_client(
    request: Request, db: DbDep, org: OrgDep, keys: KeysDep, current: SessionDep
) -> UUID:
    """Cliente activo del profesional: perfil, búsqueda, plan y asesor trabajan con él. Un
    particular tiene un solo perfil, el suyo: se crea la primera vez (ADR-0041)."""
    client = active_client(request, db, org)
    if client is None and is_particular(current) and not client_ids(db, org):
        client = clients.create(db, keys, org, OWN_PROFILE, informed=True)
        db.commit()
    if client is None:
        detail = (
            "Elige un cliente en la barra de arriba"
            if client_ids(db, org)
            else "Crea primero un cliente en Clientes"
        )
        raise HTTPException(status_code=409, detail=detail)
    return client


ClientDep = Annotated[UUID, Depends(get_client)]

OWN_PROFILE = "Mi perfil"
FREE_TIER_EXHAUSTED = (
    "Has usado los {n} planes completos del nivel gratuito. Puedes volver a "
    "abrir esos y seguir usando la búsqueda; el pase de compra llegará pronto."
)


def free_plans_left(db: Connection, org: UUID, particular: bool) -> int | None:
    """Planes completos que le quedan a un particular; None si no tiene límite (ADR-0041)."""
    if not particular:
        return None
    # /auth/me no pasa por get_org: sin esto, Row-Level Security esconde sus planes usados.
    db.execute("SELECT set_config('app.org_id', %s, false)", (str(org),))
    return plans_left(len(used_plans(db, org)), free_tier())


def check_full_plan(db: Connection, org: UUID, offer_id: UUID, particular: bool) -> bool:
    """Si la organización puede abrir el plan completo de esta oferta. 402 si es un particular sin
    planes libres y la oferta no es de las que ya abrió. Devuelve si hay que anotar el uso."""
    if not particular:
        return False
    used = used_plans(db, org)
    if offer_id in used:
        return False
    tier = free_tier()
    if plans_left(len(used), tier) == 0:
        raise HTTPException(status_code=402, detail=FREE_TIER_EXHAUSTED.format(n=tier.full_plans))
    return True


def plan_gate(db: Connection, org: UUID, particular: bool) -> Callable[[UUID], str | None] | None:
    """El cupo del nivel gratuito para las herramientas del asesor: el plan completo de una oferta
    contado por el asesor gasta cupo como abrir su página (ADR-0041). Devuelve, para cada oferta,
    None si se puede (y anota el uso) o el motivo si no. Sin límite (profesionales), None."""
    if not particular:
        return None

    def gate(offer_id: UUID) -> str | None:
        try:
            record = check_full_plan(db, org, offer_id, particular=True)
        except HTTPException as exc:
            return str(exc.detail)
        if record:
            record_plan_use(db, org, offer_id)
            db.commit()
        return None

    return gate
