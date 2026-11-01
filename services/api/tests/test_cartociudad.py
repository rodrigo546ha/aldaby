"""Geocodificador de CartoCiudad (ADR-0009), sin red: respuestas con la forma de `find`."""

import httpx
import pytest

from housefinder.geo.cartociudad import (
    AddressNotFound,
    AddressTooVague,
    geocode,
    normalize,
    parse_find,
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
