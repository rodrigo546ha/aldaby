"""Acceso de los profesionales (F7.1, ADR-0028): entrar, salir, quién soy y elegir contraseña.

La cookie de sesión es `HttpOnly`, `Secure` y `SameSite=Lax`, y la web llama a la API por el
mismo origen (`/api`). Los errores no dicen si una cuenta existe.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from housefinder.accounts.service import (
    SESSION_DAYS,
    AccountError,
    log_in,
    log_out,
    set_password,
)
from housefinder.api.deps import (
    CLIENT_COOKIE,
    SESSION_COOKIE,
    DbDep,
    SessionDep,
    free_plans_left,
    is_particular,
    pending_legal,
)

router = APIRouter(prefix="/auth", tags=["acceso"])


class LoginIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


class PasswordIn(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=1024)


class MeOut(BaseModel):
    email: str
    role: str
    pending_legal: list[str] = []  # textos legales que faltan por aceptar (ADR-0039)
    free_plans_left: int | None = None  # particular: planes completos que le quedan (ADR-0040)


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, db: DbDep, response: Response) -> MeOut:
    try:
        token, opened = log_in(db, body.email, body.password)
    except AccountError as exc:
        db.commit()  # el fallo cuenta para el bloqueo
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True,
                        secure=secure_cookies(), samesite="lax", path="/")
    return MeOut(email=opened.email, role=opened.role,
                 pending_legal=pending_legal(db, opened.account_id, opened.role),
                 free_plans_left=free_plans_left(db, opened.org_id, is_particular(opened)))


@router.post("/logout", status_code=204)
def logout(request: Request, db: DbDep, response: Response) -> None:
    log_out(db, request.cookies.get(SESSION_COOKIE))
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CLIENT_COOKIE, path="/")  # el cliente activo era de esta cuenta


@router.get("/me", response_model=MeOut)
def me(current: SessionDep, db: DbDep) -> MeOut:
    if current is not None:
        return MeOut(email=current.email, role=current.role,
                     pending_legal=pending_legal(db, current.account_id, current.role),
                     free_plans_left=free_plans_left(db, current.org_id, is_particular(current)))
    if os.environ.get("HOUSEFINDER_DEV_ORG") == "1":  # en el Mac, sin cuenta (ADR-0028)
        return MeOut(email="desarrollo local", role="admin")
    raise HTTPException(status_code=401, detail="Inicia sesión para seguir")


@router.post("/password", status_code=204)
def choose_password(body: PasswordIn, db: DbDep) -> None:
    """Elegir o restablecer la contraseña con el enlace de un solo uso del administrador."""
    try:
        set_password(db, body.token, body.password)
    except AccountError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()


def secure_cookies() -> bool:
    """`Secure` siempre, salvo apagado a propósito en local (`HOUSEFINDER_COOKIE_SECURE=0`)."""
    return os.environ.get("HOUSEFINDER_COOKIE_SECURE") != "0"
