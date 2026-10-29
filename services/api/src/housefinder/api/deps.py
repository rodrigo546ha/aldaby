"""Dependencias compartidas de la API: libros de reglas y de parámetros, cargados una vez."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException

from housefinder.db.connection import Connection, DatabaseUnavailable, connect
from housefinder.db.profiles import get_or_create_organization
from housefinder.geo.cartociudad import Geocoded, geocode
from housefinder.offers.link import Resolver, link_client, system_resolve
from housefinder.params.book import ParamBook, default_params_dir
from housefinder.regulation.rules import RuleBook, default_rules_dir


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


def get_link_client() -> Iterator[httpx.Client]:
    with link_client() as client:
        yield client


def get_resolver() -> Resolver:
    return system_resolve


OrgDep = Annotated[UUID, Depends(get_org)]
LinkClientDep = Annotated[httpx.Client, Depends(get_link_client)]
ResolverDep = Annotated[Resolver, Depends(get_resolver)]
