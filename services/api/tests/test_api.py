from fastapi.testclient import TestClient

from housefinder.api.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_affordability_devuelve_cifras_trazables():
    resp = client.post(
        "/simulate/affordability",
        json={
            "net_monthly_income": 4000,
            "available_savings": 60000,
            "age": 30,
            "annual_rate": 0.03,
            "purchase_cost_rate": 0.10,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["max_price"]["value"] == "150000.00"
    assert body["max_price"]["formula"]
    assert body["max_price"]["sources"]
