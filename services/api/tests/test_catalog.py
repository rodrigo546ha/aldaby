"""Catálogo de ofertas e imagen de cada una (ADR-0054)."""

import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from PIL import Image

from housefinder.db.offers import CatalogRow
from housefinder.geo import photos as geo_photos
from housefinder.offers.catalog import catalog_item, channel_of, parcel_ref, place_name
from housefinder.offers.locate import load_provinces
from housefinder.offers.photos import PhotoCache, card_image

D = Decimal
PROVINCES = load_provinces()


def row(**kw) -> CatalogRow:
    base = dict(
        id=uuid4(), channel="boe_seccion_v", kind="lote", title="Lote 1 · Resolución…", url=None,
        asking_price=None, auction_min_bid=D("82161.23"), deposit_required=D("4804.75"),
        built_area_m2=None, address="Plaza Cuartel, 6", cadastral_ref=None,
        municipality_code="18041", lon=-3.9, lat=37.1,
        extracted={"property_type": "vivienda",
                   "municipality": {"value": "CACÍN", "status": "verificado"}},
        images=None, town=None, extraction_status="extraida", published_on=date(2026, 10, 29),
        parent_url="https://www.boe.es/diario_boe/txt.php?id=BOE-B-2026-1", deadline=None,
        source_name=None)
    base.update(kw)
    return CatalogRow(**base)


def test_lote_del_boe_con_titulo_corto_y_lugar():
    item = catalog_item(row(), PROVINCES)
    assert item.channel == "subasta_administrativa" and item.auction
    assert item.title == "Vivienda en Cacín"
    assert item.place == "Cacín · Granada"  # provincia del código INE 18
    assert item.price == D("82161.23") and item.price_kind == "valor_subasta"
    assert item.deposit == D("4804.75")
    assert item.source_name == "BOE" and item.source_url.startswith("https://www.boe.es")
    assert item.original_title == "Lote 1 · Resolución…"


@pytest.mark.parametrize("title, channel", [
    ("Subasta judicial · CALLE MERCURIO 36", "subasta_judicial"),
    ("Subasta administrativa · CL LAS PALMAS 59", "subasta_administrativa"),
    ("Subasta notarial · Calle Mayor 1", "subasta_notarial"),
])
def test_origen_de_la_subasta_del_portal(title, channel):
    assert channel_of(row(channel="boe_subasta_portal", title=title)) == channel


def test_ventas_directas_agencias_y_anuncios_propios():
    assert channel_of(row(channel="patrimonio_estado")) == "venta_directa"
    assert channel_of(row(channel="feed_agencia", kind="anuncio")) == "agencia"
    assert channel_of(row(channel="url_usuario", kind="enlace")) == "tu_anuncio"


def test_subasta_del_portal_con_fin_estado_y_posesion_sin_nombres():
    item = catalog_item(row(
        channel="boe_subasta_portal", title="Subasta judicial · CALLE X", municipality_code="28079",
        town="MADRID", extracted={"property_type": "vivienda", "portal": {
            "status": "Celebrándose - [Conclusión prevista: 09/11/2026 a las 18:00:00]",
            "concludes": "09/11/2026 a las 18:00:00", "habitual_residence": "Sí",
            "possession": "No consta (INSCRITA A FAVOR DE FULANA DE TAL)"}}), PROVINCES)
    assert item.title == "Vivienda en Madrid" and item.place == "Madrid"  # sin repetir provincia
    assert item.ends_on == date(2026, 11, 9)
    assert item.auction_state == "Celebrándose"
    assert item.habitual_residence is True
    assert item.possession is None  # «No consta», y el paréntesis nunca sale


def test_posesion_que_consta_sin_parentesis():
    item = catalog_item(row(extracted={"portal": {"possession": "Ocupado (por D. Fulano)"}}),
                        PROVINCES)
    assert item.possession == "Ocupado"


def test_anuncio_pegado_usa_lo_confirmado():
    item = catalog_item(row(
        channel="url_usuario", kind="enlace", title="Piso luminoso", asking_price=D("235000"),
        auction_min_bid=None, deposit_required=None, municipality_code=None,
        extraction_status="extraida", images=["https://img.example/1.jpg", "http://x/2.jpg"],
        extracted={"listing": {"property_type": "vivienda"}, "confirmed": {"fields": {
            "municipality": {"value": "Getafe", "origin": "usuario"},
            "built_area_m2": {"value": "85", "origin": "usuario"}}}}), PROVINCES)
    assert item.channel == "tu_anuncio" and not item.auction
    assert item.title == "Vivienda en Getafe"
    assert item.price == D("235000") and item.price_kind == "precio"
    assert item.built_area_m2 == D("85")
    assert item.status == "por_confirmar"
    assert item.images == ("https://img.example/1.jpg",)  # solo https


@pytest.mark.parametrize("text, expected", [
    ("ALCOLEA DEL PINAR (Guadalajara)", "Alcolea del Pinar"),
    ("TORRES TORRES", "Torres Torres"),
    ("Santa María de la Alameda", "Santa María de la Alameda"),
    ("", None),
])
def test_nombre_de_lugar(text, expected):
    assert place_name(text) == expected


def test_referencia_de_parcela_para_la_fachada():
    assert parcel_ref(row(cadastral_ref="8930637VK4783B0020DK")) == "8930637VK4783B"
    assert parcel_ref(row(extracted={"cadastral_ref": {
        "value": "24142a50100014 0000RX", "status": "verificado"}})) == "24142A50100014"
    assert parcel_ref(row(cadastral_ref="123")) is None


# --- Imágenes -------------------------------------------------------------------------------


def jpeg(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (40, 90, 60)).save(buffer, "JPEG")
    return buffer.getvalue()


def test_imagen_de_tarjeta_reducida_y_con_marca():
    out = card_image(jpeg(1024, 768), mark_center=True)
    assert out is not None
    with Image.open(io.BytesIO(out)) as img:
        assert img.size == (640, 480)
        assert img.getpixel((320, 240))[0] > 150  # el punto de latón en el centro
    assert card_image(b"no es una imagen") is None


def test_cache_guarda_tambien_que_no_hay_foto():
    now = [0.0]
    cache = PhotoCache(size=2, seconds=10, clock=lambda: now[0])
    calls = []

    def load(value):
        def inner():
            calls.append(value)
            return value
        return inner

    assert cache.get("a", load(None)) is None
    assert cache.get("a", load(b"x")) is None and calls == [None]  # de la caché
    now[0] = 11
    assert cache.get("a", load(b"x")) == b"x"  # caducada
    cache.get("b", load(b"b"))
    cache.get("c", load(b"c"))
    assert cache.get("a", load(b"otra")) == b"otra"  # la más antigua salió


def test_caja_de_la_ortofoto_centrada():
    south, west, north, east = geo_photos.aerial_bbox(-3.6, 40.4)
    assert (south + north) / 2 == pytest.approx(40.4)
    assert (west + east) / 2 == pytest.approx(-3.6)
    # 160 m de alto y 256 m de ancho (640 × 400 px)
    assert (north - south) * 111_320 == pytest.approx(160)
    assert (east - west) * 111_320 * 0.7615 == pytest.approx(256, rel=0.01)


def test_fachada_vacia_es_none():
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=b"", headers={"Content-Type": "image/jpeg"})))
    assert geo_photos.facade(client, "24142A50100014") is None


# --- Con base de datos ----------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")
from test_offer_valuation import api, confirmed_offer, database  # noqa: E402, F401


@pytest.mark.db
def test_catalogo_con_los_anuncios_propios_y_no_los_ajenos(api, database):  # noqa: F811
    from housefinder.db.profiles import create_organization

    http, org = api
    mine = confirmed_offer(database, org, "venta", "150000")
    with psycopg.connect(database) as conn:
        other = create_organization(conn, f"Otra {uuid4()}", "particular")
        conn.commit()
    theirs = confirmed_offer(database, other, "venta", "99000")
    resp = http.get("/offers/catalog")
    assert resp.status_code == 200
    by_id = {o["offer_id"]: o for o in resp.json()}
    assert str(mine) in by_id and str(theirs) not in by_id
    item = by_id[str(mine)]
    assert item["channel"] == "tu_anuncio" and item["title"] == "Vivienda en Villaprueba"
    assert item["price"] == "150000" and item["status"] == "publicada"
    assert item["photos"] == ["aerea"]  # ubicada y sin referencia catastral


@pytest.mark.db
def test_foto_de_una_oferta(api, database):  # noqa: F811
    from housefinder.api.deps import get_photo_client
    from housefinder.api.main import app

    http, org = api
    mine = confirmed_offer(database, org, "venta", "150000")
    asked = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.host)
        return httpx.Response(200, content=jpeg(640, 400), headers={"Content-Type": "image/jpeg"})

    app.dependency_overrides[get_photo_client] = lambda: httpx.Client(
        transport=httpx.MockTransport(handler))
    resp = http.get(f"/offers/{mine}/photo/aerea")
    assert resp.status_code == 200 and resp.headers["content-type"] == "image/jpeg"
    assert "CC BY 4.0" in resp.headers["x-attribution"]
    assert asked == ["www.ign.es"]
    assert http.get(f"/offers/{mine}/photo/fachada").status_code == 404  # sin referencia
    assert http.get(f"/offers/{uuid4()}/photo/aerea").status_code == 404


def test_direccion_en_mayusculas_se_escribe_normal():
    item = catalog_item(row(address="CALLE MERCURIO 36, CUARTO DERECHA"), PROVINCES)
    assert item.address == "Calle Mercurio 36, Cuarto Derecha"
    item = catalog_item(row(address="CALLE NUESTRA SEÑORA DE LA LUZ Nº 36"), PROVINCES)
    assert item.address == "Calle Nuestra Señora de la Luz Nº 36"
    assert catalog_item(row(address="Plaza Cuartel, 6"), PROVINCES).address == "Plaza Cuartel, 6"


@pytest.mark.db
def test_catalogo_sin_las_ventas_terminadas(api, database):  # noqa: F811
    http, _ = api
    ended = catalog_item(row(deadline="30/10/2020"), PROVINCES)
    assert ended.ends_on == date(2020, 10, 30)
    with patch("housefinder.api.offers.catalog_rows", return_value=[
            row(deadline="30/10/2020"), row(deadline="30/10/2099")]):
        body = http.get("/offers/catalog").json()
    assert [o["ends_on"] for o in body] == ["2099-10-30"]
