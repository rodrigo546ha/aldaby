"""Geocodificador de CartoCiudad (ADR-0009), sin red: respuestas con la forma de `find`."""

import json
from pathlib import Path

import httpx
import pytest

from housefinder.geo.cartociudad import (
    CANDIDATES_URL,
    AddressNotFound,
    AddressTooVague,
    geocode,
    municipality_codes,
    normalize,
    parse_find,
    parse_municipalities,
)

PORTAL = {
    "type": "portal", "tip_via": "PLAZA", "address": "PUERTA DEL SOL", "portalNumber": 1,
    "noNumber": False, "extension": None, "postalCode": "28014", "poblacion": "Madrid",
    "muniCode": "28079", "lat": 40.4169, "lng": -3.7022, "refCatastral": "0644301VK4704D",
    "state": 0,
}


def test_portal():
    found = parse_find(PORTAL)
    assert (found.lon, found.lat) == (-3.7022, 40.4169)
    assert found.matched == "PLAZA PUERTA DEL SOL 1, 28014 Madrid"
    assert found.municipality == "28079" and found.cadastral_ref == "0644301VK4704D"
    assert not found.approximate


def test_calle_sin_numero_es_aproximada():
    street = {**PORTAL, "type": "callejero", "portalNumber": 0, "noNumber": True}
    found = parse_find(street)
    assert found.approximate
    assert found.matched == "PLAZA PUERTA DEL SOL, 28014 Madrid"


@pytest.mark.parametrize("kind", ["Municipio", "poblacion", "codpost", "toponimo"])
def test_resultados_imprecisos(kind):
    with pytest.raises(AddressTooVague, match=kind):
        parse_find({**PORTAL, "type": kind})


def test_sin_resultado():
    with pytest.raises(AddressNotFound):
        parse_find({})


def test_respuesta_vacia_del_servicio():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    with pytest.raises(AddressNotFound):
        geocode(client, "calle que no existe 999")


def test_normalizacion_para_la_cache():
    assert normalize("  Calle  de ALCALÁ   1 ") == "calle de alcalá 1"


def test_sin_comillas_dobles_ni_barras_invertidas():
    """Con ellas CartoCiudad responde un 500 (BOE-B-2026-34360, comprobado el 2026-11-01)."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(AddressNotFound):
        geocode(client, 'parcela 14, paraje: "Camino de Galleguillos", Sahagún\\ (León)')
    assert seen[0].url.params["q"] == "parcela 14, paraje: Camino de Galleguillos, Sahagún (León)"


# Respuestas reales de `candidates` del 2026-11-01.
CANDIDATES = Path(__file__).parent / "fixtures" / "cartociudad"


def test_codigo_ine_de_un_municipio_por_cualquiera_de_sus_nombres():
    castellon = json.loads((CANDIDATES / "candidates-castellon-de-la-plana.json").read_text())
    assert parse_municipalities(castellon, "Castellón de la Plana") == {"12040"}
    assert parse_municipalities(castellon, "castello de la plana") == {"12040"}
    # Solo el nombre exacto: ni el «Cortijo Gerona» de Luque, ni Girona, ni Gironella.
    gerona = json.loads((CANDIDATES / "candidates-gerona.json").read_text())
    assert parse_municipalities(gerona, "Gerona") == frozenset()
    assert parse_municipalities(gerona, "Girona") == {"17079"}
    # El anuncio en castellano, CartoCiudad en valenciano y sin el municipio entre los candidatos:
    # sus calles y topónimos dicen de qué municipio son.
    algimia = json.loads((CANDIDATES / "candidates-algimia-de-alfara.json").read_text())
    assert parse_municipalities(algimia, "Algimia de Alfara") == {"46030"}
    assert parse_municipalities(algimia, "Torres") == frozenset()  # «Torres Torres» no


def test_nombres_iguales_en_las_lenguas_oficiales():
    from housefinder.geo.names import place_key

    assert place_key("Algimia de Alfara") == place_key("Algímia d'Alfara") == "algimia alfara"
    assert place_key("Cangas de Narcea") == place_key("CANGAS DEL NARCEA")
    assert place_key("Pobra do Brollón, A") == place_key("A Pobra de Brollón")
    assert place_key("Donostia-San Sebastián") == place_key("Donostia/San Sebastián")
    assert place_key("Alcalá de Henares") != place_key("Alcalá del Júcar")


def test_peticion_de_candidatos():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=(CANDIDATES / "candidates-gerona.json").read_bytes())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert municipality_codes(client, 'Girona"') == {"17079"}
    assert str(seen[0].url).startswith(CANDIDATES_URL)
    assert dict(seen[0].url.params) == {"q": "Girona", "limit": "10"}
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):
        municipality_codes(down, "Girona")
