"""Marca del profesional en sus planes (F7.3, ADR-0030)."""

from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from housefinder.api.deps import DbDep, OrgDep
from housefinder.branding import service
from housefinder.branding.logo import MAX_BYTES, LogoError

router = APIRouter(prefix="/branding", tags=["marca"])


class BrandingOut(BaseModel):
    display_name: str | None
    contact: str | None
    color: str | None
    intro: str | None
    has_logo: bool


class BrandingIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=400)
    contact: str | None = Field(default=None, max_length=400)
    color: str | None = Field(default=None, max_length=20)
    intro: str | None = Field(default=None, max_length=2000)


class LogoIn(BaseModel):
    content_base64: str = Field(max_length=MAX_BYTES * 4 // 3 + 16)


@router.get("", response_model=BrandingOut)
def get_branding(db: DbDep, org: OrgDep) -> BrandingOut:
    return _out(service.load(db, org))


@router.put("", response_model=BrandingOut)
def put_branding(body: BrandingIn, db: DbDep, org: OrgDep) -> BrandingOut:
    try:
        service.save_texts(db, org, body.display_name, body.contact, body.color, body.intro)
    except service.BrandingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return _out(service.load(db, org))


@router.put("/logo", response_model=BrandingOut)
def put_logo(body: LogoIn, db: DbDep, org: OrgDep) -> BrandingOut:
    try:
        service.save_logo(db, org, base64.b64decode(body.content_base64, validate=True))
    except binascii.Error as exc:
        raise HTTPException(status_code=422, detail="La imagen no llega bien codificada") from exc
    except LogoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return _out(service.load(db, org))


@router.delete("/logo", response_model=BrandingOut)
def delete_logo(db: DbDep, org: OrgDep) -> BrandingOut:
    service.save_logo(db, org, None)
    db.commit()
    return _out(service.load(db, org))


@router.get("/logo", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def get_logo(db: DbDep, org: OrgDep) -> Response:
    logo = service.load(db, org).logo_png
    if logo is None:
        raise HTTPException(status_code=404, detail="Sin logotipo")
    return Response(logo, media_type="image/png", headers={"Cache-Control": "private, no-cache"})


def _out(brand: service.Branding) -> BrandingOut:
    return BrandingOut(display_name=brand.display_name, contact=brand.contact,
                       color=brand.color, intro=brand.intro, has_logo=brand.logo_png is not None)
