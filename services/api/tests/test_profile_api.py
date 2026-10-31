"""API de la entrevista de perfil (F6.2, ADR-0020) contra la base temporal, con un modelo falso y
una clave maestra de prueba."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from housefinder.agent.extraction import Quoted
from housefinder.agent.llm import FakeLLMClient
from housefinder.agent.profiling import ProfileExtraction
from housefinder.api.deps import get_db, get_keys, get_llm, get_org
from housefinder.api.main import app
from housefinder.crypto.envelope import LocalKeyProvider
from housefinder.profiles import store

pytestmark = pytest.mark.db
psycopg = pytest.importorskip("psycopg")

NONE = Quoted(value=None, evidence=None)
EMPTY = dict(
    birth_year=NONE, age=NONE, residence=NONE, income=NONE, income_period=None,
    income_period_evidence=None, income_payments=NONE, debt=NONE, no_debt=False,
    no_debt_evidence=None, savings=NONE, children_birth_years=[], children_ages=[],
    no_children=False, no_children_evidence=None, goal=None, goal_evidence=None,
    horizon_years=NONE, risk_tolerance=None, risk_tolerance_evidence=None, management=None,
    management_evidence=None)
FIRST = "Nací en 1988, vivo en Madrid y gano 2.600 al mes"
SECOND = "No pago ningún préstamo y tengo 45.000 ahorrados"


def extraction(document: str) -> ProfileExtraction:
    """Lo que diría el modelo de cada respuesta de prueba."""
    if FIRST in document:
        return ProfileExtraction(**EMPTY | dict(
            birth_year=Quoted(value="1988", evidence="Nací en 1988"),
            residence=Quoted(value="Madrid", evidence="vivo en Madrid"),
            income=Quoted(value="2600", evidence="gano 2.600 al mes"), income_period="mes",
            income_period_evidence="al mes"))
    if SECOND in document:
        return ProfileExtraction(**EMPTY | dict(
            no_debt=True, no_debt_evidence="No pago ningún préstamo",
            savings=Quoted(value="45000", evidence="tengo 45.000 ahorrados")))
    return ProfileExtraction(**EMPTY)


@pytest.fixture
def setup(migrated_database: str):
    from housefinder.db.profiles import create_organization

    keys = LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")
    with psycopg.connect(migrated_database) as conn:
        orgs = [create_organization(conn, f"Perfil {uuid4()}", "particular") for _ in range(2)]
        conn.commit()
    current = {"org": orgs[0]}

    def db():
        with psycopg.connect(migrated_database) as conn:
            yield conn

    app.dependency_overrides.update({
        get_db: db, get_keys: lambda: keys, get_org: lambda: current["org"],
        get_llm: lambda: FakeLLMClient(respond=lambda _i, document, _o: extraction(document)),
    })
    yield TestClient(app), migrated_database, keys, orgs, current
    app.dependency_overrides.clear()


def test_entrevista_completa_hasta_el_perfil_cifrado(setup):
    client, database, keys, orgs, _ = setup
    started = client.post("/profile/interviews").json()
    assert started["next_question"]["field"] == "birth_year"
    interview = f"/profile/interviews/{started['id']}"

    after = client.post(f"{interview}/answers", json={"text": FIRST}).json()
    values = {f["field"]: f["value"] for f in after["fields"]}
    assert values["birth_year"] == "1988" and values["residence"] == "ES-13"
    assert values["net_monthly_income"] == "2600.00"
    assert after["next_question"]["field"] == "existing_monthly_debt"  # se salta lo ya dicho
    after = client.post(f"{interview}/answers", json={"text": SECOND}).json()
    assert after["complete"] is True and after["next_question"]["field"] == "descendant_birth_years"

    # Al retomar, la entrevista sigue donde estaba
    assert client.get("/profile/interviews/current").json()["id"] == started["id"]

    values = {f["field"]: f["value"] for f in after["fields"]}
    values["available_savings"] = "50000"  # el usuario corrige al confirmar
    confirmed = client.post(f"{interview}/confirm", json={"values": values})
    assert confirmed.status_code == 200
    profile_id = confirmed.json()["profile_id"]
    with psycopg.connect(database) as conn:
        profile = store.load(conn, keys, profile_id, orgs[0])
        stored = conn.execute("SELECT data_enc FROM profile_interviews WHERE id = %s",
                              (started["id"],)).fetchone()[0]
    assert str(profile.available_savings) == "50000" and profile.residence == "ES-13"
    assert b"1988" not in bytes(stored) and b"Madrid" not in bytes(stored)  # cifrado
    assert client.get(interview).json()["status"] == "confirmada"
    assert client.post(f"{interview}/answers", json={"text": "más"}).status_code == 409


def test_otra_organizacion_no_la_ve_y_se_puede_borrar(setup):
    client, _, _, orgs, current = setup
    started = client.post("/profile/interviews").json()
    interview = f"/profile/interviews/{started['id']}"
    current["org"] = orgs[1]
    assert client.get(interview).status_code == 404
    assert client.delete(interview).status_code == 404
    current["org"] = orgs[0]
    assert client.delete(interview).status_code == 204
    assert client.get(interview).status_code == 404


def test_confirmar_incompleto_dice_los_campos_sin_valores(setup):
    client, *_ = setup
    started = client.post("/profile/interviews").json()
    response = client.post(f"/profile/interviews/{started['id']}/confirm",
                           json={"values": {"birth_year": "1988", "residence": "Sevilla"}})
    assert response.status_code == 422
    assert "residence" in response.json()["detail"] and "Sevilla" not in response.json()["detail"]


def test_sin_clave_maestra_responde_503(migrated_database, tmp_path, monkeypatch):
    monkeypatch.setenv("HOUSEFINDER_KEYS_FILE", str(tmp_path / "no-existe.keys"))
    response = TestClient(app).post("/profile/interviews")
    assert response.status_code == 503 and "nueva-clave" in response.json()["detail"]
