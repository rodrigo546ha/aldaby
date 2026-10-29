"""API de anuncios del BOE (F4.4) contra la base temporal, con anuncios reales: el de la TGSS de
Madrid (dos parcelas en Alcalá de Henares, lotes extraídos con un LLM falso) y el de la TGSS de
Salamanca con su corrección."""

from datetime import date

import pytest
from conftest import add_section
from fastapi.testclient import TestClient

from housefinder.api.deps import get_db
from housefinder.api.main import app

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")


@pytest.fixture(scope="module")
def client(migrated_database: str):
    import test_boe_corrections
    import test_extraction

    from housefinder.agent.llm import FakeLLMClient
    from housefinder.geo.cartociudad import Geocoded
    from housefinder.offers.run import extract_boe_v, run_boe_v

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM watch_issues WHERE source = 'offers_boe_v' "
                     "AND issue_id IN ('2026-10-27', '2026-10-28')")
        conn.execute("DELETE FROM geocode_cache WHERE query LIKE 'rc:%'")
        conn.execute("UPDATE offers SET extraction_status = 'pendiente' "
                     "WHERE external_id = 'BOE-B-2026-35273'")
    run_boe_v(migrated_database, test_boe_corrections.boe_client(), date(2026, 10, 27), days=1,
              geocoder=lambda a: None, parcels=lambda r: None)
    run_boe_v(migrated_database, test_extraction.boe_client(), date(2026, 10, 28), days=1)
    add_section(migrated_database, "2800597005", -3.36, 40.51)
    extract_boe_v(
        migrated_database, test_extraction.boe_client(),
        FakeLLMClient(lambda *a: test_extraction.EXTRACTION), only=["BOE-B-2026-35273"],
        geocoder=lambda address: Geocoded(-3.36, 40.51, "portal", address, "28005", None),
    )

    def db():
        with psycopg.connect(migrated_database) as conn:
            yield conn

    app.dependency_overrides[get_db] = db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_lista_sin_correcciones_sueltas(client):
    listed = {a["boe_id"]: a for a in client.get("/boe/announcements").json()}
    assert "BOE-B-2026-35167" not in listed  # va dentro del anuncio que corrige
    assert listed["BOE-B-2026-34188"]["corrections"] == 1
    assert listed["BOE-B-2026-35273"]["status"] == "extraida"
    assert listed["BOE-B-2026-35273"]["lots"] == 2


def test_lotes_con_la_cita_de_cada_dato(client):
    detail = client.get("/boe/announcements/BOE-B-2026-35273").json()
    assert detail["attribution"].startswith("Fuente: Agencia Estatal")
    assert detail["paragraphs"][0].startswith("Acordada la enajenación")
    first, second = detail["lots"]
    fields = {f["name"]: f for f in first["fields"]}
    assert fields["price"]["value"] == "25802189"
    assert fields["price"]["evidence"] == "El tipo de licitación es 25.802.189 €"
    assert first["status"] == "extraida" and first["property_type"] == "suelo"
    assert first["located"] and first["section_code"] == "2800597005"
    rejected = {f["name"]: f for f in second["fields"]}["deposit"]
    assert rejected["value"] is None and rejected["reason"] == "el número no aparece en la cita"


def test_anuncio_con_su_correccion(client):
    original = client.get("/boe/announcements/BOE-B-2026-34188").json()
    assert [c["boe_id"] for c in original["corrections"]] == ["BOE-B-2026-35167"]
    assert original["corrections"][0]["paragraphs"][0].startswith("Advertidos errores")
    correction = client.get("/boe/announcements/BOE-B-2026-35167").json()
    assert correction["corrects"] == "BOE-B-2026-34188"
    assert client.get("/boe/announcements/BOE-B-2026-99999").status_code == 404
