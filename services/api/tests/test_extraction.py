"""Extracción con evidencia comprobada (ADR-0013), con el anuncio real BOE-B-2026-35273 (dos
parcelas de la TGSS en Alcalá de Henares) y un LLM falso: el LLM solo propone; los valores que
quedan son los que están escritos en la fuente."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

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
from housefinder.agent.llm import (
    FakeLLMClient,
    LLMOutputError,
    OpenAICompatibleLLMClient,
    llm_from_env,
)
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


# --- Cliente del servidor propio contra un transporte simulado (sin red) ----------------------


def server(reply: dict | None = None, status: int = 200):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=reply or {})

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def completion(content: str, finish_reason: str = "stop") -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content},
                         "finish_reason": finish_reason}]}


def test_servidor_propio_pide_json_schema_con_el_documento_como_dato():
    http, seen = server(completion(EXTRACTION.model_dump_json()))
    client = OpenAICompatibleLLMClient("http://llm.test/v1/", "qwen3:8b", api_key="k",
                                       reasoning_effort="none", client=http)
    assert client.structured(instructions="x", document="doc",
                             output=DocumentExtraction) == EXTRACTION
    request = seen[0]
    body = json.loads(request.content)
    assert str(request.url) == "http://llm.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer k"
    assert body["model"] == "qwen3:8b" and body["temperature"] == 0
    assert body["reasoning_effort"] == "none"
    assert body["messages"][0] == {"role": "system", "content": "x"}
    assert "<documento>\ndoc\n</documento>" in body["messages"][1]["content"]
    schema = body["response_format"]["json_schema"]
    assert schema["name"] == "DocumentExtraction"
    assert schema["schema"] == DocumentExtraction.model_json_schema()


@pytest.mark.parametrize("reply, status", [
    (completion("{}", finish_reason="length"), 200),   # cortada por longitud
    (completion('{"lots": "no"}'), 200),               # no valida con el esquema
    (completion("no es json"), 200),
    ({"error": "modelo no cargado"}, 500),
    ({"choices": []}, 200),
])
def test_servidor_propio_respuestas_malas(reply, status):
    http, _ = server(reply, status)
    with pytest.raises(LLMOutputError):
        OpenAICompatibleLLMClient("http://llm.test/v1", "m", client=http).structured(
            instructions="x", document="d", output=DocumentExtraction)


def test_configuracion_sin_valores_por_defecto(monkeypatch):
    for name in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL_ID", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        llm_from_env()
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        llm_from_env()
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_MODEL_ID", "qwen3:8b")
    client = llm_from_env()
    assert isinstance(client, OpenAICompatibleLLMClient) and client.model == "qwen3:8b"


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
    failing = FakeLLMClient(lambda *a: (_ for _ in ()).throw(LLMOutputError("prueba")))
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
