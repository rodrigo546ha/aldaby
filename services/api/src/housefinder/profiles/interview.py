"""Entrevista de perfil: preguntas fijas, extracción con evidencia y borrador cifrado (ADR-0020).

El código elige el siguiente dato que falta y hace su pregunta. El modelo solo saca de la respuesta
lo que el usuario ha dicho, con su cita (`agent/profiling.py`), y aquí se convierte: ingresos
anuales o en catorce pagas a mensuales, edad a año de nacimiento, nombre a código de comunidad.
Cada conversión deja su nota con la cuenta. El usuario confirma campo a campo y solo entonces se
valida el `UserProfile` y se guarda cifrado.

La entrevista (respuestas literales y borrador) se guarda en un sobre (ADR-0011), atado a su fila
y su organización. Ni las respuestas ni los valores van nunca a un log ni a un mensaje de error.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

import yaml

from housefinder.agent.documents import CheckedDocument
from housefinder.agent.profiling import CheckedAnswer
from housefinder.core.figures import money
from housefinder.crypto.envelope import KeyProvider, Sealed, open_sealed, seal
from housefinder.db.connection import Connection
from housefinder.db.interviews import (
    InterviewRow,
    delete_interview,
    get_interview,
    insert_interview,
    latest_open_interview,
    mark_confirmed,
    update_interview,
)
from housefinder.db.profiles import SealedRow
from housefinder.profiles import store
from housefinder.profiles.model import UserProfile

TABLE = "profile_interviews"
Source = Literal["respuesta", "calculado", "usuario", "documento"]


@dataclass(frozen=True)
class Question:
    field: str  # campo de UserProfile
    label: str
    text: str
    required: bool


# Orden de la entrevista: primero lo que el plan necesita sí o sí
QUESTIONS = (
    Question("birth_year", "Año de nacimiento",
             "Para empezar, ¿en qué año naciste? Si lo prefieres, dime tu edad.", True),
    Question("residence", "Comunidad de residencia",
             "¿En qué comunidad autónoma vives? Cambia los impuestos que pagas.", True),
    Question("net_monthly_income", "Ingresos netos al mes",
             "¿Cuánto ingresas al mes, neto, después de impuestos? Si lo sabes al año o en catorce "
             "pagas, dímelo así.", True),
    Question("existing_monthly_debt", "Cuotas de préstamos al mes",
             "¿Pagas ahora alguna cuota de hipoteca o préstamo? Si es así, ¿cuánto al mes en "
             "total?", True),
    Question("available_savings", "Ahorro disponible",
             "¿Cuánto ahorro podrías dedicar a la compra, entre entrada y gastos?", True),
    Question("descendant_birth_years", "Años de nacimiento de los hijos",
             "¿Tienes hijos? Si es así, ¿en qué año nació cada uno? Cuentan en el IRPF.", False),
    Question("goal", "Objetivo",
             "¿Qué buscas sobre todo: renta cada mes, que el inmueble gane valor, o las dos "
             "cosas?", False),
    Question("horizon_years", "Horizonte en años",
             "¿Cuántos años piensas mantener la inversión?", False),
    Question("risk_tolerance", "Riesgo que aceptas",
             "Si bajara el alquiler o subieran los tipos, ¿cuánto riesgo aceptarías: poco, "
             "medio o mucho?", False),
    Question("management", "Gestión",
             "¿Quieres gestionar tú el alquiler o prefieres delegarlo en alguien?", False),
)
BY_FIELD = {q.field: q for q in QUESTIONS}
# Campos del perfil que no se preguntan: solo los rellena la declaración de la renta (ADR-0021)
DOCUMENT_FIELDS = {"taxable_base": "Base liquidable general (sin el alquiler)",
                   "savings_base": "Base liquidable del ahorro"}
DOCUMENT_NAMES = {"nomina": "nómina", "declaracion": "declaración de la renta",
                  "extracto": "extracto bancario"}
READ_BY = {"texto": "texto pegado", "pdf": "PDF", "ocr": "escaneo leído con OCR",
           "pdf+ocr": "PDF con páginas escaneadas leídas con OCR"}
NOT_UNDERSTOOD = "No lo he entendido. "


class InterviewNotFound(LookupError):
    pass


class InterviewClosed(ValueError):
    """La entrevista ya está confirmada: no admite más respuestas."""


@dataclass(frozen=True)
class DraftField:
    value: str | list[str] | None
    evidence: str | None
    source: Source
    note: str = ""


@dataclass
class State:
    """Lo que va dentro del sobre."""

    answers: list[dict[str, str]] = field(default_factory=list)  # pregunta, campo y texto
    draft: dict[str, DraftField] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)  # opcionales que el usuario no contestó
    issues: list[str] = field(default_factory=list)  # por qué no se entendió la última respuesta
    asked: str | None = None  # campo de la última pregunta
    documents: list[dict[str, Any]] = field(default_factory=list)  # leídos, sin su texto

    def to_json(self) -> bytes:
        return json.dumps({
            "answers": self.answers, "skipped": self.skipped, "issues": self.issues,
            "asked": self.asked, "documents": self.documents,
            "draft": {k: v.__dict__ for k, v in self.draft.items()},
        }, ensure_ascii=False).encode()

    @classmethod
    def from_json(cls, raw: bytes) -> State:
        data = json.loads(raw)
        return cls(answers=data["answers"], skipped=data["skipped"], issues=data["issues"],
                   asked=data["asked"], documents=data.get("documents", []),
                   draft={k: DraftField(**v) for k, v in data["draft"].items()})


@dataclass(frozen=True)
class Interview:
    id: UUID
    status: Literal["en_curso", "confirmada"]
    state: State
    profile_id: UUID | None

    @property
    def next_question(self) -> Question | None:
        return next_question(self.state)


# --- Lógica de la entrevista (pura) ------------------------------------------------------------


def next_question(state: State) -> Question | None:
    """El primer obligatorio que falta; después, los opcionales sin contestar ni saltados."""
    for question in QUESTIONS:
        if question.field in state.draft:
            continue
        if question.required or question.field not in state.skipped:
            return question
    return None


def question_text(state: State) -> str | None:
    question = next_question(state)
    if question is None:
        return None
    retry = question.required and question.field == state.asked and state.issues
    return (NOT_UNDERSTOOD if retry else "") + question.text


def apply_answer(state: State, asked: str, text: str, checked: CheckedAnswer,
                 today: date) -> State:
    """El borrador con lo que la respuesta dice de cualquier campo (no solo del preguntado)."""
    draft = dict(state.draft)
    # Lo que la respuesta dice de otros campos solo rellena huecos: con qwen3, «uno nació en 2016»
    # (de un hijo) pisaba el año de nacimiento del usuario. Se corrige al confirmar.
    for name, value in derive(checked, today).items():
        if name == asked or name not in draft:
            draft[name] = value
    if asked == "descendant_birth_years" and asked not in draft:
        years = _years_in(text, today)
        if years:  # con qwen3 la lista de hijos llegaba vacía aunque el usuario diera los años
            draft[asked] = DraftField(years, text, "respuesta", "Años escritos en tu respuesta.")
    skipped = list(state.skipped)
    issues: list[str] = []
    if asked not in draft:
        issues = [_issue(asked, checked)]
        if not BY_FIELD[asked].required and asked not in skipped:
            skipped.append(asked)  # un opcional sin respuesta no se vuelve a preguntar
    answers = [*state.answers, {"field": asked, "question": BY_FIELD[asked].text, "text": text}]
    return State(answers, draft, skipped, issues, asked)


def apply_document(state: State, checked: CheckedDocument, method: str, today: date) -> State:
    """El borrador con los campos del documento. Pisan lo dicho en la conversación: el usuario lo
    ha subido para eso, y confirma al final. El texto del documento no se guarda."""
    found = document_fields(checked, method, today)
    draft = {**state.draft, **found}
    entry = {"kind": checked.kind, "method": method, "fields": sorted(found),
             "truncated": checked.truncated}
    issues = [] if found else [
        f"No he encontrado datos en la {DOCUMENT_NAMES[checked.kind]}. Si es un escaneo, prueba "
        "con el PDF original o una foto más nítida."]
    if checked.truncated:
        issues.append("El documento es largo y solo se ha leído el principio.")
    return State(state.answers, draft, state.skipped, issues, state.asked,
                 [*state.documents, entry])


def document_fields(checked: CheckedDocument, method: str, today: date) -> dict[str, DraftField]:
    """Campos del perfil desde lo verificado en el documento; las cuentas, aquí y con su nota."""
    origin = f"De tu {DOCUMENT_NAMES[checked.kind]} ({READ_BY.get(method, method)})."
    if method in ("ocr", "pdf+ocr"):
        origin += " Comprueba la cifra: el OCR puede leer mal un número."
    out: dict[str, DraftField] = {}
    f = checked.fields

    if checked.kind == "nomina" and (net := checked.verified("net_pay")) is not None:
        amount = Decimal(str(net))
        if checked.verified("extra_pay_prorated") == "sí":
            out["net_monthly_income"] = DraftField(
                str(money(amount)), f["net_pay"].evidence, "documento",
                f"{origin} Pagas extra prorrateadas: el líquido ya las incluye.")
        else:
            out["net_monthly_income"] = DraftField(
                str(money(amount * 14 / 12)), f["net_pay"].evidence, "documento",
                f"{origin} {amount} € × 14 pagas / 12 meses: supone catorce pagas sin prorrata; "
                "corrígelo si cobras otras.")

    if checked.kind == "declaracion":
        year = checked.verified("fiscal_year")
        about = f" Ejercicio {int(Decimal(str(year)))}." if year is not None else ""
        for name in ("taxable_base", "savings_base"):
            if (value := checked.verified(name)) is not None:
                extra = (" Si ya declaras alquileres, réstalos: la del perfil es sin el alquiler."
                         if name == "taxable_base" else "")
                out[name] = DraftField(str(money(Decimal(str(value)))), f[name].evidence,
                                       "documento", origin + about + extra)
        years = [c for c in checked.descendant_birth_years if c.status == "verificado"
                 and 1900 <= int(Decimal(str(c.value))) <= today.year]
        if years:
            out["descendant_birth_years"] = DraftField(
                [str(int(Decimal(str(c.value)))) for c in years],
                " · ".join(c.evidence or "" for c in years), "documento", origin)

    if checked.kind == "extracto":
        if (balance := checked.verified("closing_balance")) is not None:
            out["available_savings"] = DraftField(
                str(money(Decimal(str(balance)))), f["closing_balance"].evidence, "documento",
                f"{origin} Es el saldo de la cuenta: pon lo que de verdad dedicarías a la compra.")
        loans: dict[str, Decimal] = {}  # una cuota por concepto, aunque el extracto tenga varias
        for concept, amount in checked.loan_payments:
            if concept.status == "verificado" and amount.status == "verificado":
                loans.setdefault(_fold(str(concept.value)), Decimal(str(amount.value)))
        if loans:
            total = sum(loans.values(), Decimal(0))
            out["existing_monthly_debt"] = DraftField(
                str(money(total)), " · ".join(c.evidence or "" for c, _ in checked.loan_payments
                                              if c.status == "verificado"),
                "documento", f"{origin} Suma de {len(loans)} cuota(s) distintas del extracto.")
    return out


def _adult(birth_year: int, today: date) -> bool:
    """Un año de nacimiento de quien invierte: entre dieciocho y cien años."""
    return today.year - 100 <= birth_year <= today.year - 18


def _years_in(text: str, today: date) -> list[str]:
    """Años de cuatro cifras plausibles para un hijo, tal como los escribe el usuario."""
    return [y for y in re.findall(r"\b(\d{4})\b", text) if 1950 <= int(y) <= today.year]


def _issue(asked: str, checked: CheckedAnswer) -> str:
    """Para el usuario, sin los motivos internos de la comprobación."""
    place = checked.fields["residence"]
    if asked == "residence" and place.status == "verificado":
        return (f"No sé de qué comunidad es «{place.evidence}»: dime el nombre de la comunidad "
                "autónoma.")
    return (f"No he encontrado «{BY_FIELD[asked].label.lower()}» en tu respuesta. Si es una "
            "cantidad, escríbela con cifras (por ejemplo, 2.500).")


def derive(checked: CheckedAnswer, today: date) -> dict[str, DraftField]:
    """Campos de UserProfile desde lo verificado; las cuentas, aquí y con su nota."""
    out: dict[str, DraftField] = {}
    f = checked.fields

    year = checked.verified("birth_year")
    if year is not None and _adult(int(year), today):
        out["birth_year"] = DraftField(str(int(year)), f["birth_year"].evidence, "respuesta")
    elif (age := checked.verified("age")) is not None and _adult(today.year - int(age), today):
        out["birth_year"] = DraftField(
            str(today.year - int(age)), f["age"].evidence, "calculado",
            f"{today.year} − {int(age)} años: puede ser un año antes según tu cumpleaños.")

    if (place := f["residence"]).status == "verificado":
        found = region_in(place.evidence or "")
        if found is not None:
            code, name = found
            out["residence"] = DraftField(code, place.evidence, "calculado", name)

    if (income := checked.verified("income")) is not None:
        out["net_monthly_income"] = _monthly(Decimal(income), checked)

    if (debt := checked.verified("debt")) is not None:
        out["existing_monthly_debt"] = DraftField(str(money(Decimal(debt))), f["debt"].evidence,
                                                  "respuesta")
    elif checked.verified("no_debt") == "sí":
        out["existing_monthly_debt"] = DraftField("0", f["no_debt"].evidence, "respuesta")

    if (savings := checked.verified("savings")) is not None:
        out["available_savings"] = DraftField(str(money(Decimal(savings))),
                                              f["savings"].evidence, "respuesta")

    years = [c for c in checked.children_birth_years if c.status == "verificado"]
    ages = [c for c in checked.children_ages if c.status == "verificado"]
    if years:
        out["descendant_birth_years"] = DraftField(
            [str(int(Decimal(c.value or 0))) for c in years],
            " · ".join(c.evidence or "" for c in years), "respuesta")
    elif ages:
        out["descendant_birth_years"] = DraftField(
            [str(today.year - int(Decimal(c.value or 0))) for c in ages],
            " · ".join(c.evidence or "" for c in ages), "calculado",
            f"{today.year} menos la edad de cada hijo: puede ser un año antes.")
    elif checked.verified("no_children") == "sí":
        out["descendant_birth_years"] = DraftField([], f["no_children"].evidence, "respuesta")

    for name in ("goal", "risk_tolerance", "management"):
        if (choice := checked.verified(name)) is not None:
            out[name] = DraftField(str(choice), f[name].evidence, "respuesta")
    if (horizon := checked.verified("horizon_years")) is not None:
        out["horizon_years"] = DraftField(str(int(Decimal(horizon))), f["horizon_years"].evidence,
                                          "respuesta")
    return out


def _monthly(amount: Decimal, checked: CheckedAnswer) -> DraftField:
    evidence = checked.fields["income"].evidence
    period = checked.verified("income_period") or "mes"
    payments = checked.verified("income_payments")
    if period == "año":
        return DraftField(str(money(amount / 12)), evidence, "calculado",
                          f"{amount} € al año / 12 meses.")
    if payments is not None and Decimal(payments) != 12:
        n = int(Decimal(payments))
        return DraftField(str(money(amount * n / 12)), evidence, "calculado",
                          f"{amount} € × {n} pagas / 12 meses.")
    return DraftField(str(money(amount)), evidence, "respuesta")


def region_in(text: str) -> tuple[str, str] | None:
    """Código y nombre de la comunidad que nombra el texto (el nombre más largo gana)."""
    folded = f" {_fold(text)} "
    best: tuple[int, str, str] | None = None
    for code, names in regions().items():
        for name in names:
            if f" {_fold(name)} " in folded and (best is None or len(name) > best[0]):
                best = (len(name), f"ES-{code}", names[0])
    return (best[1], best[2]) if best else None


@lru_cache
def regions() -> dict[str, list[str]]:
    path = Path(__file__).resolve().parents[3] / "data" / "profiles" / "comunidades.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(code): [str(n) for n in names] for code, names in data.items()}


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join("".join(c if c.isalnum() else " " for c in plain).split())


def to_profile(values: Mapping[str, Any]) -> UserProfile:
    """Lo que el usuario confirma (o corrige) → `UserProfile` validado. Vacío = sin dato."""
    data = {k: v for k, v in values.items()
            if (k in BY_FIELD or k in DOCUMENT_FIELDS) and v not in (None, "")}
    if "descendant_birth_years" in data:
        data["descendant_birth_years"] = tuple(int(y) for y in data["descendant_birth_years"])
    return UserProfile.parse(data)


# --- Almacén cifrado ------------------------------------------------------------------------------


def associated_data(interview_id: UUID, org_id: UUID) -> bytes:
    return f"{TABLE}:{interview_id}:{org_id}".encode()


def start(conn: Connection, keys: KeyProvider, org_id: UUID, owner_id: str) -> Interview:
    interview_id = uuid4()
    state = State()
    insert_interview(conn, interview_id, org_id, owner_id,
                     _row(_seal(state, interview_id, org_id, keys)))
    return Interview(interview_id, "en_curso", state, None)


def load(conn: Connection, keys: KeyProvider, interview_id: UUID, org_id: UUID) -> Interview:
    row = get_interview(conn, interview_id, org_id)
    if row is None:
        raise InterviewNotFound(str(interview_id))
    return _open(row, interview_id, org_id, keys)


def current(conn: Connection, keys: KeyProvider, org_id: UUID) -> Interview | None:
    interview_id = latest_open_interview(conn, org_id)
    return load(conn, keys, interview_id, org_id) if interview_id else None


def answer(conn: Connection, keys: KeyProvider, interview_id: UUID, org_id: UUID, text: str,
           extract: Callable[[str, str], CheckedAnswer], today: date) -> Interview:
    """Extrae la respuesta a la pregunta en curso y guarda el borrador."""
    interview = load(conn, keys, interview_id, org_id)
    if interview.status != "en_curso":
        raise InterviewClosed(str(interview_id))
    question = next_question(interview.state)
    if question is None:
        raise InterviewClosed(str(interview_id))
    checked = extract(question.text, text)
    state = apply_answer(interview.state, question.field, text, checked, today)
    update_interview(conn, interview_id, org_id, _row(_seal(state, interview_id, org_id, keys)))
    return Interview(interview_id, "en_curso", state, None)


def add_document(conn: Connection, keys: KeyProvider, interview_id: UUID, org_id: UUID,
                 kind: str, text: str, method: str,
                 extract: Callable[[str, str], CheckedDocument], today: date) -> Interview:
    """Extrae los campos del texto del documento y los pone en el borrador; el texto se descarta."""
    interview = load(conn, keys, interview_id, org_id)
    if interview.status != "en_curso":
        raise InterviewClosed(str(interview_id))
    state = apply_document(interview.state, extract(kind, text), method, today)
    update_interview(conn, interview_id, org_id, _row(_seal(state, interview_id, org_id, keys)))
    return Interview(interview_id, "en_curso", state, None)


def confirm(conn: Connection, keys: KeyProvider, interview_id: UUID, org_id: UUID,
            owner_id: str, values: Mapping[str, Any]) -> UUID:
    """Valida lo confirmado y guarda el perfil cifrado. `ProfileError` si no vale (sin valores)."""
    interview = load(conn, keys, interview_id, org_id)
    if interview.status != "en_curso":
        raise InterviewClosed(str(interview_id))
    profile = to_profile(values)
    profile_id = store.save_new(conn, keys, org_id, owner_id, profile)
    mark_confirmed(conn, interview_id, org_id, profile_id)
    return profile_id


def discard(conn: Connection, interview_id: UUID, org_id: UUID) -> None:
    """Borra la entrevista y sus respuestas; el perfil confirmado, si lo hay, se queda."""
    if not delete_interview(conn, interview_id, org_id):
        raise InterviewNotFound(str(interview_id))


def _open(row: InterviewRow, interview_id: UUID, org_id: UUID, keys: KeyProvider) -> Interview:
    sealed = Sealed(row.sealed.data_enc, row.sealed.dek_enc, row.sealed.key_id,
                    row.sealed.version)
    state = State.from_json(open_sealed(sealed, associated_data(interview_id, org_id), keys))
    return Interview(interview_id, row.status, state, row.profile_id)


def _seal(state: State, interview_id: UUID, org_id: UUID, keys: KeyProvider) -> Sealed:
    return seal(state.to_json(), associated_data(interview_id, org_id), keys)


def _row(sealed: Sealed) -> SealedRow:
    return SealedRow(sealed.data_enc, sealed.dek_enc, sealed.key_id, sealed.version)
