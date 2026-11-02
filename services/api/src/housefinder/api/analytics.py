"""Recuento de visitas sin cookies (F8.6, ADR-0042). Público y siempre 204: no dice si contó.

No se guarda la IP, el navegador ni la hora: solo se suma 1 al día, la ruta normalizada, el dominio
de origen y la fuente. Quien pide no ser contado (GPC, DNT) no se cuenta.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from housefinder.analytics.visits import counts, visit
from housefinder.db.analytics import count_view

from .deps import DbDep

router = APIRouter(prefix="/analytics", tags=["analítica"])
MADRID = ZoneInfo("Europe/Madrid")


class EventIn(BaseModel):
    path: str = Field(max_length=300)
    referrer: str | None = Field(default=None, max_length=500)
    source: str | None = Field(default=None, max_length=100)  # utm_source


@router.post("/event", status_code=204)
def event(body: EventIn, request: Request, db: DbDep) -> None:
    headers = {k.lower(): v for k, v in request.headers.items()}
    if not counts(headers):
        return
    seen = visit(body.path, body.referrer, body.source, request.url.hostname)
    if seen is None:
        return
    count_view(db, datetime.now(MADRID).date(), seen.path, seen.referrer, seen.source)
    db.commit()
