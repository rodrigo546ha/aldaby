"""Tests del scraper del Portal de Subastas del BOE (subastas.boe.es).

Comprueba el parseo de todas las pestañas (ver=1 a ver=5), subastas de lote único, subastas con
múltiples lotes, búsqueda avanzada y la conversión a ofertas normalizadas.
"""

from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from housefinder.offers.boe_portal import (
    ScrapedAuction,
    build_auction_url,
    extract_portal_id,
    parse_auction_tab1,
    parse_auction_tab2,
    parse_auction_tab3,
    parse_auction_tab4,
    parse_auction_tab5,
    parse_money,
    parse_search_results,
    scrape_auction,
    search_boe_auctions,
    to_normalized_offers,
)

FIXTURES = Path(__file__).parent / "fixtures" / "boe" / "portal"


def test_extract_portal_id():
    assert extract_portal_id("SUB-JA-2026-267866") == "SUB-JA-2026-267866"
    assert extract_portal_id("sub-ja-2026-267866") == "SUB-JA-2026-267866"
    assert (
        extract_portal_id("https://subastas.boe.es/ds.php?id=SUB-JA-2026-267866")
        == "SUB-JA-2026-267866"
    )
    assert (
        extract_portal_id(
            "https://subastas.boe.es/detalleSubasta.php?idSub=SUB-AT-2026-26R2886001552&ver=1"
        )
        == "SUB-AT-2026-26R2886001552"
    )

    with pytest.raises(ValueError, match="No se encontró un identificador"):
        extract_portal_id("https://subastas.boe.es/index.php")


def test_parse_money():
    assert parse_money("130.560,00 €") == Decimal("130560.00")
    assert parse_money("130560.00") == Decimal("130560.00")
    assert parse_money("29.766,05 €") == Decimal("29766.05")
    assert parse_money("0,00 €") == Decimal("0.00")
    assert parse_money("Sin puja mínima") is None
    assert parse_money("No consta") is None
    assert parse_money(None) is None


def test_parse_tab1_notice_and_documents():
    html_content = (FIXTURES / "single_ver1.html").read_text(encoding="utf-8")
    notice = parse_auction_tab1(html_content, "SUB-JA-2026-267866")

    assert notice.portal_id == "SUB-JA-2026-267866"
    assert notice.tipo_subasta == "JUDICIAL EN VÍA DE APREMIO"
    assert notice.cuenta_expediente == "2459 0000 00 0119 24"
    assert notice.anuncio_boe == "BOE-B-2026-35002"
    assert notice.cantidad_reclamada == Decimal("29766.05")
    assert notice.valor_subasta == Decimal("130560.00")
    assert notice.tasacion == Decimal("0.00")
    assert notice.puja_minima == Decimal("200.00")
    assert notice.tramos_entre_pujas == Decimal("2620.00")
    assert notice.importe_deposito == Decimal("6528.00")

    # Documentos adjuntos
    assert len(notice.documents) == 2
    assert notice.documents[0].title == "EDICTO"
    assert notice.documents[0].id_doc == "1-0a54b03f7ea893a2640bd31f452993bf"
    assert (
        "verDocumento.php?idSub=SUB-JA-2026-267866&idDoc=1-0a54b03f7ea893a2640bd31f452993bf"
        in notice.documents[0].url
    )

    assert notice.documents[1].title == "CERTIFICACION REGISTRAL DOMINIO Y CARGAS"
    assert notice.documents[1].id_doc == "2-185b453923336e8ba027ff73b922a322"


def test_parse_tab2_managing_authority():
    html_content = (FIXTURES / "single_ver2.html").read_text(encoding="utf-8")
    auth = parse_auction_tab2(html_content)

    assert auth.codigo == "2807942031"
    assert auth.descripcion == "Sección Civil TI Madrid. Plz.n 31"
    assert "POETA JOAN MARAGALL" in (auth.direccion or "")
    assert auth.telefono == "914932843"
    assert auth.fax == "914932844"


def test_parse_tab3_single_lot():
    html_content = (FIXTURES / "single_ver3.html").read_text(encoding="utf-8")
    lots = parse_auction_tab3(html_content)

    assert len(lots) == 1
    lot = lots[0]
    assert lot.lote_num == 1
    assert len(lot.bienes) == 1

    bien = lot.bienes[0]
    assert bien.bien_num == 1
    assert bien.tipo_bien == "Inmueble (Vivienda)"
    assert bien.idufir == "28177001763770"
    assert bien.referencia_catastral == "9402504VK3790C0005KT"
    assert "Fermín Donaire" in (bien.direccion or "")
    assert bien.codigo_postal == "28008"
    assert bien.localidad == "MADRID"
    assert bien.provincia == "Madrid"
    assert bien.vivienda_habitual == "No"
    assert bien.situacion_posesoria == "No consta"
    assert "Finca Registral 23778" in (bien.inscripcion_registral or "")


def test_parse_tab3_multi_lot():
    html_lote1 = (FIXTURES / "multi_ver3_lote1.html").read_text(encoding="utf-8")
    html_lote2 = (FIXTURES / "multi_ver3_lote2.html").read_text(encoding="utf-8")

    lots = parse_auction_tab3(html_lote1, lot_subpages={1: html_lote1, 2: html_lote2})
    assert len(lots) == 4

    lote1 = lots[0]
    assert lote1.lote_num == 1
    assert "FINCA 32216" in (lote1.titulo or "")
    assert lote1.valor_subasta == Decimal("198698.50")
    assert lote1.tasacion == Decimal("198698.50")
    assert lote1.deposito == Decimal("9934.93")
    assert lote1.puja_minima is None  # 'Sin puja mínima'
    assert lote1.tramos is None  # 'Sin tramos'

    assert len(lote1.bienes) == 1
    b1 = lote1.bienes[0]
    assert b1.localidad == "AVILES"
    assert b1.provincia == "Asturias"
    assert b1.situacion_posesoria == "Ocupante desconocido"

    lote2 = lots[1]
    assert lote2.lote_num == 2
    assert "32220" in (lote2.titulo or "")
    assert lote2.valor_subasta == Decimal("231870.20")


def test_parse_tab4_creditors():
    html_content = (FIXTURES / "single_ver4.html").read_text(encoding="utf-8")
    creds = parse_auction_tab4(html_content)

    assert len(creds) == 1
    assert creds[0].nombre == "FINANCIERA CARRION S.A. E.F.C"
    assert creds[0].nif == "A28216778"
    assert creds[0].provincia == "Madrid"


def test_parse_tab5_bids():
    html_content = (FIXTURES / "single_ver5.html").read_text(encoding="utf-8")
    bid, status, state, lot_bids = parse_auction_tab5(html_content)

    assert bid is None
    assert status is not None
    assert "La subasta no ha recibido pujas" in status
    assert state == "sin_pujas"
    assert lot_bids == {}


def test_parse_tab5_bids_states():
    # 1. Requiere usuario registrado
    login_html = (
        '<div id="idBloqueDatos8">'
        '<p class="centrador">La subasta ha recibido alguna puja. '
        "Para ver su importe debe acceder como usuario registrado.</p>"
        '</div><div class="bloqueBotones">'
    )
    bid, status, state, lot_bids = parse_auction_tab5(login_html)
    assert bid is None
    assert state == "con_pujas_requiere_login"

    # 2. Puja secreta
    secret_html = (
        '<div id="idBloqueDatos8">'
        '<p class="centrador">La puja máxima de la subasta es secreta.</p>'
        '</div><div class="bloqueBotones">'
    )
    bid, status, state, lot_bids = parse_auction_tab5(secret_html)
    assert bid is None
    assert state == "puja_secreta"

    # 3. Puja pública visible
    public_html = (
        '<div id="idBloqueDatos8">'
        '<p class="centrador">145.200,00 €</p>'
        '</div><div class="bloqueBotones">'
    )
    bid, status, state, lot_bids = parse_auction_tab5(public_html)
    assert bid == Decimal("145200.00")
    assert state == "puja_publica"

    # 4. Tabla de múltiples lotes
    multi_html = """<div id="idBloqueDatos8">
    <table>
      <thead>
        <tr><th id="lote">Lote</th><th id="cantidad">Importe</th></tr>
      </thead>
      <tbody>
        <tr><td headers="lote">1</td><td headers="cantidad">Sin puja</td></tr>
        <tr><td headers="lote">2</td>
            <td headers="cantidad">Con puja (inicie sesión para consultar el importe)</td>
        </tr>
      </tbody>
    </table>
    </div><div class="bloqueBotones">"""
    bid, status, state, lot_bids = parse_auction_tab5(multi_html)
    assert bid is None
    assert state == "con_pujas_requiere_login"
    assert len(lot_bids) == 2
    assert lot_bids[1]["state"] == "sin_pujas"
    assert lot_bids[2]["state"] == "con_pujas_requiere_login"


def test_parse_search_results():
    html_content = (FIXTURES / "search_madrid.html").read_text(encoding="utf-8")
    results = parse_search_results(html_content)

    assert len(results) == 38
    first = results[0]
    assert first.portal_id == "SUB-JA-2024-232137"
    assert "JUZGADO 1 INSTANCIA 32" in (first.court or "")
    assert first.procedure == "0010/18"
    assert "Celebrándose" in (first.status or "")
    assert first.conclusion_date is not None
    assert "09/11/2026" in first.conclusion_date


def test_to_normalized_offers_single_lot():
    html_v1 = (FIXTURES / "single_ver1.html").read_text(encoding="utf-8")
    notice = parse_auction_tab1(html_v1, "SUB-JA-2026-267866")
    lots = parse_auction_tab3((FIXTURES / "single_ver3.html").read_text(encoding="utf-8"))

    auction = ScrapedAuction(
        portal_id="SUB-JA-2026-267866",
        portal_url=build_auction_url("SUB-JA-2026-267866"),
        notice=notice,
        authority=None,
        lots=lots,
        creditors=[],
        highest_bid=None,
        bid_status="Sin pujas",
    )

    offers = to_normalized_offers(auction)
    assert len(offers) == 1
    offer = offers[0]
    assert offer.external_id == "SUB-JA-2026-267866"
    # Un lote público sin precio pedido: el plan lo trata como subasta y el simulador de puja
    # parte del valor de subasta, no de la puja mínima (200 €) (ADR-0053)
    assert offer.kind == "lote"
    assert offer.asking_price is None
    assert offer.auction_min_bid == Decimal("130560.00")
    assert offer.deposit_required == Decimal("6528.00")
    assert offer.cadastral_ref == "9402504VK3790C0005KT"
    assert offer.municipality == "MADRID"
    assert offer.extracted["property_type"] == "vivienda"
    assert offer.built_area_m2 is None  # sin el Catastro, sin superficie
    assert offer.title.startswith("Subasta judicial · ")


def test_scrape_auction_offline_mock():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for ver in range(1, 6):
            if f"ver={ver}" in url:
                content = (FIXTURES / f"single_ver{ver}.html").read_bytes()
                return httpx.Response(200, content=content)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    auction = scrape_auction(client, "SUB-JA-2026-267866")

    assert auction.portal_id == "SUB-JA-2026-267866"
    assert auction.notice.valor_subasta == Decimal("130560.00")
    assert auction.authority is not None
    assert "Sección Civil TI Madrid" in (auction.authority.descripcion or "")
    assert len(auction.lots) == 1
    assert len(auction.notice.documents) == 2
    assert "ver1" in auction.raw_html


def test_search_boe_auctions_defaults_to_all_spain():
    posted_data: list[str] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        posted_data.append(request.content.decode("utf-8"))
        content = (FIXTURES / "search_madrid.html").read_bytes()
        return httpx.Response(200, content=content)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    results = search_boe_auctions(client)

    assert len(results) == 38
    assert len(posted_data) == 1
    # Cuando province es vacía, busca en toda España (dato[8] vacío)
    assert "dato%5B8%5D=&" in posted_data[0] or "dato%5B8%5D=" in posted_data[0]


def test_search_boe_auctions_pagination():
    requests_log: list[str] = []

    page1_html = (
        (FIXTURES / "search_madrid.html").read_text(encoding="utf-8")
        + '<a href="./subastas_ava.php?accion=Mas&amp;id_busqueda=TOKEN123">'
        "<abbr title='Página'>Pág.</abbr> siguiente</a>"
    )
    page2_html = (
        '<ul class="resultados-busqueda">'
        '<li class="resultado-busqueda">'
        '<a href="detalleSubasta.php?idSub=SUB-JA-2026-999999&amp;ver=1">Lote</a>'
        "<h4>JUZGADO DE PRUEBA</h4>"
        "<p>Celebrándose</p>"
        "</li>"
        "</ul>"
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requests_log.append(url)
        if "TOKEN123" in url:
            return httpx.Response(200, content=page2_html.encode("utf-8"))
        return httpx.Response(200, content=page1_html.encode("utf-8"))

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    results = search_boe_auctions(client, max_pages=2)

    assert len(results) == 39
    assert len(requests_log) == 2
    assert any("TOKEN123" in url for url in requests_log)
