"""Extracción con evidencia comprobada (ADR-0013), con el anuncio real BOE-B-2026-35273 (dos
parcelas de la TGSS en Alcalá de Henares) y un LLM falso: el LLM solo propone; los valores que
quedan son los que están escritos en la fuente."""

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from conftest import add_section

from housefinder.agent.extraction import (
    NO_SPAN,
    PART_LIMIT,
    DocumentExtraction,
    LotExtraction,
    ProposalMismatch,
    Quoted,
    check_document,
    check_field,
    document_parts,
    extract,
    heading_starts,
    lot_part,
    recheck_document,
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
    """Sin encabezados «Lote…» no se sabe cuál de los dos es el bueno (ADR-0033)."""
    text = "Se venden:\n1.- Piso en la calle Mayor, 3. Precio: 100.000 €.\n" \
           "2.- Piso en la calle Real, 5. Precio: 200.000 €."
    twins = [lot(label=q("1.-", "1.-"), price=q(price, f"Precio: {shown} €"))
             for price, shown in [("100000", "100.000"), ("200000", "200.000")]]
    raw = DocumentExtraction(is_correction=False, corrected_reference=NONE, lots=twins)
    assert all(checked.value("price") is None for checked in check_document(text, raw).lots)


def test_dos_elementos_del_mismo_lote_son_un_lote():
    """El modelo saca un elemento por parcela con la misma etiqueta del lote (BOE-B-2026-31848).
    Con encabezados «Lote…», el párrafo de la etiqueta dice de qué lote es: se juntan."""
    twin = lot(label=q("Lote 1", "Lote 1: Urbana"),
               price=q("6778639", "El tipo de licitación es 6.778.639 €"))  # el del lote 2
    raw = DocumentExtraction(is_correction=False, corrected_reference=NONE, lots=[LOT_1, twin])
    checked = check_document(TEXT, raw)
    assert len(checked.lots) == 1
    assert checked.lots[0].value("price") == Decimal("25802189")
    assert checked.lots[0].value("cadastral_ref") == "7744401VK6874N0001FJ"


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


# --- Anuncios reales que se quedaban sin ubicar (ADR-0033) -------------------------------------

EVALUATION = Path(__file__).parents[1] / "data" / "evaluation" / "anuncios"


def real(external_id: str) -> str:
    return (EVALUATION / f"boe-{external_id}.txt").read_text()


def test_encabezados_de_lote_al_principio_de_parrafo():
    text = real("BOE-B-2026-32279")
    source = " ".join(text.split())
    starts = heading_starts(text)
    assert [source[s:s + 11] for s in starts] == ["Lote nº 1.-", "Lote nº 2.-", "Lote nº 3.-"]
    huelva = real("BOE-B-2026-35250")
    assert [" ".join(huelva.split())[s:s + 5] for s in heading_starts(huelva)] == [
        "Uno) ", "Dos) ", "Tres)", "Cuatr"]


def test_sin_etiqueta_literal_el_tramo_es_el_del_encabezado_de_sus_citas():
    """qwen3 escribía «El texto menciona 'Lote nº 4'…» o «Lote 4» por «Lote nº 4:»: el lote
    perdía su tramo y, con él, todos sus datos (BOE-B-2026-32776)."""
    text = real("BOE-B-2026-32776")
    fourth = lot(
        label=q("Lote 4", "El texto menciona el Lote nº 4 como una parcela"),
        property_type="rustica", property_type_evidence="Lote nº 4: RÚSTICA",
        address=q("Parcela 90 del polígono 7", "Lote nº 4: RÚSTICA: Parcela 90 del polígono 7"),
        municipality=q("Gualchos", "en el término de Gualchos"),
        cadastral_ref=q("18095A007000900000IT", "Referencia catastral 18095A007000900000IT."),
        price=q("1685.80", "El tipo de licitación será de 1.685,80 €"),
    )
    first = lot(
        label=q("Lote nº 1", "Lote nº 1:"),
        municipality=q("Santa Fe", "término de Santa Fe"),
        price=q("74761.43", "El tipo de licitación será de 74.761,43 €"),
    )
    checked = check_document(text, DocumentExtraction(
        is_correction=False, corrected_reference=NONE, lots=[first, fourth]))
    assert checked.lots[1].value("cadastral_ref") == "18095A007000900000IT"
    assert checked.lots[1].value("price") == Decimal("1685.80")
    assert checked.lots[1].value("address") == "Parcela 90 del polígono 7"
    # El lote 1 acaba en el encabezado del lote 2, no en el del lote 4: su precio está ahí.
    assert checked.lots[0].value("price") == Decimal("74761.43")
    assert checked.proposed["lots"][1]["label"]["value"] == "Lote 4"


def test_citas_de_ubicacion_de_dos_lotes_distintos_no_dan_tramo():
    text = real("BOE-B-2026-32776")
    mixed = lot(
        label=q("Lote 9", "El lote nueve"),
        address=q("Parcela 90 del polígono 7", "Parcela 90 del polígono 7"),  # lote 4
        cadastral_ref=q("18142A032003170000YM", "Referencia catastral 18142A032003170000YM"),  # 3
    )
    other = lot(label=q("Lote nº 1", "Lote nº 1:"))
    checked = check_document(text, DocumentExtraction(
        is_correction=False, corrected_reference=NONE, lots=[other, mixed]))
    assert checked.lots[1].fields["cadastral_ref"].reason == NO_SPAN


def test_direccion_compuesta_de_partes_de_la_cita():
    evidence = "1. Antigua casa-cuartel de la Guardia Civil en CACÍN (Granada), Plaza Cuartel, 6."
    source = real("BOE-B-2026-35361")
    assert check_field(source, q("Plaza Cuartel 6, Cacín", evidence), "text").status == \
        "verificado"
    # Una palabra que no está en la cita no vale, aunque el resto sí.
    assert check_field(source, q("Plaza del Cuartel 6, Cacín", evidence), "text").reason == \
        "el texto no está en la cita"


@pytest.mark.parametrize("external_id, value, evidence, ref", [
    ("BOE-B-2026-35250", "21026A0 0400061 0000", "Referencia catastral 21026A0 0400061 0000.",
     "21026A004000610000"),  # sin los dos caracteres de control
    ("BOE-B-2026-33450", "2006983/9728140/0439/9E",
     "• Planta semisótano: 2006983/9728140/0439/9E, con una superficie de 403,18 m2.",
     "2006983972814004399E"),  # Gipuzkoa, con barras
])
def test_referencias_con_espacios_o_barras(external_id, value, evidence, ref):
    checked = check_field(real(external_id), q(value, evidence), "cadastral")
    assert (checked.status, checked.value) == ("verificado", ref)


def test_una_referencia_tiene_que_tener_cifras():
    assert check_field("Referencia catastral: PARCELARIA", q("PARCELARIA", "Referencia "
                       "catastral: PARCELARIA"), "cadastral").status == "rechazado"


# --- Anuncios largos (ADR-0034) ------------------------------------------------------------------

# Nueve lotes de fincas rústicas en El Frasno (Zaragoza), 80.107 caracteres: no cabía en la
# ventana del modelo, que solo veía el final y devolvía los lotes 8 y 9.
FRASNO = (FIXTURES / "texto-BOE-B-2026-32775.txt").read_text()


def test_un_anuncio_largo_va_por_partes_con_lotes_enteros():
    parts = document_parts(FRASNO)
    assert len(parts) == 9 and all(len(p) <= PART_LIMIT for p in parts)
    preamble = FRASNO[:FRASNO.index("LOTE Nº 1.")]
    for n, part in enumerate(parts, start=1):
        assert part.startswith(preamble)  # el título y las condiciones de antes de los lotes
        assert f"LOTE Nº {n}." in part and f"LOTE Nº {n + 1}." not in part
    # Con lotes cortos, varios por parte, como mucho `max_lots`.
    lots = "\n".join(f"Lote {n}.- Finca en calle Mayor {n}.\n" + "x" * 100 for n in range(1, 8))
    short = document_parts("Anuncio\n" + lots, max_chars=500, max_lots=3)
    assert [p.count("Lote ") for p in short] == [3, 3, 1]
    assert document_parts("Anuncio corto\nLote 1.- uno\nLote 2.- dos") == [
        "Anuncio corto\nLote 1.- uno\nLote 2.- dos"]


def test_las_fincas_de_un_lote_no_cierran_su_tramo():
    part = document_parts(FRASNO)[0]
    source = " ".join(part.split())
    assert [source[s:s + 10] for s in heading_starts(part)] == ["LOTE Nº 1."]  # no «1.1», «1.2»
    first = lot(
        label=q("LOTE Nº 1", "LOTE Nº 1. Expediente 2026 050 00038."),
        property_type="rustica", property_type_evidence="Finca rústica situada en Inogés",
        municipality=q("El Frasno", "perteneciente al término municipal de El Frasno"),
        cadastral_ref=q("50111A109000090000BO", "su referencia catastral es la "
                                                "50111A109000090000BO"),  # finca 1.1
    )
    second = lot(label=q("LOTE Nº 2", "LOTE Nº 2. Expediente 2026 050 00039."))
    checked = check_document(FRASNO, DocumentExtraction(
        is_correction=False, corrected_reference=NONE, lots=[first, second]))
    # El tramo del lote 1 llega hasta el lote 2, con sus once fincas dentro.
    assert checked.lots[0].value("cadastral_ref") == "50111A109000090000BO"
    assert checked.lots[0].value("municipality") == "El Frasno"


def test_las_fincas_que_el_modelo_saca_aparte_se_juntan_en_su_lote():
    """qwen3 sacó El Frasno como 67 lotes: cada «LOTE Nº n.» y cada una de sus fincas («9.1»,
    «9.2»…). Un lote es lo que se subasta junto: las fincas van en él, con la ubicación de la
    primera que tiene referencia catastral (ADR-0034)."""
    eighth = lot(label=q("LOTE Nº 8", "LOTE Nº 8. Expediente 2026 050 00045."))
    ninth = lot(label=q("LOTE Nº 9", "LOTE Nº 9. Expediente 2026 050 00046."),
                municipality=q("El Frasno", "perteneciente al término municipal de El Frasno"),
                address=q("Inogés", "situadas en Inogés"))  # del encabezado: no ubica una finca
    fincas = [lot(label=q(label, label), property_type="rustica",
                  property_type_evidence="Finca rústica situada en Inogés",
                  cadastral_ref=q(ref, f"su referencia catastral es la {ref}"))
              for label, ref in [("9.1", "50111A101001020000BF"),
                                 ("9.2", "50111A101001300000BQ")]]
    checked = check_document(FRASNO, DocumentExtraction(
        is_correction=False, corrected_reference=NONE, lots=[eighth, ninth, *fincas]))
    assert [x.value("label") for x in checked.lots] == ["LOTE Nº 8", "LOTE Nº 9"]
    assert checked.lots[1].value("cadastral_ref") == "50111A101001020000BF"  # la finca 9.1
    assert checked.lots[1].value("municipality") == "El Frasno"
    assert checked.lots[1].property_type == "rustica"
    assert len(checked.proposed["lots"]) == 4  # lo propuesto, tal como llegó


ASTURIAS = (FIXTURES / "texto-BOE-B-2026-31848.txt").read_text()
SALAMANCA = (FIXTURES / "texto-BOE-B-2026-31747.txt").read_text()


def test_la_fila_de_precios_no_empieza_otro_lote():
    """En 31848 cada lote acaba con su fila de la tabla de precios («Lote 1 2ª subasta…»): no es
    un lote nuevo, y el precio queda dentro del tramo del lote."""
    assert sum(len(part.split("LOTE Nº ")) - 1 for part in document_parts(ASTURIAS)) == 17
    assert len(document_parts(ASTURIAS)) == 4  # antes, 6: las filas contaban como lotes
    first = lot(label=q("LOTE Nº 1", "LOTE Nº 1: SEGUNDA, TERCERA Y CUARTA SUBASTA."),
                price=q("86.12", "Lote 1 2ª subasta 3ª subasta 4ª subasta Tipo de licitación "
                                 "86,12 euros"))
    second = lot(label=q("LOTE Nº 2", "LOTE Nº 2: SEGUNDA, TERCERA Y CUARTA SUBASTA."))
    checked = check_document(document_parts(ASTURIAS)[0], DocumentExtraction(
        is_correction=False, corrected_reference=NONE, lots=[first, second]))
    assert checked.lots[0].value("price") == Decimal("86.12")


def test_un_lote_que_el_modelo_se_salta_se_pide_otra_vez():
    """En 31747 el modelo devolvió el lote 7 de su parte y se saltó del 8 al 11. Se le pide cada
    uno otra vez, solo con el preámbulo; de la respuesta vale lo que es de ese lote."""
    numbers = [int(n) for n in re.findall(r"^LOTE Nº (\d+):", SALAMANCA, re.MULTILINE)]

    def respond(instructions, document, output):
        here = [int(n) for n in re.findall(r"^LOTE Nº (\d+):", document, re.MULTILINE)]
        given = [n for n in here if len(here) == 1 or not 8 <= n <= 11]
        lots = [lot(label=q(f"LOTE Nº {n}:", f"LOTE Nº {n}:")) for n in given]
        if len(here) == 1:  # y un lote de otra parte, que no vale
            lots.append(lot(label=q("LOTE Nº 1:", "LOTE Nº 1:")))
        return DocumentExtraction(is_correction=False, corrected_reference=NONE, lots=lots)

    llm = FakeLLMClient(respond)
    checked = extract(llm, SALAMANCA)
    assert numbers == list(range(1, 14))
    assert len(llm.calls) == len(document_parts(SALAMANCA)) + 4
    labels = [x.value("label") for x in checked.lots]
    assert sorted(labels, key=lambda label: int(label[8:-1])) == [
        f"LOTE Nº {n}:" for n in numbers]
    assert labels[-4:] == ["LOTE Nº 8:", "LOTE Nº 9:", "LOTE Nº 10:", "LOTE Nº 11:"]
    again = recheck_document(SALAMANCA, checked.proposed)  # sin el LLM
    assert [x.as_dict() for x in again.lots] == [x.as_dict() for x in checked.lots]
    # Lo propuesto con otras reglas de corte no se puede volver a comprobar: se extrae otra vez.
    with pytest.raises(ProposalMismatch):
        recheck_document(SALAMANCA, {**checked.proposed, "parts": checked.proposed["parts"][1:]})


def test_varias_referencias_en_una_cita_vale_la_primera():
    """En 31747 el modelo juntó las referencias de las fincas del lote 12 en un valor y en una
    cita de varias líneas que no es seguida en el documento."""
    part = lot_part(SALAMANCA, 11)
    twelve = lot(label=q("LOTE Nº 12:", "LOTE Nº 12:"), cadastral_ref=q(
        "37014A514013730000BY, 37014A514013550000BD",
        "Referencia Catastral: 37014A514013730000BY.\nReferencia Catastral: 37014A514013550000BD."))
    checked = check_document(part, DocumentExtraction(
        is_correction=False, corrected_reference=NONE, lots=[twelve]))
    assert checked.lots[0].value("cadastral_ref") == "37014A514013730000BY"


def test_cada_parte_se_extrae_y_se_comprueba_contra_su_texto():
    def respond(instructions, document, output):
        n = next(n for n in range(1, 10) if f"LOTE Nº {n}." in document)
        label = f"LOTE Nº {n}."
        # El lote 2 cita el 1: está en el documento, pero no en su parte.
        ref = "50111A109000090000BO" if n in (1, 2) else None
        return DocumentExtraction(is_correction=False, corrected_reference=NONE, lots=[lot(
            label=q(label, label), property_type="rustica",
            cadastral_ref=q(ref, ref) if ref else NONE)])

    llm = FakeLLMClient(respond)
    checked = extract(llm, FRASNO)
    assert len(llm.calls) == 9 and len(checked.lots) == 9
    assert checked.lots[0].value("cadastral_ref") == "50111A109000090000BO"
    assert checked.lots[1].fields["cadastral_ref"].reason == "la cita no está en el documento"
    assert len(checked.proposed["parts"]) == 9
    again = recheck_document(FRASNO, checked.proposed)  # sin el LLM, partido igual
    assert [lot.as_dict() for lot in again.lots] == [lot.as_dict() for lot in checked.lots]


def test_la_cita_envuelta_en_una_frase_del_modelo():
    """qwen3 escribía «The text states 'municipio de UTIEL'»: vale el fragmento entre comillas
    que está en el documento; el valor se sigue comprobando contra él (BOE-B-2026-32556)."""
    text = "Lote 49.- Finca rústica en el municipio de UTIEL, polígono 36, parcela 251."
    raw = DocumentExtraction(is_correction=False, corrected_reference=NONE, lots=[lot(
        municipality=q("Utiel", "The text states 'municipio de UTIEL'"),
        address=q("polígono 36, parcela 251", "El texto dice «polígono 36, parcela 251»"),
        price=q("1000", "The text states 'municipio de UTIEL'"))])
    checked = check_document(text, raw).lots[0]
    assert checked.value("municipality") == "Utiel"
    assert checked.fields["municipality"].evidence == "municipio de UTIEL"
    assert checked.value("address") == "polígono 36, parcela 251"
    assert checked.fields["price"].reason == "el número no aparece en la cita"
    # Lo propuesto se guarda tal como llegó.
    assert check_document(text, raw).proposed["lots"][0]["municipality"]["evidence"] == \
        "The text states 'municipio de UTIEL'"


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
    `extract_offers` entero y cada reintento repetía la extracción con el LLM (ADR-0031)."""
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
        # Sin ubicar otra vez: la búsqueda inversa lee los lotes ubicados de la misma base.
        conn.execute("UPDATE offers SET property_id = NULL, location_source = NULL "
                     "WHERE external_id LIKE 'BOE-B-2026-35273#%'")


@pytest.mark.db
def test_una_extraccion_nueva_actualiza_retira_y_no_toca_lo_confirmado(migrated_database: str):
    """Antes, volver a extraer un anuncio no cambiaba sus lotes: `upsert_offer` solo actualiza el
    título y lo recibido (ADR-0033)."""
    from housefinder.offers.run import extract_boe_v, run_boe_v

    pending_again(migrated_database)
    run_boe_v(migrated_database, boe_client(), date(2026, 10, 28), days=1)
    stray = lot(label=q("Lote 3", "Lote 3"))  # un lote que el anuncio no tiene
    only_first = DocumentExtraction(is_correction=False, corrected_reference=NONE,
                                    lots=[LOT_1, LOT_2, stray])
    # Tres lotes la primera vez (el tercero, inventado por el modelo, sin tramo).
    extract_boe_v(migrated_database, boe_client(), FakeLLMClient(lambda *a: only_first),
                  geocoder=geocoded)
    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("UPDATE offers SET extraction_status = 'pendiente' "
                     "WHERE external_id = 'BOE-B-2026-35273'")
        conn.execute("UPDATE offers SET extraction_status = 'confirmada' "
                     "WHERE external_id = 'BOE-B-2026-35273#2'")
    better = lot(label=q("Lote 1", "Lote 1: Urbana"),
                 price=q("25802189", "El tipo de licitación es 25.802.189 €"))
    report = extract_boe_v(migrated_database, boe_client(),
                           FakeLLMClient(lambda *a: DocumentExtraction(
                               is_correction=False, corrected_reference=NONE, lots=[better])),
                           geocoder=geocoded)
    assert report["retired"] == 1  # el #3; el #2 está confirmado y no se toca
    with psycopg.connect(migrated_database, autocommit=True) as conn:
        rows = {r[0]: r[1:] for r in conn.execute(
            "SELECT external_id, extraction_status, cadastral_ref, property_id IS NULL "
            "FROM offers WHERE external_id LIKE 'BOE-B-2026-35273#%'").fetchall()}
        conn.execute("UPDATE offers SET extraction_status = 'extraida' "
                     "WHERE external_id = 'BOE-B-2026-35273#2'")
    # El #1 sin referencia ya: se desenlaza para volver a ubicarlo (aquí, sin dirección, no puede).
    assert rows["BOE-B-2026-35273#1"] == ("extraida", None, True)
    assert rows["BOE-B-2026-35273#2"][0] == "confirmada"
    assert rows["BOE-B-2026-35273#3"] == ("retirada", None, True)

    # Una extracción más que lo vuelve a encontrar: el #3 vuelve, sin el aviso de retirado.
    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("UPDATE offers SET extraction_status = 'pendiente' "
                     "WHERE external_id = 'BOE-B-2026-35273'")
    extract_boe_v(migrated_database, boe_client(), FakeLLMClient(lambda *a: only_first),
                  geocoder=geocoded)
    with psycopg.connect(migrated_database) as conn:
        back = conn.execute("SELECT extraction_status, location_issue FROM offers "
                            "WHERE external_id = 'BOE-B-2026-35273#3'").fetchone()
    assert back[0] == "extraida"
    assert back[1] != "una extracción nueva del anuncio ya no lo encuentra"


@pytest.mark.db
def test_volver_a_comprobar_sin_el_llm_lo_que_propuso_el_modelo(migrated_database: str):
    from housefinder.offers.run import extract_boe_v, run_boe_v

    pending_again(migrated_database)
    run_boe_v(migrated_database, boe_client(), date(2026, 10, 28), days=1)
    extract_boe_v(migrated_database, boe_client(), FakeLLMClient(lambda *a: EXTRACTION),
                  geocoder=geocoded)
    no_llm = FakeLLMClient(lambda *a: (_ for _ in ()).throw(AssertionError("sin LLM")))
    again = extract_boe_v(migrated_database, boe_client(), no_llm, geocoder=geocoded,
                          only=["BOE-B-2026-35273"], recheck=True)
    assert (again["announcements"], again["lots"], again["rejected_fields"]) == (1, 2, 2)
    with psycopg.connect(migrated_database, autocommit=True) as conn:
        proposed = conn.execute("SELECT extracted->'proposed'->'lots'->1->'deposit'->>'value' "
                                "FROM offers WHERE external_id = 'BOE-B-2026-35273'").fetchone()
        conn.execute("UPDATE offers SET property_id = NULL, location_source = NULL "
                     "WHERE external_id LIKE 'BOE-B-2026-35273#%'")
    assert proposed == ("340000",)  # la garantía inventada se guarda como propuesta, no como dato
