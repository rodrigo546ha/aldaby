"""Evaluación de la extracción contra el juego etiquetado (F6.9, ADR-0027)."""

from decimal import Decimal
from typing import Any

from housefinder.agent.extraction import (
    FIELD_KINDS,
    LISTING_KINDS,
    CheckedDocument,
    CheckedField,
    CheckedListing,
    CheckedLot,
)
from housefinder.evaluations.listings import evaluate, load_cases


def checked(value: Any) -> CheckedField:
    if isinstance(value, list):
        value = next((v for v in value if v is not None), None)
    if value is None:
        return CheckedField(None, None, "ausente")
    return CheckedField(Decimal(str(value)) if isinstance(value, (int, float)) else str(value),
                        "cita", "verificado")


def perfect_listing(expected: dict[str, Any]) -> CheckedListing:
    return CheckedListing(expected.get("operation"), expected.get("property_type"),
                          {n: checked(expected.get(n)) for n in LISTING_KINDS})


def perfect_document(lots: list[dict[str, Any]]) -> CheckedDocument:
    return CheckedDocument(False, checked(None), [
        CheckedLot(lot.get("property_type"), {n: checked(lot.get(n)) for n in FIELD_KINDS})
        for lot in lots])


def test_el_juego_se_carga_entero():
    cases = load_cases()
    assert len(cases) == 22
    assert sum(c.kind == "boe" for c in cases) == 10
    assert all(c.text.strip() for c in cases)


def test_respuestas_perfectas_aciertan_todo():
    cases = load_cases()
    by_text = {c.text: c for c in cases}
    report = evaluate(cases, lambda t: perfect_listing(by_text[t].expected),
                      lambda t: perfect_document(by_text[t].lots))
    m = report.metrics()
    assert m["correctos"] == m["con_valor"] > 100
    assert m["falta"] == m["distinto"] == m["sobra"] == m["errores"] == 0


def test_cada_error_se_clasifica():
    cases = [c for c in load_cases() if c.id in ("piso-getafe", "boe-alcaniz",
                                                  "boe-tgss-alcala")]
    by_text = {c.text: c for c in cases}

    def listing(text: str) -> CheckedListing:
        wrong = dict(by_text[text].expected, price=199000, rooms=None, cadastral_ref="X" * 14)
        return perfect_listing(wrong)

    def document(text: str) -> CheckedDocument:
        case = by_text[text]
        return perfect_document([{"property_type": "suelo"}] if not case.lots else case.lots[:1])

    report = evaluate(cases, listing, document)
    outcomes = {(r.case, r.field): r.outcome for r in report.fields}
    assert outcomes[("piso-getafe", "price")] == "distinto"
    assert outcomes[("piso-getafe", "rooms")] == "falta"
    assert outcomes[("piso-getafe", "cadastral_ref")] == "sobra"
    assert report.extra_lots == 1 and report.missing_lots == 1  # Alcañiz de más, Lote 2 de menos
    assert outcomes[("boe-tgss-alcala#2", "price")] == "falta"
