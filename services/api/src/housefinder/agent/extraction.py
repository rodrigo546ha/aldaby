"""Extracción de inmuebles de un texto libre, con evidencia comprobada (ADR-0013).

El LLM devuelve cada campo con una cita literal del documento. Después, sin LLM:
1. la cita tiene que estar en el documento (espacios normalizados);
2. si hay varios lotes, la cita tiene que estar en el tramo de su lote: desde su etiqueta («Lote 2»)
   hasta la etiqueta del lote siguiente o el siguiente encabezado de lote del documento (ADR-0014).
   Si la etiqueta no vale, el tramo es el del encabezado en el que caen todas sus citas de
   ubicación (ADR-0033). Si el documento tiene encabezados «Lote…», las fincas de dentro no cierran
   el tramo; y un anuncio largo se extrae por partes con lotes enteros (ADR-0034);
3. el valor tiene que salir de la cita: un importe o una superficie es uno de los números de la
   cita; una referencia catastral está en la cita, sin contar espacios, puntos ni barras; cada
   parte de un texto separada por comas está en ella como palabras seguidas.
Lo que no pasa se descarta con su motivo. Ninguna cifra que quede es inventada: está en la fuente,
en la parte que habla de ese lote.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from itertools import accumulate
from typing import Any, Literal

from pydantic import BaseModel, Field

from housefinder.agent.llm import LLMClient

PropertyType = Literal[
    "vivienda", "local", "oficina", "garaje", "trastero", "edificio", "suelo", "rustica", "otro"
]
NUMBER_IN_TEXT = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")
# 14, 18 o 20 caracteres de la Dirección General; 8 a 20 de los catastros forales (ADR-0032).
CADASTRAL_REF = re.compile(r"^(?=(?:\D*\d){5})[0-9A-Z]{8,20}$")
REF_SEPARATORS = re.compile(r"[\s./-]")
# Encabezado de un lote al principio de un párrafo: «Lote nº 2.-», «LOTE ÚNICO», «Finca 1:»,
# «1.», «1.1», «Dos)». Solo sirve para cerrar tramos y para el tramo de reserva: no crea lotes.
HEADING = re.compile(
    r"(?:lotes?|fincas?)\b\W*(?:n(?:º|°|o|úm(?:ero)?)?\.?\s*)?(?:\d|[uú]nico\b)"
    r"|\d+(?:\.\d+)*\s*(?:[.:)–-]|$)"
    r"|(?:uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\)",
    re.IGNORECASE)
# Encabezado de un lote propiamente dicho («Lote nº 2.-», «LOTE ÚNICO»), con su número. Si el
# documento los tiene, los demás encabezados («1.1», «Finca 1:») son fincas de un lote: no cierran
# su tramo.
LOT_HEADING = re.compile(r"lotes?\b\W*(?:n(?:º|°|o|úm(?:ero)?)?\.?\s*)?(\d+|[uú]nico\b)",
                         re.IGNORECASE)
# Anuncios largos por partes (ADR-0034): lo que cabe en la ventana del modelo local (16.384
# tokens) con las instrucciones, el esquema y la respuesta, que crece con cada lote.
QUOTED_IN = re.compile(r"'([^']+)'|\"([^\"]+)\"")  # sobre el texto normalizado
PART_CHARS = 12_000
PART_LOTS = 6
PART_LIMIT = 20_000  # una parte nunca pasa de aquí (como agent/documents.py)
LOCATION_FIELDS = ("address", "cadastral_ref", "municipality")
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
    label: Quoted = Field(description="Encabezado del lote copiado tal como aparece al principio "
                                      "de su párrafo (Lote nº 1.-, LOTE ÚNICO, Dos), 1.)")
    property_type: PropertyType
    property_type_evidence: str | None = Field(description="Cita literal que indica el tipo")
    address: Quoted = Field(description="Calle y número, paraje, o polígono y parcela del "
                                        "inmueble, copiados del documento (no la dirección de "
                                        "una oficina o un registro)")
    municipality: Quoted
    province: Quoted
    cadastral_ref: Quoted = Field(description="Referencia catastral tal como aparece (puede "
                                              "llevar espacios o barras)")
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
  nunca una frase tuya sobre el documento («El texto menciona…»);
- si el documento no da el dato, deja value y evidence a null; no lo deduzcas ni lo calcules;
- en `label`, copia el encabezado del lote tal como empieza su párrafo («Lote nº 2.-», «Dos)»,
  «1.»), el mismo texto en value y en evidence;
- la dirección es la del inmueble, nunca la de la oficina, el registro o el lugar de la subasta;
  copia la calle y el número (o el paraje, o el polígono y la parcela) como están escritos, y
  deja el municipio y la provincia para sus campos;
- un lote que agrupa varias fincas es un solo elemento, con la ubicación de su primera finca;
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
    # Lo que propuso el modelo, sin comprobar: con ello se puede volver a comprobar sin el LLM
    # cuando cambian las reglas de la comprobación (ADR-0033).
    proposed: dict[str, Any] = field(default_factory=dict)

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
    """Extrae los lotes con el LLM y deja solo lo que la evidencia respalda. Un anuncio largo va
    por partes, y un lote que el modelo se salta se le pide otra vez, solo (ADR-0034)."""
    def ask(part: str) -> DocumentExtraction:
        return llm.structured(instructions=INSTRUCTIONS, document=part, output=DocumentExtraction)

    raws = [ask(part) for part in document_parts(document)]
    retries = {i: ask(lot_part(document, i)) for i in missing_lots(document, raws)}
    return check_parts(document, raws, retries)


def document_parts(document: str, max_chars: int = PART_CHARS,
                   max_lots: int = PART_LOTS) -> list[str]:
    """El documento en partes que caben en la ventana del modelo: cada una con el preámbulo (lo
    que va antes del primer lote) y lotes enteros, como mucho `max_lots`. Un lote que no cabe va
    solo y, si pasa de `PART_LIMIT`, sin el final: el del último lote son las condiciones comunes
    del pliego. Si el documento cabe, o no tiene encabezados de lote, va entero."""
    return [part for part, _ in _parts(document, max_chars, max_lots)]


def _parts(document: str, max_chars: int, max_lots: int) -> list[tuple[str, list[int]]]:
    """Cada parte con los números de orden de sus lotes en el documento."""
    preamble, blocks = _blocks(document)
    if len(document) <= max_chars or not blocks:
        return [(document, list(range(len(blocks))))]
    groups: list[list[int]] = [[]]
    for i, block in enumerate(blocks):
        size = len(preamble) + sum(len(blocks[j]) + 1 for j in groups[-1]) + len(block)
        if groups[-1] and (len(groups[-1]) == max_lots or size > max_chars):
            groups.append([])
        groups[-1].append(i)
    return [(_cut("\n".join([preamble, *(blocks[i] for i in group)]), PART_LIMIT), group)
            for group in groups]


def lot_part(document: str, index: int) -> str:
    """El preámbulo y el lote `index` solo: lo que se le vuelve a pedir al modelo."""
    preamble, blocks = _blocks(document)
    return _cut("\n".join([preamble, blocks[index]]), PART_LIMIT)


def _blocks(document: str) -> tuple[str, list[str]]:
    """El preámbulo y el texto de cada lote; ningún lote si el documento no tiene dos."""
    lines = document.split("\n")
    starts = _lot_lines(lines)
    if len(starts) < 2:
        return document, []
    ends = [*starts[1:], len(lines)]
    return "\n".join(lines[:starts[0]]), ["\n".join(lines[a:b])
                                           for a, b in zip(starts, ends, strict=True)]


def _lot_lines(lines: list[str]) -> list[int]:
    """Las líneas que empiezan un lote. La que repite el número del lote abierto no empieza otro:
    es su fila de la tabla de precios («Lote 1 2ª subasta…», BOE-B-2026-31848)."""
    starts: list[int] = []
    current: str | None = None
    for i, line in enumerate(lines):
        found = LOT_HEADING.match(_normalize(line))
        if found is None:
            continue
        if _fold(found.group(1)) != current:
            starts.append(i)
        current = _fold(found.group(1))
    return starts


def _cut(text: str, limit: int) -> str:
    """El texto hasta el último salto de línea antes de `limit`."""
    if len(text) <= limit:
        return text
    end = text.rfind("\n", 0, limit)
    return text[:end if end > 0 else limit]


def missing_lots(document: str, raws: list[DocumentExtraction],
                 max_chars: int = PART_CHARS, max_lots: int = PART_LOTS) -> list[int]:
    """Los lotes del documento (por su número de orden) en los que el modelo no puso ningún
    elemento: ninguna etiqueta suya empieza un párrafo del tramo del lote."""
    parts = _parts(document, max_chars, max_lots)
    covered: set[int] = set()
    for (part, group), raw in zip(parts, raws, strict=True):
        source = _normalize(part)
        _, lot_starts = _paragraph_starts(part)
        for lot in _unwrapped(source, raw).lots:
            anchor = _lot_anchor(source, part, lot)
            if anchor is not None and lot_starts.index(anchor[0]) < len(group):
                covered.add(group[lot_starts.index(anchor[0])])
    return [i for i in sorted({i for _, group in parts for i in group}) if i not in covered]


def check_parts(document: str, raws: list[DocumentExtraction],
                retries: dict[int, DocumentExtraction] | None = None,
                max_chars: int = PART_CHARS, max_lots: int = PART_LOTS) -> CheckedDocument:
    """Cada parte se comprueba contra su texto; los lotes se juntan en orden. Los lotes pedidos
    otra vez van al final, para que los demás no cambien de número; de cada respuesta solo vale
    lo que es de su lote."""
    parts = document_parts(document, max_chars, max_lots)
    retries = retries or {}
    checked = [check_document(part, raw) for part, raw in zip(parts, raws, strict=True)]
    checked += [check_document(lot_part(document, i), _in_lot(lot_part(document, i), raw))
                for i, raw in retries.items()]
    if len(checked) == 1:
        return checked[0]
    return CheckedDocument(
        is_correction=checked[0].is_correction,
        corrected_reference=checked[0].corrected_reference,
        lots=[lot for c in checked for lot in c.lots],
        proposed={"parts": [raw.model_dump() for raw in raws],
                  "retries": [{"lot": i, "raw": raw.model_dump()} for i, raw in retries.items()],
                  "part_chars": max_chars, "part_lots": max_lots},
    )


def _in_lot(part: str, raw: DocumentExtraction) -> DocumentExtraction:
    """De lo que el modelo devuelve para un lote pedido otra vez, solo los elementos de ese lote."""
    source = _normalize(part)
    lots = [lot for lot in _unwrapped(source, raw).lots
            if _lot_anchor(source, part, lot) is not None]
    return raw.model_copy(update={"lots": lots})


class ProposalMismatch(ValueError):
    """Lo propuesto se partió con otras reglas de corte: hay que volver a extraerlo con el LLM."""


def recheck_document(document: str, proposed: dict[str, Any]) -> CheckedDocument:
    """Vuelve a comprobar sin el LLM lo que propuso el modelo (ADR-0033), partido como entonces."""
    if "parts" not in proposed:
        return check_document(document, DocumentExtraction.model_validate(proposed))
    parts = document_parts(document, proposed["part_chars"], proposed["part_lots"])
    if len(parts) != len(proposed["parts"]):
        raise ProposalMismatch(f"{len(proposed['parts'])} partes propuestas y {len(parts)} ahora")
    retries = {r["lot"]: DocumentExtraction.model_validate(r["raw"])
               for r in proposed.get("retries", [])}
    return check_parts(document, [DocumentExtraction.model_validate(p) for p in proposed["parts"]],
                       retries, proposed["part_chars"], proposed["part_lots"])


def check_document(document: str, raw: DocumentExtraction) -> CheckedDocument:
    source = _normalize(document)
    proposed = raw.model_dump()
    raw = _fincas_joined(source, document, _unwrapped(source, raw))
    lots = []
    spans = lot_spans(source, raw.lots, heading_starts(document))
    for lot, span in zip(raw.lots, spans, strict=True):
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
        proposed=proposed,
    )


def lot_spans(source: str, lots: list[LotExtraction],
              headings: list[int] | None = None) -> list[Span | None]:
    """Tramo del documento (normalizado) de cada lote, o None si no se puede saber.

    Con un solo lote, todo el documento. Con varios, cada lote empieza donde está la cita de su
    etiqueta y acaba donde empieza el siguiente lote o el siguiente encabezado de lote del
    documento (`headings`); el último llega hasta el final, incluidas las condiciones comunes.
    Si la etiqueta no vale (el modelo no la copia literal), el tramo es el del encabezado en el que
    caen todas sus citas de ubicación. Dos lotes con el mismo comienzo no tienen tramo.
    """
    whole = (0, len(source))
    if len(lots) == 1:
        return [whole]
    marks = sorted(set(headings or []))
    anchors: list[int | None] = []
    for lot in lots:
        label = check_field(source, lot.label, "text", whole)
        position = source.find(_normalize(lot.label.evidence or ""))
        if label.status == "verificado" and position >= 0:
            anchors.append(position)
        else:
            anchors.append(_heading_of(source, lot, marks))
    taken = Counter(a for a in anchors if a is not None)
    starts = sorted(set(taken) | set(marks))
    spans: list[Span | None] = []
    for anchor in anchors:
        if anchor is None or taken[anchor] > 1:
            spans.append(None)
            continue
        spans.append((anchor, next((s for s in starts if s > anchor), len(source))))
    return spans


def heading_starts(document: str) -> list[int]:
    """Posiciones, en el documento normalizado, de los párrafos que empiezan por un encabezado de
    lote. Los párrafos son las líneas del documento. Si hay encabezados «Lote…», solo cuentan
    ellos: los demás son las fincas de cada lote (ADR-0034)."""
    starts, lot_starts = _paragraph_starts(document)
    return lot_starts or starts


def _paragraph_starts(document: str) -> tuple[list[int], list[int]]:
    """Las posiciones de todos los encabezados y las de los que empiezan un lote."""
    texts = [text for text in (_normalize(line) for line in document.split("\n")) if text]
    positions = list(accumulate((len(text) + 1 for text in texts[:-1]), initial=0))
    starts = [p for p, text in zip(positions, texts, strict=True) if HEADING.match(text)]
    return starts, [positions[i] for i in _lot_lines(texts)]


def _lot_anchor(source: str, document: str, lot: LotExtraction) -> tuple[int, int] | None:
    """El comienzo del lote en cuyo tramo empieza un párrafo con la etiqueta de `lot`, y el de
    ese párrafo; None si la etiqueta no empieza ningún párrafo de un lote."""
    starts, lot_starts = _paragraph_starts(document)
    label = _normalize(lot.label.evidence or "")
    at = next((s for s in starts if label and source.startswith(label, s)), None)
    key = None if at is None else max((s for s in lot_starts if s <= at), default=None)
    return None if key is None or at is None else (key, at)


def _fincas_joined(source: str, document: str, raw: DocumentExtraction) -> DocumentExtraction:
    """Las fincas que el modelo saca como lotes aparte («9.1», «9.2»), juntas en el lote en cuyo
    tramo están (ADR-0034). Un lote es lo que se subasta junto. Se juntan los elementos cuya
    etiqueta empieza un párrafo del mismo tramo «Lote…», si los que son el propio lote empiezan
    todos el mismo párrafo."""
    _, lot_starts = _paragraph_starts(document)
    if not lot_starts:
        return raw
    groups: dict[int, list[LotExtraction]] = {}
    at: dict[int, int] = {}  # dónde empieza el párrafo de la etiqueta de cada elemento
    order: list[LotExtraction | int] = []
    for lot in raw.lots:
        anchor = _lot_anchor(source, document, lot)
        if anchor is None:
            order.append(lot)
            continue
        at[id(lot)] = anchor[1]
        if anchor[0] not in groups:
            order.append(anchor[0])
        groups.setdefault(anchor[0], []).append(lot)
    lots: list[LotExtraction] = []
    for item in order:
        if isinstance(item, LotExtraction):
            lots.append(item)
            continue
        group = groups[item]
        heads = [lot for lot in group if LOT_HEADING.match(_normalize(lot.label.evidence or ""))]
        # Varias etiquetas del mismo encabezado son el mismo lote (una por parcela, en 31848).
        if len(group) == 1 or len({at[id(head)] for head in heads}) > 1:
            lots.extend(group)
            continue
        span = (item, next((s for s in lot_starts if s > item), len(source)))
        fincas = [lot for lot in group if all(lot is not head for head in heads)]
        lots.append(_joined(source, span, [*heads, *fincas]))
    return raw.model_copy(update={"lots": lots})


def _joined(source: str, span: Span, group: list[LotExtraction]) -> LotExtraction:
    """El lote (el primero del grupo) con la ubicación de la primera finca que tiene referencia
    catastral, o si no la tiene ninguna, dirección. El municipio, el precio y la garantía son los
    del primero que los da. Todo se comprueba después en el tramo del lote, como siempre."""
    def ok(lot: LotExtraction, name: str) -> bool:
        return check_field(source, getattr(lot, name), FIELD_KINDS[name], span).status \
            == "verificado"

    def first(name: str, among: list[LotExtraction]) -> Quoted:
        return next((getattr(lot, name) for lot in among if ok(lot, name)), getattr(base, name))

    base = group[0]
    place = next((lot for lot in group if ok(lot, "cadastral_ref")), None) or \
        next((lot for lot in group if ok(lot, "address")), base)
    typed = next((lot for lot in group if lot.property_type_evidence and _within(
        source, _normalize(lot.property_type_evidence), span)), base)
    return base.model_copy(update={
        "address": first("address", [place, *group]),
        "cadastral_ref": place.cadastral_ref,
        "municipality": first("municipality", [place, *group]),
        "province": first("province", [place, *group]),
        "price": first("price", group),
        "deposit": first("deposit", group),
        "property_type": typed.property_type,
        "property_type_evidence": typed.property_type_evidence,
    })


def _heading_of(source: str, lot: LotExtraction, marks: list[int]) -> int | None:
    """El encabezado cuyo tramo contiene todas las citas de ubicación del lote que están en el
    documento; None si no hay ninguna o caen en tramos distintos."""
    segments = [(start, next((m for m in marks if m > start), len(source))) for start in marks]
    found: set[int] | None = None
    for name in LOCATION_FIELDS:
        quoted: Quoted = getattr(lot, name)
        evidence = _normalize(quoted.evidence or "")
        if not (quoted.value or "").strip() or not evidence or evidence not in source:
            continue
        hits = {start for start, end in segments if _within(source, evidence, (start, end))}
        found = hits if found is None else found & hits
    return next(iter(found)) if found is not None and len(found) == 1 else None


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
        ref = REF_SEPARATORS.sub("", quoted.value).upper()
        if not CADASTRAL_REF.match(ref) or ref not in REF_SEPARATORS.sub("", evidence).upper():
            return CheckedField(None, quoted.evidence, "rechazado",
                                "la referencia catastral no está en la cita o no es válida")
        return CheckedField(ref, quoted.evidence, "verificado")
    value_text = _normalize(quoted.value)
    if not _text_in(value_text, evidence):
        return CheckedField(None, quoted.evidence, "rechazado", "el texto no está en la cita")
    return CheckedField(value_text, quoted.evidence, "verificado")


def _text_in(value: str, evidence: str) -> bool:
    """Cada parte del valor separada por comas está en la cita como palabras seguidas, sin
    contar mayúsculas, tildes ni signos: «Plaza Cuartel 6, Cacín» sale de «en CACÍN (Granada),
    Plaza Cuartel, 6». Ninguna palabra del valor queda fuera de la cita."""
    words = _words(evidence)
    parts = [part for part in (_words(p) for p in value.split(",")) if part]
    return bool(parts) and all(
        any(words[i:i + len(part)] == part for i in range(len(words) - len(part) + 1))
        for part in parts)


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", _fold(text))


def _unwrapped(source: str, raw: DocumentExtraction) -> DocumentExtraction:
    """Las citas que el modelo envuelve en una frase suya («The text states 'municipio de
    UTIEL'»), reducidas al fragmento entre comillas que sí está en el documento (ADR-0034)."""
    def quote(evidence: str | None) -> str | None:
        if not evidence or _normalize(evidence) in source:
            return evidence
        inner = [a or b for a, b in QUOTED_IN.findall(_normalize(evidence))]
        found = [q for q in inner if q.strip() and q in source]
        return max(found, key=len) if found else evidence

    def fix(quoted: Quoted) -> Quoted:
        return Quoted(value=quoted.value, evidence=quote(quoted.evidence))

    lots = [lot.model_copy(update={
        **{name: fix(getattr(lot, name)) for name in ("label", *FIELD_KINDS)},
        "cadastral_ref": _first_ref(source, fix(lot.cadastral_ref)),
        "property_type_evidence": quote(lot.property_type_evidence)}) for lot in raw.lots]
    return raw.model_copy(update={"lots": lots,
                                  "corrected_reference": fix(raw.corrected_reference)})


def _first_ref(source: str, quoted: Quoted) -> Quoted:
    """Las referencias de las fincas de un lote, juntas en un valor («A, B, C») y en una cita de
    varias líneas que no es seguida en el documento (BOE-B-2026-31747): la primera, con la línea
    de la cita que la tiene, si esa línea está en el documento."""
    if not quoted.value or not quoted.evidence or _normalize(quoted.evidence) in source:
        return quoted
    first = re.split(r"[,;]", quoted.value)[0].strip()
    ref = REF_SEPARATORS.sub("", first).upper()
    for line in quoted.evidence.split("\n"):
        text = _normalize(line)
        if text and text in source and ref in REF_SEPARATORS.sub("", text).upper():
            return Quoted(value=first, evidence=line.strip())
    return quoted


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
