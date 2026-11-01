"""Extracción con evidencia comprobada (ADR-0013), con el anuncio real BOE-B-2026-35273 (dos
parcelas de la TGSS en Alcalá de Henares) y un LLM falso: el LLM solo propone; los valores que
quedan son los que están escritos en la fuente."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from conftest import add_section

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
from housefinder.geo.cartociudad import FIND_URL
from housefinder.geo.catastro import CPMRC_URL
from housefinder.offers.channels.boe_v import parse_announcement

FIXTURES = Path(__file__).parent / "fixtures" / "boe"
CATASTRO = Path(__file__).parent / "fixtures" / "catastro"
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
        # F6.9: qwen3 escribe el número como en el anuncio o el nombre del campo
        (q("12.000 €", "12.000 €"), "number", "verificado"),
        (q("value", "y 12.000 €"), "number", "verificado"),
        (q("value", "por 1.290.109,45 € y 12.000 €"), "number", "rechazado"),  # dos números
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


def test_un_texto_corto_tiene_que_ser_palabra_entera_de_la_cita():
    # qwen3:8b dio la planta «0» con una cita en la que el 0 solo está dentro de otros números.
    source = "en la calle Agustín de Foxá, 28-30, planta baja; 2.050 m2"
    assert check_field(source, q("0", "Foxá, 28-30, planta baja"), "text").status == "rechazado"
    assert check_field(source, q("baja", "Foxá, 28-30, planta baja"), "text").status == (
        "verificado")
    assert check_field(source, q("30, planta", "28-30, planta baja"), "text").status == (
        "verificado")


# --- Cada cita, en el tramo de su lote (ADR-0014) ----------------------------------------------
# qwen3:8b devolvió el lote 2 con la referencia catastral, el precio y la garantía del lote 1: las
# citas están en el documento, pero en el tramo del lote 1.

COPIED_LOT_2 = lot(
    label=q("Lote 2", "Lote 2: Urbana"),
    # La dirección es la misma en los dos lotes y también está escrita en el tramo del lote 2.
    address=q("Carretera M-119 (Camarma-Valdeavero), n°21",
              "situado en la Carretera M-119 (Camarma-Valdeavero), n°21, de Alcalá de Henares"),
    cadastral_ref=LOT_1.cadastral_ref,
    price=LOT_1.price,
    deposit=LOT_1.deposit,
)


def test_una_cita_de_otro_lote_se_rechaza():
    raw = DocumentExtraction(is_correction=False, corrected_reference=NONE,
                             lots=[LOT_1, COPIED_LOT_2])
    first, second = check_document(TEXT, raw).lots
    assert first.value("price") == Decimal("25802189")  # el lote 1 no cambia
    assert second.value("address") == "Carretera M-119 (Camarma-Valdeavero), n°21"
    for name in ("cadastral_ref", "price", "deposit"):
        assert second.value(name) is None
        assert second.fields[name].reason == "la cita no está en el tramo de su lote"


def test_sin_etiqueta_no_hay_tramo_y_el_lote_se_rechaza():
    unlabeled = lot(price=q("6778639", "El tipo de licitación es 6.778.639 €"))
    raw = DocumentExtraction(is_correction=False, corrected_reference=NONE,
                             lots=[LOT_1, unlabeled])
    second = check_document(TEXT, raw).lots[1]
    assert second.value("price") is None
    assert second.fields["price"].reason == "no se sabe qué tramo del documento es de este lote"
    assert second.property_type is None


def test_dos_lotes_con_la_misma_etiqueta_se_rechazan_los_dos():
    twin = lot(label=q("Lote 1", "Lote 1: Urbana"),
               price=q("25802189", "El tipo de licitación es 25.802.189 €"))
    raw = DocumentExtraction(is_correction=False, corrected_reference=NONE, lots=[LOT_1, twin])
    assert all(checked.value("price") is None for checked in check_document(TEXT, raw).lots)


def test_un_solo_lote_usa_todo_el_documento():
    single = lot(price=q("6778639", "El tipo de licitación es 6.778.639 €"))
    raw = DocumentExtraction(is_correction=False, corrected_reference=NONE, lots=[single])
    assert check_document(TEXT, raw).lots[0].value("price") == Decimal("6778639")


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


def boe_client(cartociudad: int = 404, seen: list[str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url.endswith("/sumario/20261028"):
            return httpx.Response(200, content=(FIXTURES / "sumario-20261028-5b.json").read_bytes())
        if "xml.php?id=BOE-B-2026-35273" in url:
            return httpx.Response(200, content=ANNOUNCEMENT)
        if url.startswith(FIND_URL):
            return httpx.Response(cartociudad)
        if url.startswith(CPMRC_URL):  # el Catastro no tiene la referencia
            return httpx.Response(200, content=(CATASTRO / "cpmrc-no-existe.json").read_bytes())
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def pending_again(conninfo: str) -> None:
    """Deja BOE-B-2026-35273 como único anuncio pendiente, con sus lotes sin ubicar y sin caché
    de la parcela ni de la dirección."""
    with psycopg.connect(conninfo, autocommit=True) as conn:  # otros tests leen el día
        conn.execute("DELETE FROM watch_issues WHERE source = 'offers_boe_v'")
        # Sin parcelas en la caché: el Catastro no responde aquí y se ubica por dirección.
        conn.execute("DELETE FROM geocode_cache WHERE query LIKE 'rc:%'")
        # Lotes sin ubicar y dirección sin caché: otros tests ya los ubican en la misma base.
        conn.execute("UPDATE offers SET property_id = NULL, location_source = NULL "
                     "WHERE parent_id IN (SELECT id FROM offers "
                     "WHERE external_id = 'BOE-B-2026-35273')")
        conn.execute("DELETE FROM geocode_cache WHERE query LIKE 'carretera m-119%'")
        # Ningún lote esperando otro intento: extract_offers los volvería a ubicar al empezar.
        conn.execute("UPDATE offers SET location_issue = NULL, location_retry = false "
                     "WHERE kind = 'lote'")
        # Solo este anuncio pendiente: otros tests dejan anuncios del canal en la misma base.
        conn.execute("UPDATE offers SET extraction_status = 'no_aplica' "
                     "WHERE channel = 'boe_seccion_v' AND kind = 'anuncio' "
                     "AND extraction_status = 'pendiente' AND external_id <> 'BOE-B-2026-35273'")
        conn.execute("UPDATE offers SET extraction_status = 'pendiente' "
                     "WHERE external_id = 'BOE-B-2026-35273'")


@pytest.mark.db
def test_lotes_extraidos_ubicados_y_pendientes_de_confirmar(migrated_database: str):
    from housefinder.offers.run import extract_boe_v, run_boe_v

    pending_again(migrated_database)
    run_boe_v(migrated_database, boe_client(), date(2026, 10, 28), days=1)
    failing = FakeLLMClient(lambda *a: (_ for _ in ()).throw(LLMOutputError("prueba")))
    assert extract_boe_v(migrated_database, boe_client(), failing)["failed"] >= 1

    asked: list[str] = []

    def geocoder(address):
        asked.append(address)
        return geocoded(address)

    llm = FakeLLMClient(lambda *a: EXTRACTION)
    add_section(migrated_database, "2800597001", -3.36, 40.51)
    report = extract_boe_v(migrated_database, boe_client(), llm, geocoder=geocoder)
    assert report["lots"] == 2 and report["rejected_fields"] == 2
    assert asked == ["Carretera M-119 (Camarma-Valdeavero), n°21, Alcalá de Henares, Madrid"]
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



def geocoded(address):
    """CartoCiudad de vuelta: la dirección de la Carretera M-119 dentro de la sección de prueba."""
    from housefinder.geo.cartociudad import Geocoded

    return Geocoded(-3.36, 40.51, "portal", address, "28005", None)


@pytest.mark.db
def test_un_500_de_cartociudad_no_tumba_la_extraccion_y_el_lote_se_reintenta_sin_llm(
        migrated_database: str):
    """Trabajos 10 y 15 (2026-10-30 y 31): un 500 de CartoCiudad con un lote hacía fallar
    `extract_offers` entero y cada reintento repetía la extracción con el LLM (ADR-0020)."""
    from housefinder.offers.run import extract_boe_v, run_boe_v

    pending_again(migrated_database)
    add_section(migrated_database, "2800597001", -3.36, 40.51)
    run_boe_v(migrated_database, boe_client(), date(2026, 10, 28), days=1)
    seen: list[str] = []
    llm = FakeLLMClient(lambda *a: EXTRACTION)
    report = extract_boe_v(migrated_database, boe_client(cartociudad=500, seen=seen), llm)
    assert (report["announcements"], report["lots"], report["located"]) == (1, 2, 0)
    unlocated = {u["offer"]: u for u in report["unlocated"]}
    # Lote 1: CartoCiudad falló; el Catastro no tenía la referencia. Se reintentará.
    assert unlocated["BOE-B-2026-35273#1"]["reason"].startswith(
        "CartoCiudad no responde: HTTP 500; 7744401VK6874N0001FJ: Catastro: ")
    assert unlocated["BOE-B-2026-35273#1"]["retry"] is True
    # Lote 2: solo la referencia, que el Catastro no tiene. No hay nada que reintentar.
    assert unlocated["BOE-B-2026-35273#2"]["retry"] is False
    assert sum(url.startswith(FIND_URL) for url in seen) == 1
    lot_1 = ("SELECT property_id IS NOT NULL, location_issue IS NOT NULL, location_retry "
             "FROM offers WHERE external_id = 'BOE-B-2026-35273#1'")
    with psycopg.connect(migrated_database) as conn:
        parent = conn.execute("SELECT extraction_status FROM offers "
                              "WHERE external_id = 'BOE-B-2026-35273'").fetchone()
        assert conn.execute(lot_1).fetchone() == (False, True, True)
    assert parent == ("extraida",)  # un reintento no vuelve a pasar el anuncio por el LLM

    # Al día siguiente CartoCiudad responde: el lote se ubica con lo ya extraído, sin el LLM.
    no_llm = FakeLLMClient(lambda *a: (_ for _ in ()).throw(AssertionError("sin LLM")))
    again = extract_boe_v(migrated_database, boe_client(), no_llm, geocoder=geocoded)
    assert (again["retried"], again["located"], again["announcements"]) == (1, 1, 0)
    assert again["unlocated"] == []
    with psycopg.connect(migrated_database) as conn:
        assert conn.execute(lot_1).fetchone() == (True, False, False)
