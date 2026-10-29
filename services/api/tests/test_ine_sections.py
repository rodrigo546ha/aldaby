"""Cargador de la cartografía de secciones del INE (F3.2), con respuestas sintéticas.

Las geometrías son dos cuadrados inventados junto a la Puerta del Sol, no datos del INE.
"""

from datetime import UTC, datetime

import httpx
import pytest

from housefinder.db.sections import (
    SectionRow,
    SourceRecord,
    count_sections,
    section_at,
    upsert_sections,
    upsert_source,
)
from housefinder.ingestion.ine_sections import (
    collection_url,
    fetch_sections,
    first_page_params,
    parse_page,
    source_record,
)


def square(lon: float, lat: float, size: float = 0.01) -> dict:
    ring = [[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size],
            [lon, lat]]
    return {"type": "MultiPolygon", "coordinates": [[ring]]}


def feature(code: str, tipo: str = "SECCIONADO", geometry: dict | None = None) -> dict:
    return {
        "type": "Feature",
        "properties": {"CUSEC": code, "CUMUN": code[:5], "CPRO": code[:2], "TIPO": tipo},
        "geometry": geometry or square(-3.71, 40.41),
    }


NEXT = "https://www.ine.es/geoserver/ogc/features/v1/collections/x/items?startIndex=2"
PAGE_1 = {
    "numberMatched": 3,
    "features": [
        feature("2807901001", geometry=square(-3.71, 40.41)),
        feature("2807901000", tipo="DISTRITO", geometry=square(-3.71, 40.41, 0.02)),
    ],
    "links": [{"rel": "next", "href": NEXT}],
}
PAGE_2 = {
    "numberMatched": 3,
    "features": [feature("2807901002", geometry=square(-3.70, 40.41))],
    "links": [],
}


def test_filtro_de_la_primera_pagina():
    params = first_page_params("28", 500)
    assert params["filter"] == "CPRO='28' AND TIPO='SECCIONADO'"
    assert params["limit"] == "500"
    with pytest.raises(ValueError, match="provincia"):
        first_page_params("28' OR '1'='1", 500)


def test_la_pagina_salta_los_contornos_de_distrito():
    page = parse_page(PAGE_1, "28")
    assert [s.code for s in page.sections] == ["2807901001"]
    assert page.skipped == 1
    assert page.next_url == NEXT
    assert page.sections[0].municipality == "28079"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"CUSEC": "28079010"}, "Código de sección"),
        ({"CUSEC": "0807901001", "CUMUN": "08079"}, "Código de sección"),  # otra provincia
        ({"CUMUN": "28005"}, "municipio"),
    ],
)
def test_validaciones(change, message):
    bad = feature("2807901001")
    bad["properties"].update(change)
    with pytest.raises(ValueError, match=message):
        parse_page({"features": [bad]}, "28")


def test_geometria_no_esperada():
    bad = feature("2807901001", geometry={"type": "Point", "coordinates": [-3.7, 40.4]})
    with pytest.raises(ValueError, match="geometría"):
        parse_page({"features": [bad]}, "28")


def mock_client(pages: list[dict]) -> httpx.Client:
    calls = iter(pages)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(calls))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_sigue_los_enlaces_next():
    rows = list(fetch_sections(mock_client([PAGE_1, PAGE_2]), 2025, "28"))
    assert [r.code for r in rows] == ["2807901001", "2807901002"]


def test_para_si_faltan_elementos():
    short = {**PAGE_2, "numberMatched": 5}
    with pytest.raises(ValueError, match="anunció 5"):
        list(fetch_sections(mock_client([{**PAGE_1, "numberMatched": 5}, short]), 2025, "28"))


def test_la_fuente_registra_licencia_y_huella():
    rows = [SectionRow("2807901001", "28079", "{}")]
    source = source_record(2025, "28", rows)
    assert source.id == "ine-secciones-2025-28"
    assert "CC BY 4.0" in source.license
    assert "sha256" in source.notes
    assert source.url == collection_url(2025)


# --- Contra la base de datos -----------------------------------------------------------------


@pytest.fixture(scope="module")
def conn(migrated_database: str):
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(migrated_database) as connection:
        yield connection


@pytest.mark.db
def test_carga_idempotente_y_seccion_de_un_punto(conn):
    import json

    rows = [
        SectionRow("2807901001", "28079", json.dumps(square(-3.71, 40.41))),
        SectionRow("2807901002", "28079", json.dumps(square(-3.70, 40.41))),
    ]
    source = SourceRecord("ine-secciones-2025-28", "prueba", "https://example.org",
                          "CC BY 4.0", datetime.now(UTC))
    for _ in range(2):  # repetir la carga no duplica
        upsert_source(conn, source)
        upsert_sections(conn, rows, 2025, source.id)
    assert count_sections(conn, 2025, "2807901") == 2
    hit = section_at(conn, -3.705, 40.415, 2025)
    assert hit is not None and hit.code == "2807901001"
    assert section_at(conn, -3.695, 40.415, 2025).code == "2807901002"
    assert section_at(conn, -3.80, 40.415, 2025) is None  # fuera de las dos
    assert section_at(conn, -3.705, 40.415, 2024) is None  # otra cartografía
    conn.rollback()
