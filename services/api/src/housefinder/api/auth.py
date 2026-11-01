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
from housefinder.api.deps import SESSION_COOKIE, DbDep, SessionDep

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


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, db: DbDep, response: Response) -> MeOut:
    try:
        token, opened = log_in(db, body.email, body.password)
    except AccountError as exc:
        db.commit()  # el fallo cuenta para el bloqueo
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True,
                        secure=_secure(), samesite="lax", path="/")
    return MeOut(email=opened.email, role=opened.role)


@router.post("/logout", status_code=204)
def logout(request: Request, db: DbDep, response: Response) -> None:
    log_out(db, request.cookies.get(SESSION_COOKIE))
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=MeOut)
def me(current: SessionDep) -> MeOut:
    if current is not None:
        return MeOut(email=current.email, role=current.role)
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


def _secure() -> bool:
    """`Secure` siempre, salvo apagado a propósito en local (`HOUSEFINDER_COOKIE_SECURE=0`)."""
    return os.environ.get("HOUSEFINDER_COOKIE_SECURE") != "0"
