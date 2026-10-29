"""GET /territory contra la base temporal (F3.6), con un geocodificador falso.

Secciones e indicadores sintéticos, lejos de los de otros tests: 2807999001 tiene el mismo
polígono en 2020 y 2025; 2807999002 se redibuja en 2025.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from housefinder.api.deps import get_db, get_geocoder
from housefinder.api.main import app
from housefinder.db.indicators import IndicatorRow, upsert_indicators
from housefinder.db.sections import SectionRow, SourceRecord, upsert_sections, upsert_source
from housefinder.geo.cartociudad import AddressTooVague, Geocoded

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")


def square(lon, lat, size=0.01):
    ring = [[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size],
            [lon, lat]]
    return json.dumps({"type": "MultiPolygon", "coordinates": [[ring]]})


@pytest.fixture(scope="module")
def database(migrated_database: str) -> str:
    now = datetime.now(UTC)
    with psycopg.connect(migrated_database) as conn:
        for vintage in (2020, 2025):
            source = SourceRecord(f"ine-secciones-{vintage}-28", "prueba", "https://x", "CC BY",
                                  now)
            upsert_source(conn, source)
            # 2807999002 es más grande en 2025: redibujada.
            size2 = 0.02 if vintage == 2025 else 0.01
            upsert_sections(conn, [SectionRow("2807999001", "28079", square(-3.50, 40.50)),
                                   SectionRow("2807999002", "28079",
                                              square(-3.48, 40.50, size2))],
                            vintage, source.id)
        upsert_source(conn, SourceRecord("ine-adrh-31097", "prueba", "https://x", "CC BY", now))
        rows = []
        for code in ("2807999001", "2807999002"):
            rows += [IndicatorRow(code, 2020, "renta_neta_media_persona", 2019, Decimal(20000),
                                  "EUR"),
                     IndicatorRow(code, 2025, "renta_neta_media_persona", 2024, Decimal(23000),
                                  "EUR"),
                     IndicatorRow(code, 2025, "poblacion", 2024, Decimal(1500), "personas")]
        upsert_indicators(conn, rows, "ine-adrh-31097")
        conn.commit()
    return migrated_database


@pytest.fixture
def client(database: str):
    calls: list[str] = []

    def fake_geocoder(address: str) -> Geocoded:
        calls.append(address)
        if "sin numero" in address:
            raise AddressTooVague("La dirección solo se localiza como «Municipio»")
        return Geocoded(-3.495, 40.505, "portal", "CALLE FALSA 1, 28079 Madrid", "28079",
                        None)

    def db():
        with psycopg.connect(database) as conn:
            yield conn

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_geocoder] = lambda: fake_geocoder
    try:
        yield TestClient(app), calls
    finally:
        app.dependency_overrides.clear()


def test_direccion_con_seccion_renta_y_tendencia(client):
    http, calls = client
    resp = http.get("/territory", params={"address": "Calle Falsa 1, Madrid"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["section"] == {"code": "2807999001", "municipality": "28079", "vintage": 2025}
    assert body["location"]["matched"] == "CALLE FALSA 1, 28079 Madrid"
    renta = body["figures"]["territory.renta_neta_media_persona"]
    assert renta["value"] == "23000" and renta["unit"] == "EUR/año"
    assert body["figures"]["territory.renta_neta_media_persona.change_5y"]["value"] == "0.1500"
    assert len(body["series"]["renta_neta_media_persona"]) == 2
    assert any("CartoCiudad" in a for a in body["attribution"])
    assert any("INE" in a for a in body["attribution"])
    assert calls == ["Calle Falsa 1, Madrid"]


def test_la_segunda_consulta_sale_de_la_cache(client):
    http, calls = client
    for _ in range(2):
        assert http.get("/territory", params={"address": "calle  falsa 1, MADRID"}
                        ).status_code == 200
    assert calls == []  # misma consulta normalizada que la del test anterior


def test_seccion_redibujada_sin_tendencia(client):
    http, _ = client
    body = http.get("/territory", params={"lon": -3.465, "lat": 40.515}).json()
    assert body["section"]["code"] == "2807999002"
    assert "territory.renta_neta_media_persona.change_5y" not in body["figures"]
    assert any("redibujó" in n for n in body["notes"])
    assert body["location"]["match_type"] is None  # coordenadas: sin geocodificar


def test_fuera_de_las_secciones_es_404(client):
    http, _ = client
    assert http.get("/territory", params={"lon": 2.17, "lat": 41.38}).status_code == 404


def test_direccion_imprecisa_es_422(client):
    http, _ = client
    resp = http.get("/territory", params={"address": "Madrid sin numero"})
    assert resp.status_code == 422 and "Municipio" in resp.json()["detail"]


def test_ni_direccion_ni_coordenadas_es_422(client):
    http, _ = client
    assert http.get("/territory").status_code == 422
