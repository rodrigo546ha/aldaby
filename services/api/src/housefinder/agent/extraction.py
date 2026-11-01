"""Extracción de inmuebles de un texto libre, con evidencia comprobada (ADR-0013).

El LLM devuelve cada campo con una cita literal del documento. Después, sin LLM:
1. la cita tiene que estar en el documento (espacios normalizados);
2. si hay varios lotes, la cita tiene que estar en el tramo de su lote: desde su etiqueta («Lote 2»)
   hasta la etiqueta del lote siguiente (ADR-0014);
3. el valor tiene que salir de la cita: un importe o una superficie es uno de los números de la
   cita; una referencia catastral está en la cita con su formato; un texto está en ella como
   palabras enteras.
Lo que no pasa se descarta con su motivo. Ninguna cifra que quede es inventada: está en la fuente,
en la parte que habla de ese lote.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, Field

from housefinder.agent.llm import LLMClient

PropertyType = Literal[
    "vivienda", "local", "oficina", "garaje", "trastero", "edificio", "suelo", "rustica", "otro"
]
NUMBER_IN_TEXT = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")
CADASTRAL_REF = re.compile(r"^(?:[0-9A-Z]{14}|[0-9A-Z]{20})$")
NO_SPAN = "no se sabe qué tramo del documento es de este lote"
PLACEHOLDERS = {"value", "valor"}  # el modelo escribe el nombre del campo en vez del dato

Span = tuple[int, int]  # [inicio, fin) en el documento normalizado


class Quoted(BaseModel):
    value: str | None = Field(
        description="Valor del campo, o null si el documento no lo dice. Números sin separador "
                    "de miles y con punto decimal (1290109.45)."
    )
    evidence: str | None = Field(
        description="Cita literal y exacta del documento de la que sale el valor (una frase o "
                    "un fragmento, copiado sin cambiar nada). null si no hay valor."
    )


class LotExtraction(BaseModel):
    label: Quoted = Field(description="Nombre del lote tal como aparece (Lote 1, 1., etc.)")
    property_type: PropertyType
    property_type_evidence: str | None = Field(description="Cita literal que indica el tipo")
    address: Quoted = Field(description="Dirección del inmueble (no la de una oficina o registro)")
    municipality: Quoted
    province: Quoted
    cadastral_ref: Quoted = Field(description="Referencia catastral de 14 o 20 caracteres")
    built_area_m2: Quoted = Field(description="Superficie en m²")
    floor: Quoted = Field(description="Planta o piso")
    price: Quoted = Field(description="Precio de venta o tipo de licitación (euros)")
    deposit: Quoted = Field(description="Garantía o fianza para pujar (euros)")


class DocumentExtraction(BaseModel):
    is_correction: bool = Field(description="True si el documento corrige otro anuncio")
    corrected_reference: Quoted = Field(
        description="Identificador o fecha del anuncio que se corrige, si lo es"
    )
    lots: list[LotExtraction] = Field(description="Un elemento por inmueble o lote en venta")


INSTRUCTIONS = """Eres un extractor de datos de anuncios de venta de inmuebles en España.
Del documento, extrae cada inmueble o lote que se vende o subasta. Para cada campo:
- copia en `evidence` el fragmento EXACTO del documento del que sale el valor, sin reescribirlo;
- si el documento no da el dato, deja value y evidence a null; no lo deduzcas ni lo calcules;
- la dirección es la del inmueble, nunca la de la oficina, el registro o el lugar de la subasta;
- en `value` escribe el dato (25802189, Madrid), nunca la palabra «value» ni la cita entera;
- los números van sin separador de miles y con punto decimal.
No inventes lotes: si el documento no vende inmuebles, devuelve una lista vacía."""


Operation = Literal["venta", "alquiler", "desconocida"]


class ListingExtraction(BaseModel):
    """Un anuncio de un portal o de una agencia: un solo inmueble (F4.1, ADR-0015)."""

    operation: Operation = Field(description="Si el anuncio vende o alquila el inmueble")
    operation_evidence: str | None = Field(description="Cita literal que indica la operación")
    property_type: PropertyType
    property_type_evidence: str | None = Field(description="Cita literal que indica el tipo")
    price: Quoted = Field(description="Precio pedido en euros: de venta, o al mes si se alquila")
    built_area_m2: Quoted = Field(description="Superficie construida en m²")
    usable_area_m2: Quoted = Field(description="Superficie útil en m², solo si la da aparte")
    rooms: Quoted = Field(description="Número de habitaciones o dormitorios")
    bathrooms: Quoted = Field(description="Número de baños")
    floor: Quoted = Field(description="Planta o piso (bajo, 1ª, ático…)")
    condition: Quoted = Field(
        description="Estado de conservación con las palabras del anuncio (a reformar, buen "
                    "estado, obra nueva…)"
    )
    address: Quoted = Field(description="Calle y número del inmueble, si el anuncio los da")
    municipality: Quoted
    cadastral_ref: Quoted = Field(description="Referencia catastral de 14 o 20 caracteres")
    year_built: Quoted = Field(description="Año de construcción")
    community_fees: Quoted = Field(description="Gastos de comunidad al mes, en euros")


LISTING_INSTRUCTIONS = """Eres un extractor de datos de anuncios de inmuebles en España.
El documento es el texto de la página de un anuncio (un portal o una agencia). Extrae los datos del
inmueble anunciado, no los de otros anuncios recomendados ni los de la agencia. Para cada campo:
- copia en `evidence` el fragmento EXACTO del documento del que sale el valor, sin reescribirlo;
- si el documento no da el dato, deja value y evidence a null; no lo deduzcas ni lo calcules;
- en `value` escribe el dato (235000, Getafe, 2ª), nunca la palabra «value» ni la cita entera;
- los números van sin separador de miles y con punto decimal."""


FieldKind = Literal["number", "cadastral", "text"]
FIELD_KINDS: dict[str, FieldKind] = {
    "label": "text",
    "address": "text",
    "municipality": "text",
    "province": "text",
    "floor": "text",
    "cadastral_ref": "cadastral",
    "built_area_m2": "number",
    "price": "number",
    "deposit": "number",
}


@dataclass(frozen=True)
class CheckedField:
    value: Decimal | str | None
    evidence: str | None
    status: Literal["verificado", "rechazado", "ausente"]
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        value = str(self.value) if self.value is not None else None
        return {"value": value, "evidence": self.evidence, "status": self.status,
                "reason": self.reason}


LISTING_KINDS: dict[str, FieldKind] = {
    "price": "number",
    "built_area_m2": "number",
    "usable_area_m2": "number",
    "rooms": "number",
    "bathrooms": "number",
    "floor": "text",
    "condition": "text",
    "address": "text",
    "municipality": "text",
    "cadastral_ref": "cadastral",
    "year_built": "number",
    "community_fees": "number",
}


@dataclass(frozen=True)
class CheckedLot:
    property_type: PropertyType | None  # None si su evidencia no está en el documento
    fields: dict[str, CheckedField]

    def value(self, name: str) -> Decimal | str | None:
        checked = self.fields[name]
        return checked.value if checked.status == "verificado" else None

    def as_dict(self) -> dict[str, Any]:
        return {"property_type": self.property_type,
                **{name: f.as_dict() for name, f in self.fields.items()}}


@dataclass(frozen=True)
class CheckedDocument:
    is_correction: bool
    corrected_reference: CheckedField
    lots: list[CheckedLot]

    @property
    def rejected(self) -> int:
        return sum(1 for lot in self.lots for f in lot.fields.values() if f.status == "rechazado")


@dataclass(frozen=True)
class CheckedListing:
    operation: Operation | None  # None si su evidencia no está en el documento
    property_type: PropertyType | None
    fields: dict[str, CheckedField]

    def value(self, name: str) -> Decimal | str | None:
        checked = self.fields[name]
        return checked.value if checked.status == "verificado" else None

    @property
    def rejected(self) -> int:
        return sum(1 for f in self.fields.values() if f.status == "rechazado")

    def as_dict(self) -> dict[str, Any]:
        return {"operation": self.operation, "property_type": self.property_type,
                "fields": {name: f.as_dict() for name, f in self.fields.items()}}


def extract_listing(llm: LLMClient, document: str) -> CheckedListing:
    """Extrae los datos de un anuncio con el LLM y deja solo lo que la evidencia respalda."""
    raw = llm.structured(instructions=LISTING_INSTRUCTIONS, document=document,
                         output=ListingExtraction)
    return check_listing(document, raw)


def check_listing(document: str, raw: ListingExtraction) -> CheckedListing:
    source = _normalize(document)
    whole = (0, len(source))
    fields = {name: check_field(source, getattr(raw, name), kind, whole)
              for name, kind in LISTING_KINDS.items()}

    def quoted(evidence: str | None) -> bool:
        return bool(evidence) and _within(source, _normalize(evidence or ""), whole)

    return CheckedListing(
        operation=raw.operation if quoted(raw.operation_evidence) else None,
        property_type=raw.property_type if quoted(raw.property_type_evidence) else None,
        fields=fields,
    )


def extract(llm: LLMClient, document: str) -> CheckedDocument:
    """Extrae los lotes con el LLM y deja solo lo que la evidencia respalda."""
    raw = llm.structured(instructions=INSTRUCTIONS, document=document, output=DocumentExtraction)
    return check_document(document, raw)


def check_document(document: str, raw: DocumentExtraction) -> CheckedDocument:
    source = _normalize(document)
    lots = []
    for lot, span in zip(raw.lots, lot_spans(source, raw.lots), strict=True):
        if span is None:
            fields = {name: _without_span(getattr(lot, name)) for name in FIELD_KINDS}
            lots.append(CheckedLot(None, fields))
            continue
        fields = {name: check_field(source, getattr(lot, name), kind, span)
                  for name, kind in FIELD_KINDS.items()}
        type_ok = bool(lot.property_type_evidence) and _within(
            source, _normalize(lot.property_type_evidence or ""), span)
        lots.append(CheckedLot(lot.property_type if type_ok else None, fields))
    return CheckedDocument(
        is_correction=raw.is_correction,
        corrected_reference=check_field(source, raw.corrected_reference, "text"),
        lots=lots,
    )


def lot_spans(source: str, lots: list[LotExtraction]) -> list[Span | None]:
    """Tramo del documento (normalizado) de cada lote, o None si no se puede saber.

    Con un solo lote, todo el documento. Con varios, cada lote empieza donde está la cita de su
    etiqueta y acaba donde empieza el siguiente; el último llega hasta el final, incluidas las
    condiciones comunes. Un lote sin etiqueta verificada, o con la misma posición que otro, no
    tiene tramo.
    """
    whole = (0, len(source))
    if len(lots) == 1:
        return [whole]
    anchors: list[int | None] = []
    for lot in lots:
        label = check_field(source, lot.label, "text", whole)
        position = source.find(_normalize(lot.label.evidence or ""))
        anchors.append(position if label.status == "verificado" and position >= 0 else None)
    taken = Counter(a for a in anchors if a is not None)
    starts = sorted(taken)
    spans: list[Span | None] = []
    for anchor in anchors:
        if anchor is None or taken[anchor] > 1:
            spans.append(None)
            continue
        spans.append((anchor, next((s for s in starts if s > anchor), len(source))))
    return spans


def check_field(
    source: str, quoted: Quoted, kind: FieldKind, span: Span | None = None
) -> CheckedField:
    """Comprueba un campo contra el documento (`source`, normalizado o no).

    `span` limita dónde puede estar la cita (posiciones en el documento normalizado).
    """
    source = _normalize(source)
    if quoted.value is None or not quoted.value.strip():
        return CheckedField(None, None, "ausente")
    if not quoted.evidence:
        return CheckedField(None, None, "rechazado", "sin cita")
    evidence = _normalize(quoted.evidence)
    if evidence not in source:
        return CheckedField(None, quoted.evidence, "rechazado", "la cita no está en el documento")
    if span is not None and not _within(source, evidence, span):
        return CheckedField(None, quoted.evidence, "rechazado",
                            "la cita no está en el tramo de su lote")
    if kind == "number":
        value = _plain_number(quoted.value) or _from_quote(quoted.value, evidence)
        if value is None:
            return CheckedField(None, quoted.evidence, "rechazado", "valor no numérico")
        if value not in _numbers(evidence):
            return CheckedField(None, quoted.evidence, "rechazado",
                                "el número no aparece en la cita")
        return CheckedField(value, quoted.evidence, "verificado")
    if kind == "cadastral":
        ref = re.sub(r"\s", "", quoted.value).upper()
        if not CADASTRAL_REF.match(ref) or ref not in re.sub(r"\s", "", evidence).upper():
            return CheckedField(None, quoted.evidence, "rechazado",
                                "la referencia catastral no está en la cita o no es válida")
        return CheckedField(ref, quoted.evidence, "verificado")
    value_text = _normalize(quoted.value)
    if not re.search(rf"(?<!\w){re.escape(_fold(value_text))}(?!\w)", _fold(evidence)):
        return CheckedField(None, quoted.evidence, "rechazado", "el texto no está en la cita")
    return CheckedField(value_text, quoted.evidence, "verificado")


def _without_span(quoted: Quoted) -> CheckedField:
    if quoted.value is None or not quoted.value.strip():
        return CheckedField(None, None, "ausente")
    return CheckedField(None, quoted.evidence, "rechazado", NO_SPAN)


def _within(source: str, evidence: str, span: Span) -> bool:
    """La cita aparece entera dentro del tramo (alguna de sus apariciones)."""
    start, end = span
    return bool(evidence) and source.find(evidence, start, end) >= 0


def _normalize(text: str) -> str:
    """Espacios simples y comillas y guiones unificados, para comparar citas."""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(str.maketrans({" ": " ", "–": "-", "—": "-",
                                         "−": "-", "“": '"', "”": '"',
                                         "«": '"', "»": '"', "’": "'"}))
    return " ".join(text.split())


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _numbers(text: str) -> set[Decimal]:
    """Números escritos a la española en un texto: 1.290.109,45 → 1290109.45."""
    found = set()
    for token in NUMBER_IN_TEXT.findall(text):
        try:
            found.add(Decimal(token.replace(".", "").replace(",", ".")))
        except InvalidOperation:
            continue
    return found


def _from_quote(value: str, evidence: str) -> Decimal | None:
    """El número cuando el modelo no lo da limpio (F6.9): con qwen3 llegaban «235.000 €» o la
    palabra «value» con la cifra solo en la cita. Vale el único número del valor escrito a la
    española o, si el valor es solo el nombre del campo, el único número de la cita. Un valor en
    palabras («doce mil») sigue sin valer."""
    if any(c.isdigit() for c in value):
        found = _numbers(value)
    elif value.strip().lower() in PLACEHOLDERS:
        found = _numbers(evidence)
    else:
        return None
    return next(iter(found)) if len(found) == 1 else None


def _plain_number(value: str) -> Decimal | None:
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return None
