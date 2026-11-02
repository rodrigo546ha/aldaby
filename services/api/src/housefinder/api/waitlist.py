"""Lista de espera de la página de presentación (F8.1, ADR-0040). Pública y sin sesión.

La respuesta es la misma esté el correo ya apuntado o no: no dice quién se ha apuntado.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from housefinder.accounts.service import AccountError, normalize_email
from housefinder.accounts.tiers import free_tier
from housefinder.db.waitlist import join_waitlist
from housefinder.legal.documents import load

from .deps import DbDep

router = APIRouter(prefix="/waitlist", tags=["lista de espera"])


class WaitlistIn(BaseModel):
    email: str = Field(max_length=320)
    kind: Literal["particular", "profesional"]
    consent: bool  # «acepto la política de privacidad y que me escribáis para darme acceso»


class WaitlistOut(BaseModel):
    message: str


class FreeTierOut(BaseModel):
    full_plans: int  # planes completos del nivel gratuito (data/niveles.yaml)


@router.post("", status_code=201, response_model=WaitlistOut)
def join(body: WaitlistIn, db: DbDep) -> WaitlistOut:
    if not body.consent:
        raise HTTPException(status_code=422,
                            detail="Hace falta aceptar la política de privacidad para apuntarte")
    try:
        email = normalize_email(body.email)
    except AccountError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    join_waitlist(db, email, body.kind, load()["privacidad"].version)
    db.commit()
    return WaitlistOut(message="Apuntado. Te escribiremos a ese correo cuando haya sitio.")


@router.get("/free-tier", response_model=FreeTierOut)
def free_tier_info() -> FreeTierOut:
    """Lo que incluye el nivel gratuito, para la página de presentación (sin repetir el número)."""
    return FreeTierOut(full_plans=free_tier().full_plans)
