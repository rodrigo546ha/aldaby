"""Textos legales y su aceptación (F7.4, ADR-0039).

Los textos se leen sin sesión: tienen que poder consultarse antes de entrar. Aceptarlos exige
sesión y la versión vigente de cada uno.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from housefinder.db.legal import record_acceptance
from housefinder.legal.documents import LegalDocument, audience_of, load

from .deps import DbDep, SessionDep, pending_legal

router = APIRouter(prefix="/legal", tags=["textos legales"])


class LegalSummaryOut(BaseModel):
    id: str
    title: str
    version: int
    effective_from: date
    requires_acceptance: bool
    verified: bool  # revisado por el abogado


class LegalDocumentOut(LegalSummaryOut):
    text: str  # Markdown
    missing: list[str]  # datos del titular que faltan


class AcceptanceIn(BaseModel):
    documents: dict[str, int]  # id → versión que se acepta


class PendingOut(BaseModel):
    pending: list[str]


def doc_id_not_for(doc: LegalDocument, role: str) -> bool:
    """Si la cuenta no tiene que aceptar este documento."""
    return not doc.requires_acceptance or audience_of(role) not in doc.audience


def _summary(doc: LegalDocument) -> LegalSummaryOut:
    return LegalSummaryOut(id=doc.id, title=doc.title, version=doc.version,
                           effective_from=doc.effective_from,
                           requires_acceptance=doc.requires_acceptance, verified=doc.verified)


@router.get("", response_model=list[LegalSummaryOut])
def list_documents() -> list[LegalSummaryOut]:
    return [_summary(doc) for doc in load().values()]


@router.get("/{document_id}", response_model=LegalDocumentOut)
def get_document(document_id: str) -> LegalDocumentOut:
    doc = load().get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return LegalDocumentOut(**_summary(doc).model_dump(), text=doc.text,
                            missing=list(doc.missing))


@router.post("/accept", response_model=PendingOut)
def accept(body: AcceptanceIn, db: DbDep, current: SessionDep) -> PendingOut:
    """Acepta las versiones vigentes. Una versión que no es la vigente se rechaza: el texto cambió
    mientras se leía."""
    if current is None:
        raise HTTPException(status_code=401, detail="Inicia sesión para seguir")
    documents = load()
    for document_id, version in body.documents.items():
        doc = documents.get(document_id)
        if doc is None or doc_id_not_for(doc, current.role):
            raise HTTPException(status_code=422, detail=f"No se acepta el documento {document_id}")
        if doc.version != version:
            raise HTTPException(status_code=409,
                                detail=f"«{doc.title}» ha cambiado: vuelve a leerlo")
    for document_id, version in body.documents.items():
        record_acceptance(db, current.account_id, document_id, version)
    db.commit()
    return PendingOut(pending=pending_legal(db, current.account_id, current.role))
