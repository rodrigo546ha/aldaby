"""Avisos de subastas judiciales del BOE, sección IV (F4.3, ADR-0017), con el sumario real del
27/10/2026 reducido a tres avisos: dos de la Sección Civil de Madrid y uno de Alcañiz."""

from datetime import date
from pathlib import Path

import httpx
import pytest

from housefinder.offers.channels.boe_subastas import (
    BoeAuctions,
    load_court_seats,
    parse_notice,
)

FIXTURES = Path(__file__).parent / "fixtures" / "boe"
DAY = date(2026, 10, 27)
MADRID_TEXT = ("Sección Civil TI Madrid. Plz.n 31.- Anuncio de subasta judicial en vía de apremio "
               "con número de identificación 2459000000011924. Dirección electrónica: "
               "https://subastas.boe.es/ds.php?id=SUB-JA-2026-267866 Madrid, 19 de octubre de "
               "2026.- El Letrado de la Administración de Justicia.")


def test_datos_del_aviso():
    notice = parse_notice(MADRID_TEXT)
    assert notice.portal_id == "SUB-JA-2026-267866"
    assert notice.portal_url == "https://subastas.boe.es/ds.php?id=SUB-JA-2026-267866"
    assert notice.court == "Sección Civil TI Madrid. Plz.n 31"
    assert notice.kind == "judicial en vía de apremio"
    assert notice.procedure == "2459000000011924"


def test_un_aviso_sin_enlace_al_portal_no_es_una_subasta():
    assert parse_notice("Edicto. Se cita a don X a comparecer…") is None


def test_sedes_de_partidos_judiciales_de_madrid():
    seats = load_court_seats()
    assert len(seats.seats) == 21  # «21 partidos judiciales» (Comunidad de Madrid)
    assert seats.verified is False  # hasta que Rodrigo la compare con la relación oficial
    assert seats.matches("ALCALA DE HENARES") and seats.matches("Móstoles")
    assert not seats.matches("ALCAÑIZ") and not seats.matches("MADRIDEJOS")


def test_sedes_toda_espana():
    seats = load_court_seats(all_spain=True)
    assert seats.all_spain is True
    assert seats.matches("ALCAÑIZ")
    assert seats.matches("MADRID")
    assert seats.matches("BARCELONA")


def boe_client(seen: list[str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen.append(url)
        if url.endswith("/sumario/20261027"):
            return httpx.Response(200, content=(FIXTURES / "sumario-20261027-4.json").read_bytes())
        if url.endswith("/robots.txt"):
            return httpx.Response(200, content=(FIXTURES / "robots.txt").read_bytes())
        for ident in ("BOE-B-2026-35002", "BOE-B-2026-35003", "BOE-B-2026-34976"):
            if url.endswith(f"id={ident}"):
                page = FIXTURES / f"anuncio-{ident}.html"
                return httpx.Response(200, content=page.read_bytes())
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_solo_se_descargan_los_avisos_de_madrid():
    seen: list[str] = []
    channel = BoeAuctions([DAY], load_court_seats())
    items = list(channel.fetch(boe_client(seen)))
    assert sorted(i.external_id for i in items) == ["SUB-JA-2026-262811", "SUB-JA-2026-267866"]
    assert not any("34976" in url for url in seen)  # Alcañiz: ni se descarga
    assert all("subastas.boe.es" not in url for url in seen)  # el Portal nunca se pide
    offer = channel.parse(next(i for i in items if i.external_id == "SUB-JA-2026-267866"))[0]
    assert offer.title == "Subasta judicial en vía de apremio · Sección Civil TI Madrid. Plz.n 31"
    assert offer.url == "https://subastas.boe.es/ds.php?id=SUB-JA-2026-267866"
    assert offer.extraction_status == "no_aplica" and offer.kind == "anuncio"


def test_toda_espana_descarga_todos():
    seen: list[str] = []
    channel = BoeAuctions([DAY], load_court_seats(all_spain=True))
    items = list(channel.fetch(boe_client(seen)))
    assert sorted(i.external_id for i in items) == [
        "SUB-JA-2026-262811", "SUB-JA-2026-267510", "SUB-JA-2026-267866"]  # con Alcañiz
    assert channel.unparsed == []


# --- Contra la base -----------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_canal_de_punta_a_punta(migrated_database: str):
    from housefinder.offers.run import run_boe_auctions

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM watch_issues WHERE source = 'offers_boe_subastas'")
    # Con el filtro de sedes de Madrid; el ámbito nacional, en test_toda_espana_descarga_todos
    first = run_boe_auctions(migrated_database, boe_client([]), date(2026, 10, 28), days=2,
                             all_spain=False)
    assert first["items"] == 2 and first["unparsed"] == []
    assert first["court_seats_verified"] is False
    again = run_boe_auctions(migrated_database, boe_client([]), date(2026, 10, 28), days=2,
                             all_spain=False)
    assert again["items"] == 0  # los días ya leídos no se vuelven a pedir
    with psycopg.connect(migrated_database) as conn:
        rows = conn.execute(
            "SELECT external_id, kind, extraction_status, org_id, url, raw->'aviso'->>'court' "
            "FROM offers WHERE channel = 'boe_subastas_judiciales' ORDER BY external_id"
        ).fetchall()
    assert [r[0] for r in rows] == ["SUB-JA-2026-262811", "SUB-JA-2026-267866"]
    assert all(r[1:4] == ("anuncio", "no_aplica", None) for r in rows)
    assert rows[1][4] == "https://subastas.boe.es/ds.php?id=SUB-JA-2026-267866"
