"""Municipios del INE por su nombre (ADR-0056)."""

import pytest

from housefinder.ingestion.ine_municipios import display_name
from housefinder.territory.municipalities import Municipality, load_municipalities, search


@pytest.mark.parametrize("ine, shown", [
    ("Rozas de Madrid, Las", "Las Rozas de Madrid"),
    ("Coruña, A", "A Coruña"),
    ("Alicante/Alacant", "Alicante/Alacant"),
    ("Palmas de Gran Canaria, Las", "Las Palmas de Gran Canaria"),
    # La coma de un nombre compuesto no es un artículo
    ("Castell d'Aro, Platja d'Aro i s'Agaró", "Castell d'Aro, Platja d'Aro i s'Agaró"),
])
def test_nombre_con_el_articulo_delante(ine, shown):
    assert display_name(ine) == shown


def test_la_relacion_del_ine_esta_entera():
    municipalities = load_municipalities()
    assert len(municipalities) > 8000
    madrid = municipalities["28079"]
    assert (madrid.name, madrid.territory) == ("Madrid", "ES-13-28079")
    assert municipalities["48020"].territory == "ES-16-48020"  # Bilbao


SAMPLE = {m.code: m for m in [
    Municipality("28079", "Madrid", "13"), Municipality("28127", "Las Rozas de Madrid", "13"),
    Municipality("28005", "Alcalá de Henares", "13"), Municipality("45087", "Madridejos", "08"),
]}


def test_busqueda_sin_tildes_y_primero_lo_que_empieza_igual():
    assert [m.name for m in search("madrid", municipalities=SAMPLE)] == [
        "Madrid", "Madridejos", "Las Rozas de Madrid"]
    assert [m.name for m in search("alcala hen", municipalities=SAMPLE)] == ["Alcalá de Henares"]
    assert search("  ", municipalities=SAMPLE) == []


def test_api_de_municipios():
    from fastapi.testclient import TestClient

    from housefinder.api.main import app

    http = TestClient(app)
    found = http.get("/territory/municipalities", params={"q": "getafe"}).json()
    assert found[0] == {"code": "28065", "territory": "ES-13-28065", "name": "Getafe",
                        "province": "Madrid"}
    assert http.get("/territory/municipalities/28079").json()["name"] == "Madrid"
    assert http.get("/territory/municipalities/99999").status_code == 404
    assert http.get("/territory/municipalities", params={"q": "a"}).status_code == 422


def test_diccionario_con_la_cabecera_en_la_segunda_fila(tmp_path):
    from test_serpavi import write_xlsx

    from housefinder.ingestion.ine_municipios import parse

    book = write_xlsx(tmp_path / "diccionario.xlsx", {"dic26": [
        ["Relación de municipios y códigos a 1 de enero de 2026"],
        ["CODAUTO", "CPRO", "CMUN", "DC", "NOMBRE"],
        ["13", "28", "127", "9", "Rozas de Madrid, Las"],
        ["1", "4", "1", "4", "Abla"],
    ]})
    assert parse(book) == {
        "04001": {"name": "Abla", "region": "01"},
        "28127": {"name": "Las Rozas de Madrid", "region": "13"},
    }
