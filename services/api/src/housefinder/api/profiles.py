"""Entrevista de perfil (F6.2, ADR-0020): preguntas fijas, respuestas libres y confirmación.

Las respuestas y el borrador son datos personales: se guardan cifrados y solo se devuelven a su
organización. Ningún valor va a un log ni a un mensaje de error.
"""

from __future__ import annotations

import base64
import binascii
from datetime import date
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from housefinder.agent.documents import DocumentKind, extract_document
from housefinder.agent.llm import LLMOutputError
from housefinder.agent.profiling import extract_answer
from housefinder.api.deps import ClientDep, DbDep, KeysDep, LLMDep, OrgDep
from housefinder.db.profiles import latest_profile_id
from housefinder.documents.reader import (
    MAX_BYTES,
    OcrUnavailable,
    UnreadableDocument,
    read_document,
    read_text,
)
from housefinder.profiles import interview as iv
from housefinder.profiles import store
from housefinder.profiles.model import ProfileError, UserProfile

router = APIRouter(prefix="/profile", tags=["perfil"])
OWNER = "local"  # hasta la autenticación (G8)


class QuestionOut(BaseModel):
    field: str
    text: str


class AnswerOut(BaseModel):
    question: str
    text: str


class DraftFieldOut(BaseModel):
    field: str
    label: str
    required: bool
    value: str | list[str] | None
    evidence: str | None = None
    source: Literal["respuesta", "calculado", "usuario", "documento"] | None = None
    note: str = ""
    kind: Literal["texto", "ratio", "eur", "bool"] = "texto"


class DocumentOut(BaseModel):
    kind: DocumentKind
    method: str
    fields: list[str]
    truncated: bool


class InterviewOut(BaseModel):
    id: UUID
    status: Literal["en_curso", "confirmada"]
    answers: list[AnswerOut]
    fields: list[DraftFieldOut]
    issues: list[str]
    documents: list[DocumentOut]
    next_question: QuestionOut | None
    complete: bool = Field(description="Están todos los obligatorios: se puede confirmar")
    profile_id: UUID | None


class AnswerIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class DocumentIn(BaseModel):
    kind: DocumentKind
    content_base64: str | None = Field(default=None, max_length=MAX_BYTES * 4 // 3 + 4,
                                       description="PDF, JPG o PNG en base64")
    text: str | None = Field(default=None, max_length=100_000, description="O el texto pegado")


class ConfirmIn(BaseModel):
    values: dict[str, Any] = Field(description="Valor de cada campo, corregido o no")


class ConfirmOut(BaseModel):
    profile_id: UUID


class RegionOut(BaseModel):
    code: str
    name: str


@router.get("/regions", response_model=list[RegionOut])
def regions() -> list[RegionOut]:
    """Comunidades autónomas para corregir la residencia (`data/profiles/comunidades.yaml`)."""
    return [RegionOut(code=f"ES-{code}", name=names[0]) for code, names in iv.regions().items()]


@router.post("/interviews", response_model=InterviewOut, status_code=201)
def start_interview(db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep) -> InterviewOut:
    started = iv.start(db, keys, org, client, OWNER)
    db.commit()
    return _out(started)


@router.get("/interviews/current", response_model=InterviewOut)
def current_interview(db: DbDep, keys: KeysDep, org: OrgDep,
                      client: ClientDep) -> InterviewOut:
    found = iv.current(db, keys, org, client)
    if found is None:
        raise HTTPException(status_code=404, detail="No hay ninguna entrevista en curso")
    return _out(found)


@router.get("/interviews/{interview_id}", response_model=InterviewOut)
def get_interview(interview_id: UUID, db: DbDep, keys: KeysDep, org: OrgDep) -> InterviewOut:
    try:
        return _out(iv.load(db, keys, interview_id, org))
    except iv.InterviewNotFound as exc:
        raise HTTPException(status_code=404, detail="No existe esa entrevista") from exc


@router.post("/interviews/{interview_id}/answers", response_model=InterviewOut)
def answer(interview_id: UUID, body: AnswerIn, db: DbDep, keys: KeysDep, org: OrgDep,
           llm: LLMDep) -> InterviewOut:
    try:
        updated = iv.answer(db, keys, interview_id, org, body.text,
                            lambda question, text: extract_answer(llm, question, text),
                            date.today())
    except iv.InterviewNotFound as exc:
        raise HTTPException(status_code=404, detail="No existe esa entrevista") from exc
    except iv.InterviewClosed as exc:
        raise HTTPException(status_code=409, detail="La entrevista ya está terminada") from exc
    except LLMOutputError as exc:
        raise HTTPException(status_code=503, detail="El modelo no ha respondido: vuelve a "
                                                    "intentarlo") from exc
    db.commit()
    return _out(updated)


@router.post("/interviews/{interview_id}/documents", response_model=InterviewOut)
def add_document(interview_id: UUID, body: DocumentIn, db: DbDep, keys: KeysDep, org: OrgDep,
                 llm: LLMDep) -> InterviewOut:
    """Lee el documento en memoria, extrae sus campos y lo descarta (ADR-0021)."""
    try:
        if body.content_base64:
            read = read_document(base64.b64decode(body.content_base64, validate=True))
        elif body.text and body.text.strip():
            read = read_text(body.text)
        else:
            raise HTTPException(status_code=422, detail="Falta el documento o su texto")
        updated = iv.add_document(db, keys, interview_id, org, body.kind, read.text, read.method,
                                  lambda kind, text: extract_document(llm, kind, text),
                                  date.today())
    except binascii.Error as exc:
        raise HTTPException(status_code=422, detail="El fichero no llega bien codificado") from exc
    except OcrUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UnreadableDocument as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except iv.InterviewNotFound as exc:
        raise HTTPException(status_code=404, detail="No existe esa entrevista") from exc
    except iv.InterviewClosed as exc:
        raise HTTPException(status_code=409, detail="La entrevista ya está terminada") from exc
    except LLMOutputError as exc:
        raise HTTPException(status_code=503, detail="El modelo no ha respondido: vuelve a "
                                                    "intentarlo") from exc
    db.commit()
    return _out(updated)


@router.post("/interviews/{interview_id}/confirm", response_model=ConfirmOut)
def confirm(interview_id: UUID, body: ConfirmIn, db: DbDep, keys: KeysDep,
            org: OrgDep) -> ConfirmOut:
    try:
        profile_id = iv.confirm(db, keys, interview_id, org, OWNER, body.values)
    except iv.InterviewNotFound as exc:
        raise HTTPException(status_code=404, detail="No existe esa entrevista") from exc
    except iv.InterviewClosed as exc:
        raise HTTPException(status_code=409, detail="La entrevista ya está confirmada") from exc
    except ProfileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc  # campos, sin valores
    db.commit()
    return ConfirmOut(profile_id=profile_id)


class ProfileOut(BaseModel):
    id: UUID
    values: dict[str, Any] = Field(description="Valor de cada campo del perfil confirmado")
    missing_search: list[str] = Field(description="Supuestos de búsqueda sin valor")


class SearchAssumptionsIn(BaseModel):
    values: dict[str, Any] = Field(description="Supuestos de búsqueda (ADR-0022)")


@router.get("/current", response_model=ProfileOut)
def current_profile(db: DbDep, keys: KeysDep, org: OrgDep, client: ClientDep) -> ProfileOut:
    profile_id, profile = _latest(db, keys, org, client)
    return _profile_out(profile_id, profile)


@router.put("/current/search", response_model=ProfileOut)
def set_search_assumptions(body: SearchAssumptionsIn, db: DbDep, keys: KeysDep,
                           org: OrgDep, client: ClientDep) -> ProfileOut:
    """Cambia solo los supuestos de búsqueda del perfil confirmado."""
    profile_id, profile = _latest(db, keys, org, client)
    current = profile.model_dump(mode="json")
    wanted = {k: v for k, v in body.values.items() if k in iv.SEARCH_FIELDS}
    try:
        updated = iv.to_profile({**current, **wanted})
    except ProfileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.save(db, keys, profile_id, org, updated)
    db.commit()
    return _profile_out(profile_id, updated)


def _latest(db: DbDep, keys: KeysDep, org: OrgDep, client: UUID) -> tuple[UUID, UserProfile]:
    profile_id = latest_profile_id(db, org, client)
    if profile_id is None:
        raise HTTPException(status_code=404, detail="Todavía no hay un perfil confirmado")
    return profile_id, store.load(db, keys, profile_id, org)


def _profile_out(profile_id: UUID, profile: UserProfile) -> ProfileOut:
    values = profile.model_dump(mode="json")
    return ProfileOut(id=profile_id, values=values,
                      missing_search=[k for k in iv.SEARCH_FIELDS if values.get(k) is None])


@router.delete("/interviews/{interview_id}", status_code=204)
def discard(interview_id: UUID, db: DbDep, org: OrgDep) -> None:
    try:
        iv.discard(db, interview_id, org)
    except iv.InterviewNotFound as exc:
        raise HTTPException(status_code=404, detail="No existe esa entrevista") from exc
    db.commit()


def _out(found: iv.Interview) -> InterviewOut:
    state = found.state
    question = found.next_question
    text = iv.question_text(state)
    fields = []
    for q in iv.QUESTIONS:
        draft = state.draft.get(q.field)
        fields.append(DraftFieldOut(
            field=q.field, label=q.label, required=q.required,
            value=draft.value if draft else None, evidence=draft.evidence if draft else None,
            source=draft.source if draft else None, note=draft.note if draft else ""))
    for name, (label, kind) in iv.SEARCH_FIELDS.items():  # supuestos sin fuente (ADR-0022)
        fields.append(DraftFieldOut(field=name, label=label, required=False, value=None,
                                    kind=kind))
    for name, label in iv.DOCUMENT_FIELDS.items():  # solo los rellena la declaración
        draft = state.draft.get(name)
        fields.append(DraftFieldOut(
            field=name, label=label, required=False, value=draft.value if draft else None,
            evidence=draft.evidence if draft else None, source=draft.source if draft else None,
            note=draft.note if draft else ""))
    return InterviewOut(
        id=found.id, status=found.status,
        answers=[AnswerOut(question=a["question"], text=a["text"]) for a in state.answers],
        fields=fields, issues=state.issues,
        documents=[DocumentOut(**d) for d in state.documents],
        next_question=QuestionOut(field=question.field, text=text)
        if question is not None and text is not None and found.status == "en_curso" else None,
        complete=all(q.field in state.draft for q in iv.QUESTIONS if q.required),
        profile_id=found.profile_id)
