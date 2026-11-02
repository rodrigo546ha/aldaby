"""Clientes del profesional y cliente activo (F7.2, ADR-0029).

El cliente activo va en una cookie (`hf_cliente`) que la API valida en cada petición contra la
organización de la sesión. Los nombres se descifran solo para su organización.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from housefinder.api.auth import secure_cookies
from housefinder.api.deps import CLIENT_COOKIE, DbDep, KeysDep, OrgDep, active_client
from housefinder.profiles import clients

router = APIRouter(prefix="/clients", tags=["clientes"])
COOKIE_DAYS = 365


class ClientOut(BaseModel):
    id: UUID
    name: str
    has_profile: bool
    active: bool


class ClientIn(BaseModel):
    name: str = Field(max_length=200)
    informed: bool = False  # «he informado a mi cliente del tratamiento» (ADR-0039)


class ActiveIn(BaseModel):
    client_id: UUID


@router.get("", response_model=list[ClientOut])
def list_clients(request: Request, db: DbDep, keys: KeysDep, org: OrgDep) -> list[ClientOut]:
    active = active_client(request, db, org)
    return [ClientOut(id=c.id, name=c.name, has_profile=c.has_profile, active=c.id == active)
            for c in clients.list_all(db, keys, org)]


@router.post("", response_model=ClientOut, status_code=201)
def create_client(body: ClientIn, db: DbDep, keys: KeysDep, org: OrgDep,
                  response: Response) -> ClientOut:
    """Da de alta un cliente y lo deja activo. Exige que el profesional haya informado al cliente
    del tratamiento de sus datos (ADR-0039)."""
    if not body.informed:
        raise HTTPException(status_code=422,
                            detail="Marca que has informado a tu cliente del tratamiento de sus "
                                   "datos")
    try:
        client_id = clients.create(db, keys, org, body.name, informed=True)
    except clients.ClientError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    _set_active(response, client_id)
    return ClientOut(id=client_id, name=" ".join(body.name.split()), has_profile=False,
                     active=True)


@router.put("/active", status_code=204)
def choose_client(body: ActiveIn, db: DbDep, org: OrgDep, response: Response) -> None:
    if not clients.belongs(db, body.client_id, org):
        raise HTTPException(status_code=404, detail="No existe ese cliente")
    _set_active(response, body.client_id)


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: UUID, request: Request, db: DbDep, org: OrgDep,
                  response: Response) -> None:
    """Borrado definitivo del cliente, sus perfiles y su entrevista (derecho de supresión)."""
    try:
        clients.delete(db, client_id, org)
    except clients.ClientError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    if request.cookies.get(CLIENT_COOKIE) == str(client_id):
        response.delete_cookie(CLIENT_COOKIE, path="/")


def _set_active(response: Response, client_id: UUID) -> None:
    response.set_cookie(CLIENT_COOKIE, str(client_id), max_age=COOKIE_DAYS * 86400,
                        httponly=True, secure=secure_cookies(), samesite="lax", path="/")
