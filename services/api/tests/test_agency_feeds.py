"""Feeds de agencias en formato Kyero v3 (ADR-0038), con un feed inventado."""

import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from housefinder.offers.channels import agency_feed
from housefinder.offers.channels.agency_feed import (
    AgencyFeed,
    FeedUnavailable,
    parse_feed,
    property_type,
)

FEED = (Path(__file__).parent / "fixtures" / "feeds" / "agencia-inventada.xml").read_bytes()
URL = "https://usuario:secreto@crm.example/exportar/kyero.xml?token=abc"


def feed_client(seen: list[str], content: bytes = FEED, robots: str = "",
                status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots) if robots else httpx.Response(404)
        return httpx.Response(status, content=content)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_solo_las_ventas_en_euros_de_espana_y_de_propiedad_entera():
    kept, skipped = parse_feed(FEED)
    assert [raw["id"] for raw in kept] == ["P-001", "P-003", "P-005"]
    assert skipped == {"alquiler": 1, "otra_moneda": 1, "propiedad_parcial": 1,
                       "fuera_de_espana": 1}


def test_no_se_guardan_contactos_ni_fotos():
    raw = parse_feed(FEED)[0][0]
    assert not {"email", "contact_number", "whatsapp_number"} & set(raw)
    assert raw["images"] == 3  # cuántas, no cuáles
    assert "fotos" not in str(raw)
    assert raw["catastral"] == "1234567VK3613S0001AB"  # sin el espacio


@pytest.mark.parametrize("kyero, expected", [
    ("Piso", "vivienda"), ("Apartment", "vivienda"), ("Town House", "vivienda"),
    ("Ático", "vivienda"), ("Country house", "vivienda"), ("Finca", "vivienda"),
    ("Warehouse", "local"), ("Local comercial", "local"), ("Garage", "garaje"),
    ("Plaza de garaje", "garaje"), ("Plot", "suelo"), ("Finca rústica", "rustica"),
    ("Office", "oficina"), ("Edificio", "edificio"), ("Hotel", "otro"), ("", "otro"),
])
def test_tipo_de_inmueble(kyero: str, expected: str):
    assert property_type(kyero) == expected


def test_oferta_normalizada():
    seen: list[str] = []
    feed_id = uuid4()
    channel = AgencyFeed(feed_id, URL)
    items = list(channel.fetch(feed_client(seen)))
    assert [i.external_id for i in items] == [f"{feed_id}:P-001", f"{feed_id}:P-003",
                                             f"{feed_id}:P-005"]
    piso = channel.parse(items[0])[0]
    assert piso.kind == "anuncio" and piso.extraction_status == "no_aplica"
    assert piso.title == "Piso en Getafe"
    assert piso.url == "https://agencia-inventada.example/es/p-001"
    assert piso.asking_price == Decimal("189000") and piso.built_area_m2 == Decimal("85")
    assert piso.cadastral_ref == "1234567VK3613S0001AB"
    assert (piso.lon, piso.lat) == (-3.7329, 40.3057)
    assert piso.municipality == "Getafe" and piso.province == "Madrid"
    assert piso.description == "Piso luminoso de tres dormitorios"  # la española primero
    assert piso.published_on == date(2026, 10, 30)
    assert piso.extracted["property_type"] == "vivienda"
    assert piso.extracted["feed"]["beds"] == "3"
    local = channel.parse(items[1])[0]
    assert local.extracted["property_type"] == "local" and local.lon is None
    atico = channel.parse(items[2])[0]
    assert not atico.locatable  # sin coordenada ni referencia: no se puede ubicar
    assert channel.skipped["alquiler"] == 1


def test_la_url_no_sale_ni_en_el_robots_ni_en_la_representacion():
    seen: list[str] = []
    channel = AgencyFeed(uuid4(), URL)
    list(channel.fetch(feed_client(seen)))
    assert seen[0] == "https://crm.example/robots.txt"
    assert "secreto" not in repr(channel)


def test_se_respeta_el_robots_txt_del_crm():
    seen: list[str] = []
    channel = AgencyFeed(uuid4(), URL)
    with pytest.raises(FeedUnavailable, match="robots"):
        list(channel.fetch(feed_client(seen, robots="User-agent: *\nDisallow: /exportar/\n")))
    assert len(seen) == 1  # el feed ni se pide


def test_un_feed_que_falla_no_devuelve_nada():
    with pytest.raises(FeedUnavailable, match="no se pudo descargar"):
        list(AgencyFeed(uuid4(), URL).fetch(feed_client([], status=500)))
    with pytest.raises(FeedUnavailable, match="XML no válido"):
        list(AgencyFeed(uuid4(), URL).fetch(feed_client([], content=b"<root><property>")))


def test_no_se_leen_feeds_con_doctype_ni_demasiado_grandes(monkeypatch: pytest.MonkeyPatch):
    bomb = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><root>&a;</root>'
    with pytest.raises(FeedUnavailable, match="DOCTYPE"):
        parse_feed(bomb)
    monkeypatch.setattr(agency_feed, "MAX_BYTES", 1000)
    with pytest.raises(FeedUnavailable, match="pasa de"):
        list(AgencyFeed(uuid4(), URL).fetch(feed_client([])))


def test_coordenadas_fuera_de_espana_no_se_usan():
    raw = parse_feed(FEED)[0][0]
    item = agency_feed.RawItem("x", "", None, {**raw, "latitude": "48.85", "longitude": "2.35"})
    offer = AgencyFeed(uuid4(), URL).parse(item)[0]
    assert offer.lon is None and offer.lat is None


# --- Contra la base -----------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def keys():
    from housefinder.crypto.envelope import LocalKeyProvider

    return LocalKeyProvider({"prueba": os.urandom(32)}, "prueba")


def new_org(conninfo: str) -> object:
    from housefinder.db.profiles import create_organization

    with psycopg.connect(conninfo, autocommit=True) as conn:
        return create_organization(conn, f"Agencia {uuid4()}", "profesional")


def register_feed(conninfo: str, keys, org_id, scope: str = "organizacion") -> object:
    from housefinder.feeds.registry import register

    with psycopg.connect(conninfo) as conn:
        feed_id = register(conn, keys, org_id, "Agencia Inventada", URL, scope,
                           date(2026, 11, 1), "Contrato de alta de prueba")
        conn.commit()
    return feed_id


@pytest.mark.db
def test_alta_con_la_url_cifrada(migrated_database: str, keys):
    from housefinder.feeds.registry import FeedError, active_feeds, register

    org_id = new_org(migrated_database)
    feed_id = register_feed(migrated_database, keys, org_id)
    with psycopg.connect(migrated_database) as conn:
        stored = conn.execute("SELECT url_enc FROM agency_feeds WHERE id = %s",
                              (feed_id,)).fetchone()[0]
        assert b"secreto" not in bytes(stored) and b"crm.example" not in bytes(stored)
        feed = next(f for f in active_feeds(conn, keys)[0] if f.id == feed_id)
        assert feed.url == URL and "secreto" not in repr(feed)
        # Un feed cifrado con una clave que ya no está no impide leer los demás.
        from housefinder.crypto.envelope import LocalKeyProvider

        lost = LocalKeyProvider({"perdida": os.urandom(32)}, "perdida")
        orphan = register(conn, lost, org_id, "Otra agencia", URL, "todos", date(2026, 11, 1),
                          "Contrato")
        readable, locked = active_feeds(conn, keys)
        assert orphan in locked and feed_id in {f.id for f in readable}
        for bad in [dict(scope="publico"), dict(url="ftp://crm.example/feed.xml"),
                    dict(consent_on=date(2099, 1, 1)), dict(consent_ref="  ")]:
            args = {"url": URL, "scope": "todos", "consent_on": date(2026, 11, 1),
                    "consent_ref": "Contrato", **bad}
            with pytest.raises(FeedError):
                register(conn, keys, org_id, "Agencia", args["url"], args["scope"],
                         args["consent_on"], args["consent_ref"])


@pytest.mark.db
def test_foto_completa_alta_cambio_retirada_y_vuelta(migrated_database: str, keys):
    from housefinder.db.offers import searchable_offer
    from housefinder.feeds.registry import active_feeds
    from housefinder.feeds.run import run_feed

    org_id, other = new_org(migrated_database), new_org(migrated_database)
    feed_id = register_feed(migrated_database, keys, org_id)
    with psycopg.connect(migrated_database) as conn:
        feed = next(f for f in active_feeds(conn, keys)[0] if f.id == feed_id)

        def offers() -> dict[str, tuple]:
            rows = conn.execute(
                "SELECT external_id, extraction_status, org_id, asking_price, property_id, id "
                "FROM offers WHERE channel = 'feed_agencia' AND source_id = %s",
                (f"feed-agencia-{feed_id}",)).fetchall()
            return {r[0].split(":")[1]: r[1:] for r in rows}

        first = run_feed(conn, feed_client([]), feed, lambda offer: None)
        assert (first["listings"], first["new"], first["located"]) == (3, 3, 1)
        assert first["without_location"] == 1 and first["skipped"]["alquiler"] == 1
        stored = offers()
        assert {k: v[:3] for k, v in stored.items()} == {
            "P-001": ("no_aplica", org_id, Decimal("189000")),
            "P-003": ("no_aplica", org_id, Decimal("120000")),
            "P-005": ("no_aplica", org_id, Decimal("215000"))}
        assert stored["P-001"][3] is not None  # ubicado por la coordenada del feed
        # Solo lo ve la organización del feed.
        assert searchable_offer(conn, stored["P-001"][4], org_id)
        assert not searchable_offer(conn, stored["P-001"][4], other)

        # Baja de precio de P-001 y P-003 desaparece: se pone al día y se retira.
        changed = FEED.replace(b"<price>189000</price>", b"<price>179000</price>") \
            .replace(b"<id>P-003</id>", b"<id>P-099</id>")
        second = run_feed(conn, feed_client([], content=changed), feed, lambda offer: None)
        assert (second["new"], second["changed"], second["retired"]) == (1, 1, 1)
        after = offers()
        assert after["P-001"][2] == Decimal("179000")
        assert after["P-001"][3] == stored["P-001"][3]  # no se movió: sigue en su inmueble
        assert after["P-003"][0] == "retirada" and after["P-003"][3] is None

        # Vuelve P-003: se reactiva.
        third = run_feed(conn, feed_client([]), feed, lambda offer: None)
        assert third["retired"] == 1  # ahora falta P-099
        assert offers()["P-003"][0] == "no_aplica"

        # Si el feed falla, no se retira nada.
        failed = run_feed(conn, feed_client([], status=500), feed, lambda offer: None)
        assert "error" in failed
        assert offers()["P-001"][0] == "no_aplica"
        report = conn.execute("SELECT last_report FROM agency_feeds WHERE id = %s",
                              (feed_id,)).fetchone()[0]
        assert "secreto" not in str(report)


@pytest.mark.db
def test_alcance_todos_es_oferta_publica(migrated_database: str, keys):
    from housefinder.db.offers import searchable_offer
    from housefinder.feeds.registry import active_feeds
    from housefinder.feeds.run import run_feed

    org_id, other = new_org(migrated_database), new_org(migrated_database)
    feed_id = register_feed(migrated_database, keys, org_id, scope="todos")
    with psycopg.connect(migrated_database) as conn:
        feed = next(f for f in active_feeds(conn, keys)[0] if f.id == feed_id)
        run_feed(conn, feed_client([]), feed, lambda offer: None)
        row = conn.execute(
            "SELECT id, org_id FROM offers WHERE channel = 'feed_agencia' AND external_id = %s",
            (f"{feed_id}:P-001",)).fetchone()
        source = conn.execute("SELECT license FROM sources WHERE id = %s",
                              (f"feed-agencia-{feed_id}",)).fetchone()[0]
    assert row[1] is None
    with psycopg.connect(migrated_database) as conn:
        assert searchable_offer(conn, row[0], other)
    assert "todos los usuarios de Aldaby" in source and "Contrato de alta de prueba" in source


@pytest.mark.db
def test_sin_feeds_el_trabajo_no_pide_las_claves(migrated_database: str):
    from housefinder.feeds.run import run_feeds

    def no_keys():
        raise AssertionError("no debería cargar las claves")

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM agency_feeds")
    assert run_feeds(migrated_database, feed_client([]), no_keys) == {"feeds": [], "withdrawn": 0}
