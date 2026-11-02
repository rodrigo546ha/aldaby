"""Analítica sin cookies (F8.6, ADR-0042): qué se cuenta, qué no y el embudo."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from housefinder.analytics.funnel import funnel
from housefinder.analytics.visits import counts, normalize_path, referrer_host, visit


@pytest.mark.parametrize("raw, expected", [
    ("/", "/"), ("/simulador/", "/simulador"), ("/busqueda?x=1#a", "/busqueda"),
    ("/plan/3f1c9a2e-0000-4000-8000-000000000000", "/plan/[offer]"),  # nunca el identificador
    ("/legal/privacidad", "/legal/privacidad"),
    ("/api/auth/me", None), ("/cualquier-cosa", None), ("/plan/a/b", None),
    ("/legal/<script>", None),
])
def test_solo_rutas_conocidas_y_sin_identificadores(raw, expected):
    assert normalize_path(raw) == expected


def test_del_origen_solo_el_dominio():
    assert referrer_host("https://www.google.com/search?q=aldaby", "aldaby.es") == "google.com"
    assert referrer_host("https://aldaby.es/simulador", "aldaby.es") == ""  # el propio sitio
    assert referrer_host("javascript:alert(1)", "aldaby.es") == ""
    assert referrer_host(None, "aldaby.es") == ""
    seen = visit("/", "https://t.co/abc", "Newsletter", "aldaby.es")
    assert (seen.path, seen.referrer, seen.source) == ("/", "t.co", "newsletter")
    assert visit("/", None, "no vale!", None).source == ""


def test_quien_pide_no_ser_contado_y_los_robots_no_cuentan():
    browser = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Safari/537.36"
    assert counts({"user-agent": browser})
    assert not counts({"user-agent": browser, "sec-gpc": "1"})
    assert not counts({"user-agent": browser, "dnt": "1"})
    assert not counts({"user-agent": "Googlebot/2.1"})
    assert not counts({"user-agent": "curl/8.0"})


def test_embudo_con_la_parte_de_cada_paso():
    steps = funnel({"visits": 400, "waitlist": 40, "accounts": 10, "profiles": 8, "plans": 0})
    assert [s.count for s in steps] == [400, 40, 10, 8, 0]
    assert [s.of_previous for s in steps] == [None, Decimal("0.100"), Decimal("0.250"),
                                              Decimal("0.800"), Decimal("0.000")]
    empty = funnel({"visits": 0, "waitlist": 0, "accounts": 0, "profiles": 0, "plans": 0})
    assert all(s.of_previous is None for s in empty)  # sin dividir por cero


# --- Contra la base -----------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def client(migrated_database: str, monkeypatch):
    from fastapi.testclient import TestClient

    from housefinder.api.deps import API_ROLE, get_db
    from housefinder.api.main import app

    monkeypatch.delenv("HOUSEFINDER_DEV_ORG", raising=False)

    def db():
        with psycopg.connect(migrated_database) as conn:
            conn.execute(f"SET ROLE {API_ROLE}")
            yield conn

    app.dependency_overrides[get_db] = db
    try:
        yield TestClient(app, base_url="https://testserver",
                         headers={"User-Agent": "Mozilla/5.0 (prueba)"})
    finally:
        app.dependency_overrides.clear()


@pytest.mark.db
def test_recuento_sin_datos_de_la_persona(client, migrated_database: str):
    from housefinder.db.analytics import views

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM page_views")
    body = {"path": "/", "referrer": "https://www.google.com/x", "source": None}
    assert client.post("/analytics/event", json=body).status_code == 204
    assert client.post("/analytics/event", json=body).status_code == 204
    assert client.post("/analytics/event", json={"path": "/plan/123"}).status_code == 204
    # No se cuentan: ruta desconocida, petición con GPC o un robot. La respuesta es la misma.
    assert client.post("/analytics/event", json={"path": "/x"}).status_code == 204
    assert client.post("/analytics/event", json=body, headers={"Sec-GPC": "1"}).status_code == 204
    assert client.post("/analytics/event", json=body,
                       headers={"User-Agent": "Googlebot"}).status_code == 204
    with psycopg.connect(migrated_database) as conn:
        rows = conn.execute("SELECT path, referrer, source, views FROM page_views "
                            "ORDER BY path").fetchall()
        columns = {r[0] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'page_views'").fetchall()}
        today = rows and conn.execute("SELECT max(day) FROM page_views").fetchone()[0]
        assert views(conn, today, today, "/") == 2
    assert rows == [("/", "google.com", "", 2), ("/plan/[offer]", "", "", 1)]
    assert columns == {"day", "path", "referrer", "source", "views"}  # ni IP ni navegador


@pytest.mark.db
def test_pasos_del_embudo_desde_la_base(client, migrated_database: str):
    from test_access import account

    from housefinder.db.analytics import funnel_counts

    with psycopg.connect(migrated_database) as conn:
        before = funnel_counts(conn, date.today() - timedelta(days=1),
                               date.today() + timedelta(days=1))
    email = f"embudo-{uuid4().hex[:6]}@ejemplo.es"
    client.post("/waitlist", json={"email": email, "kind": "particular", "consent": True})
    client.post("/waitlist", json={"email": f"pro-{email}", "kind": "profesional",
                                   "consent": True})
    account(migrated_database, email, role="particular")
    with psycopg.connect(migrated_database) as conn:
        after = funnel_counts(conn, date.today() - timedelta(days=1),
                              date.today() + timedelta(days=1))
    assert after["waitlist"] - before["waitlist"] == 2
    assert after["waitlist_particulares"] - before["waitlist_particulares"] == 1
    assert after["accounts"] - before["accounts"] == 1
