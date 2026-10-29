"""Extracción con evidencia comprobada (ADR-0013), con el anuncio real BOE-B-2026-35273 (dos
parcelas de la TGSS en Alcalá de Henares) y un LLM falso: el LLM solo propone; los valores que
quedan son los que están escritos en la fuente."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from housefinder.agent.extraction import (
    DocumentExtraction,
    LotExtraction,
    Quoted,
    check_document,
    check_field,
    extract,
)
from housefinder.agent.llm import BedrockLLMClient, FakeLLMClient, LLMOutputError, LLMRefusal
from housefinder.offers.channels.boe_v import parse_announcement

FIXTURES = Path(__file__).parent / "fixtures" / "boe"
ANNOUNCEMENT = (FIXTURES / "anuncio-BOE-B-2026-35273.xml").read_bytes()
TEXT = "\n".join(parse_announcement(ANNOUNCEMENT)["texto"])
NONE = Quoted(value=None, evidence=None)


def q(value, evidence):
    return Quoted(value=value, evidence=evidence)


def lot(**fields) -> LotExtraction:
    base = dict(label=NONE, property_type="suelo",
                property_type_evidence="porción de terreno", address=NONE, municipality=NONE,
                province=NONE, cadastral_ref=NONE, built_area_m2=NONE, floor=NONE, price=NONE,
                deposit=NONE)
    return LotExtraction(**{**base, **fields})


LOT_1 = lot(
    label=q("Lote 1", "Lote 1: Urbana"),
    address=q("Carretera M-119 (Camarma-Valdeavero), n°21",
              "situado en la Carretera M-119 (Camarma-Valdeavero), n°21, de Alcalá de Henares"),
    municipality=q("Alcalá de Henares", "n°21, de Alcalá de Henares (Madrid)"),
    province=q("Madrid", "Alcalá de Henares (Madrid)"),
    cadastral_ref=q("7744401VK6874N0001FJ",
                    "Su referencia y superficie catastral son las siguientes:7744401VK6874N0001FJ "
                    "y 163.883 m2."),
    built_area_m2=q("163883", "7744401VK6874N0001FJ y 163.883 m2."),
    price=q("25802189", "El tipo de licitación es 25.802.189 €"),
    deposit=q("1290109.45", "tipo de licitación: 1.290.109,45 €"),
)
LOT_2 = lot(
    label=q("Lote 2", "Lote 2: Urbana"),
    cadastral_ref=q("7744403VK6873N0001OM", "las siguientes:7744403VK6873N0001OM y 53.700 m2."),
    price=q("6778639", "El tipo de licitación es 6.778.639 €"),
    # Errores del LLM que la comprobación tiene que pillar:
    deposit=q("340000", "Garantía a constituir del 5 por ciento"),  # número inventado
    built_area_m2=q("53700", "superficie de 53.700 metros cuadrados"),  # cita que no existe
)
EXTRACTION = DocumentExtraction(is_correction=False, corrected_reference=NONE,
                                lots=[LOT_1, LOT_2])


def test_lo_que_respalda_la_cita_se_queda():
    checked = check_document(TEXT, EXTRACTION)
    first = checked.lots[0]
    assert first.property_type == "suelo"
    assert first.value("price") == Decimal("25802189")
    assert first.value("deposit") == Decimal("1290109.45")
    assert first.value("cadastral_ref") == "7744401VK6874N0001FJ"
    assert first.value("built_area_m2") == Decimal("163883")
    assert first.value("municipality") == "Alcalá de Henares"


def test_lo_inventado_se_descarta_con_su_motivo():
    second = check_document(TEXT, EXTRACTION).lots[1]
    assert second.value("price") == Decimal("6778639")
    assert second.value("deposit") is None
    assert second.fields["deposit"].reason == "el número no aparece en la cita"
    assert second.value("built_area_m2") is None
    assert second.fields["built_area_m2"].reason == "la cita no está en el documento"
    assert check_document(TEXT, EXTRACTION).rejected == 2


@pytest.mark.parametrize(
    ("quoted", "kind", "status"),
    [
        (q("1290109.45", "1.290.109,45 €"), "number", "verificado"),
        (q("1290109", "1.290.109,45 €"), "number", "rechazado"),  # sin los céntimos, no
        (q("doce mil", "12.000 €"), "number", "rechazado"),
        (q("7744401VK6874N0001FJ", "es 7744401VK6874N0001FJ"), "cadastral", "verificado"),
        (q("7744401VK6874N", "es 7744401VK6874N0001FJ"), "cadastral", "verificado"),  # parcela
        (q("XXXX", "es XXXX"), "cadastral", "rechazado"),
        (q("alcala de henares", "de Alcalá de Henares (Madrid)"), "text", "verificado"),
        (q("Getafe", "de Alcalá de Henares (Madrid)"), "text", "rechazado"),
        (q("Madrid", None), "text", "rechazado"),
        (NONE, "number", "ausente"),
    ],
)
def test_comprobacion_de_campos(quoted, kind, status):
    source = "es 7744401VK6874N0001FJ de Alcalá de Henares (Madrid) por 1.290.109,45 € y 12.000 €"
    assert check_field(source, quoted, kind).status == status


def test_las_citas_toleran_espacios_y_guiones_distintos():
    source = "Carretera M–119, n°21"
    assert check_field(source, q("Carretera M-119", "Carretera M-119, n°21"), "text").status == (
        "verificado")


def test_el_documento_va_como_dato():
    llm = FakeLLMClient(lambda instructions, document, output: EXTRACTION)
    extract(llm, TEXT)
    assert llm.calls[0] == TEXT  # el cliente falso recibe el documento tal cual


# --- Cliente de Bedrock contra un doble del SDK (sin red) --------------------------------------


class StubSDK:
    def __init__(self, response):
        self.kwargs = None
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))
        self.response = response

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_bedrock_pide_salida_estructurada_y_cachea_las_instrucciones():
    stub = StubSDK(SimpleNamespace(stop_reason="end_turn", parsed_output=EXTRACTION))
    client = BedrockLLMClient("anthropic.claude-opus-5-5", "eu-west-1", client=stub)
    assert client.structured(instructions="x", document="doc",
                             output=DocumentExtraction) is EXTRACTION
    assert stub.kwargs["model"] == "anthropic.claude-opus-5-5"
    assert stub.kwargs["output_format"] is DocumentExtraction
    assert stub.kwargs["cache_control"] == {"type": "ephemeral"}
    assert "<documento>" in stub.kwargs["messages"][0]["content"]
    assert "temperature" not in stub.kwargs and "tool_choice" not in stub.kwargs


def test_bedrock_negativa_y_respuesta_cortada():
    refusal = SimpleNamespace(stop_reason="refusal", parsed_output=None,
                              stop_details=SimpleNamespace(category="cyber"))
    with pytest.raises(LLMRefusal, match="cyber"):
        BedrockLLMClient("m", "r", client=StubSDK(refusal)).structured(
            instructions="x", document="d", output=DocumentExtraction)
    cut = SimpleNamespace(stop_reason="max_tokens", parsed_output=None)
    with pytest.raises(LLMOutputError):
        BedrockLLMClient("m", "r", client=StubSDK(cut)).structured(
            instructions="x", document="d", output=DocumentExtraction)


# --- De punta a punta contra la base -----------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


def boe_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/sumario/20261028"):
            return httpx.Response(200, content=(FIXTURES / "sumario-20261028-5b.json").read_bytes())
        if "xml.php?id=BOE-B-2026-35273" in url:
            return httpx.Response(200, content=ANNOUNCEMENT)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.db
def test_lotes_extraidos_ubicados_y_pendientes_de_confirmar(migrated_database: str):
    from housefinder.offers.run import extract_boe_v, run_boe_v

    with psycopg.connect(migrated_database, autocommit=True) as conn:  # otros tests leen el día
        conn.execute("DELETE FROM watch_issues WHERE source = 'offers_boe_v'")
        conn.execute("UPDATE offers SET extraction_status = 'pendiente' "
                     "WHERE external_id = 'BOE-B-2026-35273'")
    run_boe_v(migrated_database, boe_client(), date(2026, 10, 28), days=1)
    failing = FakeLLMClient(lambda *a: (_ for _ in ()).throw(LLMRefusal("prueba")))
    assert extract_boe_v(migrated_database, boe_client(), failing)["failed"] >= 1

    geocoded: list[str] = []

    def geocoder(address):
        from housefinder.geo.cartociudad import Geocoded

        geocoded.append(address)
        return Geocoded(-3.36, 40.51, "portal", address, "28005", None)

    llm = FakeLLMClient(lambda *a: EXTRACTION)
    report = extract_boe_v(migrated_database, boe_client(), llm, geocoder=geocoder)
    assert report["lots"] == 2 and report["rejected_fields"] == 2
    assert geocoded == ["Carretera M-119 (Camarma-Valdeavero), n°21, Alcalá de Henares, Madrid"]
    with psycopg.connect(migrated_database) as conn:
        lots = conn.execute(
            "SELECT external_id, extraction_status, auction_min_bid, deposit_required, "
            "cadastral_ref, property_id IS NOT NULL, extracted->'deposit'->>'status' "
            "FROM offers WHERE kind = 'lote' AND external_id LIKE 'BOE-B-2026-35273#%' "
            "ORDER BY external_id").fetchall()
        parent = conn.execute("SELECT extraction_status FROM offers "
                              "WHERE external_id = 'BOE-B-2026-35273'").fetchone()
    assert lots[0] == ("BOE-B-2026-35273#1", "extraida", Decimal("25802189"),
                       Decimal("1290109.45"), "7744401VK6874N0001FJ", True, "verificado")
    # Lote 2: sin dirección no se ubica; la garantía inventada no se guarda.
    assert lots[1][3] is None and lots[1][5] is False and lots[1][6] == "rechazado"
    assert parent == ("extraida",)
    assert extract_boe_v(migrated_database, boe_client(), llm)["announcements"] == 0
