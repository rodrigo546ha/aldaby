"""Tests de la API para el Portal de Subastas del BOE.

Verifica los endpoints:
- POST /boe/subastas/scrape
- GET /boe/subastas/{portal_id}
- POST /boe/subastas/search
"""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from housefinder.api.deps import get_optional_llm, get_org
from housefinder.api.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "boe" / "portal"
client = TestClient(app)


@pytest.fixture(autouse=True)
def _sin_modelo_ni_sesion_real() -> Iterator[None]:
    """Sin modelo (las reglas de respaldo), aunque `.env` configure uno: con `make test`, el
    Makefile exporta el LLM local y el test se quedaba esperando al modelo de verdad."""
    app.dependency_overrides.update({get_optional_llm: lambda: None, get_org: lambda: uuid4()})
    yield
    app.dependency_overrides.clear()


def mock_portal_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "subastas_ava.php" in url:
            content = (FIXTURES / "search_madrid.html").read_bytes()
            return httpx.Response(200, content=content)
        for ver in range(1, 6):
            if f"ver={ver}" in url:
                content = (FIXTURES / f"single_ver{ver}.html").read_bytes()
                return httpx.Response(200, content=content)
        if "verDocumento.php" in url:
            pdf_bytes = (FIXTURES / "edicto_sample.pdf").read_bytes()
            return httpx.Response(
                200, content=pdf_bytes, headers={"Content-Type": "application/pdf"}
            )
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_api_scrape_auction_success():
    with patch("housefinder.offers.boe_portal.make_client", side_effect=mock_portal_client):
        resp = client.post(
            "/boe/subastas/scrape",
            json={
                "url_or_id": "SUB-JA-2026-267866",
                "download_docs": True,
                "run_ai": True,
            },
        )
    assert resp.status_code == 200
    data = resp.json()

    assert data["portal_id"] == "SUB-JA-2026-267866"
    assert data["tipo_subasta"] == "JUDICIAL EN VÍA DE APREMIO"
    assert data["valor_subasta"] == "130560.00"
    assert data["deposito"] == "6528.00"
    assert data["bidding_state"] == "sin_pujas"
    assert data["highest_bid"] is None
    assert "La subasta no ha recibido pujas" in (data["bid_status"] or "")
    assert len(data["documents"]) == 2
    assert data["ai_report"] is not None
    assert data["ai_report"]["portal_id"] == "SUB-JA-2026-267866"
    assert data["ai_report"]["auction_value"] == "130560.00"
    assert "Agencia Estatal Boletín Oficial del Estado" in data["attribution"]


def test_api_get_auction_by_id():
    with patch("housefinder.offers.boe_portal.make_client", side_effect=mock_portal_client):
        resp = client.get("/boe/subastas/SUB-JA-2026-267866")
    assert resp.status_code == 200
    data = resp.json()
    assert data["portal_id"] == "SUB-JA-2026-267866"
    assert len(data["lots"]) == 1
    assert data["lots"][0]["bienes"][0]["referencia_catastral"] == "9402504VK3790C0005KT"


def test_api_scrape_invalid_id():
    resp = client.post(
        "/boe/subastas/scrape",
        json={
            "url_or_id": "invalido",
        },
    )
    assert resp.status_code == 422
    assert "identificador de subasta válido" in resp.json()["detail"]


def test_api_search_auctions():
    with patch("housefinder.offers.boe_portal.make_client", side_effect=mock_portal_client):
        resp = client.post(
            "/boe/subastas/search",
            json={
                "province": "28",
                "status": "EJ",
                "goods_type": "I",
                "page_hits": 20,
            },
        )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 38
    assert results[0]["portal_id"] == "SUB-JA-2024-232137"
    assert "JUZGADO 1 INSTANCIA 32" in results[0]["court"]


def test_api_search_auctions_all_spain_default():
    with patch("housefinder.offers.boe_portal.make_client", side_effect=mock_portal_client):
        resp = client.post(
            "/boe/subastas/search",
            json={},  # Sin provincia: por defecto busca en toda España
        )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 38


def test_sin_sesion_no_se_consulta_el_portal():
    app.dependency_overrides.pop(get_org)
    with patch("housefinder.offers.boe_portal.make_client") as make_client:
        resp = client.post("/boe/subastas/search", json={"province": "28"})
    assert resp.status_code in (401, 503)  # sin sesión, o sin base en la máquina de tests
    make_client.assert_not_called()
