"""Enlace pegado por el usuario (F4.1, ADR-0015) con un anuncio sintético y sin red: la descarga
es una sola y educada, la red interna está vetada, lo extraído se comprueba contra su cita y solo lo
que el usuario confirma pasa a la oferta."""

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from conftest import add_section

from housefinder.agent.extraction import ListingExtraction, Quoted, check_listing
from housefinder.agent.llm import FakeLLMClient, LLMOutputError
from housefinder.offers.html_text import page_text
from housefinder.offers.link import LinkRefused, check_url, fetch_listing

HTML = (Path(__file__).parent / "fixtures" / "enlaces" / "anuncio-sintetico.html").read_text()
URL = "https://portal.ejemplo.test/inmueble/123/"
PUBLIC = "93.184.216.34"
NONE = Quoted(value=None, evidence=None)


def public(host: str, port: int) -> list[str]:
    return [PUBLIC]


def q(value, evidence):
    return Quoted(value=value, evidence=evidence)


# --- Texto visible ------------------------------------------------------------------------------


def test_texto_visible_sin_scripts_ni_estilos():
    page = page_text(HTML)
    assert page.title == "Piso en venta en calle de Ejemplo, 12, Getafe"
    assert page.images == ["https://img.ejemplo.test/fotos/1.jpg",
                           "https://img.ejemplo.test/fotos/2.jpg"]
    assert "189.500 €" in page.text.splitlines()
    assert "3 habitaciones" in page.text.splitlines()
    for hidden in ("999999", "color: red", "Activa JavaScript"):
        assert hidden not in page.text


# --- La URL tiene que ser pública (SSRF) ---------------------------------------------------------


@pytest.mark.parametrize("url, addresses", [
    ("ftp://portal.ejemplo.test/x", [PUBLIC]),
    ("file:///etc/passwd", [PUBLIC]),
    ("https://portal.ejemplo.test:8443/x", [PUBLIC]),
    ("https://usuario:clave@portal.ejemplo.test/x", [PUBLIC]),
    ("http://interno.test/", ["127.0.0.1"]),
    ("http://interno.test/", ["10.0.0.5"]),
    ("http://interno.test/", ["192.168.1.10"]),
    ("http://metadatos.test/latest/", ["169.254.169.254"]),  # metadatos de la nube
    ("http://interno.test/", ["::1"]),
    ("http://interno.test/", ["::ffff:10.0.0.5"]),
    ("http://mixto.test/", [PUBLIC, "10.0.0.5"]),  # una sola IP interna basta para rechazar
    ("no es una url", [PUBLIC]),
])
def test_urls_que_no_se_descargan(url, addresses):
    with pytest.raises(LinkRefused):
        check_url(url, lambda host, port: addresses)


def test_url_publica():
    assert check_url(URL, public).host == "portal.ejemplo.test"


# --- Descarga: una sola petición, respetando robots.txt y los bloqueos ---------------------------


def site(pages: dict[str, httpx.Response]):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return pages.get(str(request.url), httpx.Response(404))

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return client, seen


def html(body: str = HTML, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=body, headers={"content-type": "text/html; charset=utf-8"})


ROBOTS = "https://portal.ejemplo.test/robots.txt"


def test_descarga_la_pagina_y_nada_mas():
    client, seen = site({URL: html()})
    page = fetch_listing(client, URL, public)
    assert page.title.startswith("Piso en venta")
    assert "85 m² construidos, 72 m² útiles" in page.text
    assert seen == [ROBOTS, URL]  # robots.txt (404: sin restricciones) y la página


def test_robots_txt_que_lo_prohibe():
    client, seen = site({ROBOTS: httpx.Response(200, text="User-agent: *\nDisallow: /inmueble/")})
    with pytest.raises(LinkRefused, match="no permite descargas automáticas"):
        fetch_listing(client, URL, public)
    assert seen == [ROBOTS]  # la página no se pide


def test_robots_txt_para_otros_agentes_no_aplica():
    robots = "User-agent: OtroBot\nDisallow: /\n\nUser-agent: *\nAllow: /"
    client, _ = site({ROBOTS: httpx.Response(200, text=robots), URL: html()})
    assert fetch_listing(client, URL, public).text


@pytest.mark.parametrize("status", [401, 403, 429])
def test_un_bloqueo_no_se_esquiva(status):
    client, seen = site({URL: html("Acceso denegado", status)})
    with pytest.raises(LinkRefused, match="pégalo"):
        fetch_listing(client, URL, public)
    assert seen.count(URL) == 1  # sin reintentos


def test_pagina_de_comprobacion_anti_bot():
    challenge = ('<html><body><div id="captcha-container">Verifica que eres humano</div>'
                 '</body></html>')
    client, _ = site({URL: html(challenge)})
    with pytest.raises(LinkRefused, match="no somos un robot"):
        fetch_listing(client, URL, public)


def test_una_redireccion_a_la_red_interna_se_corta():
    client, seen = site({URL: httpx.Response(302, headers={"location": "http://interno.test/"})})

    def resolve(host, port):
        return ["10.0.0.5"] if host == "interno.test" else [PUBLIC]

    with pytest.raises(LinkRefused):
        fetch_listing(client, URL, resolve)
    assert "http://interno.test/" not in seen


def test_una_redireccion_a_otro_sitio_mira_su_robots_txt():
    other = "https://www.ejemplo.test/inmueble/123/"
    client, seen = site({
        URL: httpx.Response(301, headers={"location": other}),
        "https://www.ejemplo.test/robots.txt": httpx.Response(
            200, text="User-agent: *\nDisallow: /"),
    })
    with pytest.raises(LinkRefused, match="no permite"):
        fetch_listing(client, URL, public)
    assert other not in seen


def test_lo_que_no_es_html_no_se_lee():
    client, _ = site({URL: httpx.Response(200, content=b"%PDF-1.7",
                                          headers={"content-type": "application/pdf"})})
    with pytest.raises(LinkRefused, match="no es una página web"):
        fetch_listing(client, URL, public)


# --- Extracción del anuncio con la cita comprobada -----------------------------------------------

TEXT = "\n".join([page_text(HTML).title or "", page_text(HTML).text])


def listing(**fields) -> ListingExtraction:
    base = dict(operation="venta", operation_evidence="Piso en venta", property_type="vivienda",
                property_type_evidence="Piso en venta", price=NONE, built_area_m2=NONE,
                usable_area_m2=NONE, rooms=NONE, bathrooms=NONE, floor=NONE, condition=NONE,
                address=NONE, municipality=NONE, cadastral_ref=NONE, year_built=NONE,
                community_fees=NONE)
    return ListingExtraction(**{**base, **fields})


GOOD = listing(
    price=q("189500", "189.500 €"),
    built_area_m2=q("85", "85 m² construidos"),
    usable_area_m2=q("72", "72 m² útiles"),
    rooms=q("3", "3 habitaciones"),
    bathrooms=q("1", "1 baño"),
    floor=q("2ª", "Planta 2ª exterior"),
    condition=q("para reformar", "Segunda mano/para reformar"),
    address=q("calle de Ejemplo, 12", "Piso en venta en calle de Ejemplo, 12"),
    municipality=q("Getafe", "Getafe, Madrid"),
    cadastral_ref=q("9872023VK3797S0001WX", "Referencia catastral 9872023VK3797S0001WX."),
    year_built=q("1974", "Construido en 1974"),
    community_fees=q("65", "Gastos de comunidad: 65 €/mes"),
)


def test_el_anuncio_se_extrae_con_sus_citas():
    checked = check_listing(TEXT, GOOD)
    assert checked.rejected == 0
    assert checked.operation == "venta" and checked.property_type == "vivienda"
    assert checked.value("price") == Decimal("189500")
    assert checked.value("usable_area_m2") == Decimal("72")
    assert checked.value("community_fees") == Decimal("65")
    assert checked.value("condition") == "para reformar"


def test_un_precio_inventado_o_de_un_script_se_rechaza():
    checked = check_listing(TEXT, listing(
        price=q("999999", "window.tracking = {precio: 999999}"),  # solo estaba en un script
        rooms=q("4", "3 habitaciones"),
        operation_evidence="Se alquila",
    ))
    assert checked.fields["price"].reason == "la cita no está en el documento"
    assert checked.fields["rooms"].reason == "el número no aparece en la cita"
    assert checked.operation is None


# --- De punta a punta contra la base -------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.fixture
def org(migrated_database: str):
    from housefinder.db.profiles import create_organization

    with psycopg.connect(migrated_database) as conn:
        org_id = create_organization(conn, f"Prueba enlaces {uuid4()}", "particular")
        conn.commit()
    return org_id


def geocoder_at(lon: float, lat: float):
    from housefinder.geo.cartociudad import Geocoded

    def geocode(address: str) -> Geocoded:  # puede no llamarse: la caché ya tiene la dirección
        return Geocoded(lon, lat, "portal", address, "28901", None)

    return geocode


@pytest.mark.db
def test_enlace_pegado_extraido_y_confirmado(migrated_database: str, org):
    from housefinder.db.offers import get_private_offer, list_private_offers
    from housefinder.offers.locate import offer_locator
    from housefinder.offers.pasted import ConfirmationError, confirm, extract_link, submit_link

    client, _ = site({URL: html()})
    with psycopg.connect(migrated_database) as conn:
        submitted = submit_link(conn, org, URL, client, public)
        assert submitted.created
        again = submit_link(conn, org, URL, site({URL: html()})[0], public)
        assert again.offer_id == submitted.offer_id and not again.created
        jobs = conn.execute("SELECT count(*) FROM jobs WHERE kind = 'extract_link' "
                            "AND payload->>'offer_id' = %s", (str(submitted.offer_id),)).fetchone()
        assert jobs[0] == 1  # una sola extracción en cola aunque se pegue dos veces
        offer = get_private_offer(conn, submitted.offer_id, org)
        assert offer.extraction_status == "pendiente" and offer.asking_price is None
        assert "189.500 €" in offer.raw["text"] and "<html" not in offer.raw["text"]

        # El LLM falla: la oferta sigue pendiente y el trabajo se reintentará.
        broken = FakeLLMClient(lambda *a: (_ for _ in ()).throw(LLMOutputError("prueba")))
        with pytest.raises(LLMOutputError):
            extract_link(conn, broken, submitted.offer_id)

        llm = FakeLLMClient(lambda *a: GOOD)
        assert extract_link(conn, llm, submitted.offer_id) == {"extracted": True,
                                                               "rejected_fields": 0}
        assert extract_link(conn, llm, submitted.offer_id) == {"extracted": False}  # ya hecha
        offer = get_private_offer(conn, submitted.offer_id, org)
        assert offer.extraction_status == "extraida"
        assert offer.asking_price is None  # sin confirmar, nada en las columnas

        # Otra organización no la ve ni la confirma.
        other = uuid4()
        assert get_private_offer(conn, submitted.offer_id, other) is None
        add_section(migrated_database, "2806597001", -3.7322, 40.3057)
        geocode = geocoder_at(-3.7322, 40.3057)
        locate = offer_locator(conn, geocode)
        assert not confirm(conn, other, submitted.offer_id, {"price": "1"}, "venta", locate)

        with pytest.raises(ConfirmationError):
            confirm(conn, org, submitted.offer_id, {"price": "doce"}, "venta", locate)
        with pytest.raises(ConfirmationError):
            confirm(conn, org, submitted.offer_id, {"ascensor": "sí"}, "venta", locate)

        values = {"price": "185000", "built_area_m2": "85", "rooms": "3",
                  "address": "calle de Ejemplo, 12", "municipality": "Getafe",
                  "cadastral_ref": "9872023VK3797S0001WX", "floor": ""}
        assert confirm(conn, org, submitted.offer_id, values, "venta", locate)
        offer = get_private_offer(conn, submitted.offer_id, org)
        assert offer.extraction_status == "confirmada"
        assert offer.asking_price == Decimal("185000")
        assert offer.address == "calle de Ejemplo, 12, Getafe"
        assert offer.property_id is not None
        confirmed = offer.extracted["confirmed"]["fields"]
        assert confirmed["price"] == {"value": "185000", "origin": "corregido"}
        assert confirmed["built_area_m2"]["origin"] == "extraido"
        assert "floor" not in confirmed  # vacío: no se guarda
        assert offer.extracted["listing"]["fields"]["price"]["value"] == "189500"  # lo propuesto
        assert submitted.offer_id in [o.id for o in list_private_offers(conn, org)]

        # Corregir la dirección vuelve a ubicar la oferta; si ya no se encuentra, queda sin ubicar.
        moved = {**values, "address": "calle Inexistente, 99"}
        assert confirm(conn, org, submitted.offer_id, moved, "venta",
                       lambda offer: None)
        assert get_private_offer(conn, submitted.offer_id, org).property_id is None


@pytest.mark.db
def test_texto_pegado_y_alquiler_sin_precio_de_compra(migrated_database: str, org):
    from housefinder.db.offers import get_private_offer
    from housefinder.offers.pasted import confirm, submit_text

    with psycopg.connect(migrated_database) as conn:
        submitted = submit_text(conn, org, "Se alquila piso en Getafe por 950 €/mes. 70 m².")
        offer = get_private_offer(conn, submitted.offer_id, org)
        assert offer.raw["source"] == "texto" and offer.url is None
        assert confirm(conn, org, submitted.offer_id, {"price": "950"}, "alquiler",
                       lambda offer: None)
        offer = get_private_offer(conn, submitted.offer_id, org)
        assert offer.asking_price is None  # 950 €/mes no es un precio de compra
        assert offer.extracted["confirmed"]["fields"]["price"] == {"value": "950",
                                                                  "origin": "usuario"}


# --- La geocodificación se comprueba antes de ubicar la oferta -----------------------------------


@pytest.mark.parametrize("expected, matched, same", [
    # Caso real: CartoCiudad leyó el municipio como nombre de calle y dio un punto en Murcia.
    ("Alcalá de Henares", "CALLE ALCALA HENARES 119, 30720 Santiago de la Ribera", False),
    ("Alcalá de Henares", "CALLE MAYOR 1, 28801 Alcalá de Henares", True),
    ("alcala de henares", "CALLE MAYOR 1, 28801 Alcalá de Henares", True),
    ("Madrid", "PLAZA PUERTA DEL SOL 1, 28014 Madrid", True),
    ("Getafe", "CALLE GETAFE 3, 28014 Madrid", False),  # la calle no cuenta
    ("Madrid", "PLAZA PUERTA DEL SOL 1", False),  # sin localidad no se puede comprobar
])
def test_mismo_municipio(expected, matched, same):
    from housefinder.offers.locate import same_municipality

    assert same_municipality(expected, matched) is same


@pytest.mark.db
def test_un_punto_fuera_de_la_zona_o_de_otro_municipio_no_ubica(migrated_database: str):
    from housefinder.geo.cartociudad import Geocoded
    from housefinder.offers.locate import offer_locator
    from housefinder.offers.model import NormalizedOffer

    add_section(migrated_database, "2800597002", -3.3640, 40.4820)

    def geocoder(address: str) -> Geocoded:
        if "M-119" in address:
            return Geocoded(-0.8062, 37.8102, "portal",
                            "CALLE ALCALA HENARES 119, 30720 Santiago de la Ribera", "30035", None)
        return Geocoded(-3.3640, 40.4820, "portal", f"CALLE MAYOR 1, 28801 {uuid4()}", "28005",
                        None)

    def offer(address: str, municipality: str | None) -> NormalizedOffer:
        return NormalizedOffer(external_id="", kind="enlace", url="", address=address,
                               municipality=municipality)

    with psycopg.connect(migrated_database) as conn:
        locate = offer_locator(conn, geocoder)
        # El punto de Murcia no cae en ninguna sección cargada.
        assert locate(offer(f"Carretera M-119 21 {uuid4()}", None)) is None
        # Dentro de la zona, pero la localidad encontrada no es el municipio de la oferta.
        assert locate(offer(f"Calle Mayor 1 {uuid4()}", "Alcalá de Henares")) is None
        # Sin municipio en la oferta, basta con caer en la zona.
        assert locate(offer(f"Calle Mayor 1 {uuid4()}", None)) is not None
