"""Canal de ventas directas del Patrimonio del Estado (ADR-0037), con el RSS y las fichas reales
del 2026-11-02. Los PDF no se guardan: un lector falso devuelve el texto de sus páginas."""

from datetime import date
from pathlib import Path

import httpx
import pytest

from housefinder.offers.channels.patrimonio import (
    PatrimonioEstado,
    describing_documents,
    document_lines,
    parse_feed,
    parse_ficha,
)

FIXTURES = Path(__file__).parent / "fixtures" / "patrimonio"
FICHAS = {
    "DEH-CIUDAD-REAL/Venta-directa": "ficha-ciudad-real.html",
    "DEH-ACoruna/Lotes-desiertos": "ficha-a-coruna.html",
    "DEH-MADRID/VentaDirecta4Subasta": "ficha-madrid.html",
    "DEH-OURENSE/Parcela-757": "ficha-ourense-757.html",
    "DEH-OURENSE/PARCELA-528": "ficha-ourense-528.html",
}
LOT_SHEET = ["MINISTERIO DE HACIENDA\nLote 1.- Finca rústica, polígono 8, parcela 66\n"
             "Precio: 1.000 euros\n1"]


def ficha(name: str):
    return parse_ficha((FIXTURES / name).read_bytes())


def test_el_rss_trae_las_ventas_directas():
    items = parse_feed((FIXTURES / "ventas-directas.xml").read_bytes())
    assert len(items) == 5
    first = items[0]
    assert first.external_id == ("VentasDirectas/DEH-CIUDAD-REAL/Venta-directa-finca-rustica-"
                                 "Poligono-11-Parcela-130-de-Fuente-el-Fresno.aspx")
    assert first.published_on == date(2026, 10, 23)
    assert first.description == "Delegación: CIUDAD REAL - Fecha límite: 26/02/2027"


def test_campos_y_documentos_de_la_ficha():
    ourense = ficha("ficha-ourense-757.html")
    assert ourense.title == "PARCELA 757, POLÍGONO 502, AYUNTAMIENTO DE BALTAR"
    assert ourense.fields["Precio"] == "1.344,49"
    assert ourense.fields["Superficie"] == "7.872 m2"
    assert "RC: 32006A502007570000JX" in ourense.fields["Denominación"]
    assert "Documentación" not in ourense.fields
    assert [d.name for d in ourense.documents] == [
        "Pliego Subasta 23 de marzo de 2026",
        "Modelo de Solicitud de Enajenación por Adjudicación Directa"]
    assert ourense.documents[0].url.startswith("https://www.hacienda.gob.es/dgpatrimonio/")


def test_solo_se_extraen_las_hojas_de_lote_y_las_listas_de_desiertos():
    # Con precio y superficie en la ficha, no hace falta ningún PDF.
    assert describing_documents(ficha("ficha-ourense-757.html")) == []
    assert describing_documents(ficha("ficha-ciudad-real.html")) == []
    # La lista de lotes desiertos sí; los formularios no.
    assert [d.name for d in describing_documents(ficha("ficha-a-coruna.html"))] == [
        "Lotes desiertos"]
    # Las hojas de lote sí; el pliego de la subasta original (con lotes ya vendidos) y la
    # solicitud, no.
    madrid = describing_documents(ficha("ficha-madrid.html"))
    assert [d.name for d in madrid] == ["Lote 1", "Lote 2", "Lote 3", "Lote 4", "Lote 5"]


def test_lineas_sin_cabeceras_ni_numeros_de_pagina():
    pages = [
        "MINISTERIO DE HACIENDA\nLote nº 1.- Casa en Magacela\nFdo. El Delegado\n1",
        "MINISTERIO DE HACIENDA\nTipo de licitación: 7.976,26 euros.\nFdo. El Delegado\nPágina 2",
        "MINISTERIO DE HACIENDA\n  Lote nº 2.-   Rústica\nFdo. El Delegado\n3 de 3",
    ]
    assert document_lines(pages) == [
        "Lote nº 1.- Casa en Magacela", "Tipo de licitación: 7.976,26 euros.",
        "Lote nº 2.- Rústica"]
    # Con una sola página no se quita nada por repetido.
    assert document_lines(["Lote 1\nLote 1"]) == ["Lote 1", "Lote 1"]


def hacienda_client(seen: list[str], robots: bytes | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, content=robots or (FIXTURES / "robots.txt").read_bytes())
        if "RssVentasDirectas" in url:
            return httpx.Response(200, content=(FIXTURES / "ventas-directas.xml").read_bytes())
        if url.lower().endswith(".pdf"):
            return httpx.Response(200, content=b"%PDF-1.4 falso")
        for key, name in FICHAS.items():
            if key in url:
                return httpx.Response(200, content=(FIXTURES / name).read_bytes())
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_canal_con_las_fichas_reales():
    seen: list[str] = []
    channel = PatrimonioEstado(pdf_reader=lambda content: LOT_SHEET)
    items = {i.external_id.split("/")[1]: i for i in channel.fetch(hacienda_client(seen))}
    assert sorted(items) == ["DEH-ACoruna", "DEH-CIUDAD-REAL", "DEH-MADRID", "DEH-OURENSE"]
    assert len(list(channel.fetch(hacienda_client([])))) == 5
    # Las URL van escapadas, como las pide el servidor.
    assert all(" " not in url for url in seen)
    # Solo se bajan las hojas de lote y la lista de desiertos: 5 + 1 PDF.
    assert len([u for u in seen if u.lower().endswith(".pdf")]) == 6
    assert not any("pliego" in u.lower() or "solicitud" in u.lower()
                   for u in seen if u.lower().endswith(".pdf"))
    madrid = next(i for i in channel.fetch(hacienda_client([]))
                  if "DEH-MADRID" in i.external_id)
    assert madrid.raw["texto"][0] == "Venta Directa Bienes Patrimoniales"
    assert "Lote 1.- Finca rústica, polígono 8, parcela 66" in madrid.raw["texto"]
    assert "MINISTERIO DE HACIENDA" in madrid.raw["texto"]  # una sola página: no se repite
    offer = channel.parse(madrid)[0]
    assert offer.kind == "anuncio" and offer.extraction_status == "pendiente"
    assert offer.title == "Venta Directa Bienes Patrimoniales"
    assert offer.url.startswith("https://www.hacienda.gob.es/es-ES/Areas%20Tematicas/")


def test_lo_ya_guardado_sin_cambios_no_se_vuelve_a_bajar():
    items = parse_feed((FIXTURES / "ventas-directas.xml").read_bytes())
    known = {i.external_id: i.pub_date for i in items[1:]}
    seen: list[str] = []
    channel = PatrimonioEstado(known, pdf_reader=lambda content: LOT_SHEET)
    fetched = list(channel.fetch(hacienda_client(seen)))
    assert [i.external_id for i in fetched] == [items[0].external_id]
    assert channel.unchanged == 4
    assert not any("DEH-MADRID" in u for u in seen)


def test_se_respeta_el_robots_txt():
    robots = b"User-agent: *\nDisallow: /dgpatrimonio/\n"
    seen: list[str] = []
    channel = PatrimonioEstado(pdf_reader=lambda content: LOT_SHEET)
    items = list(channel.fetch(hacienda_client(seen, robots)))
    assert len(items) == 5  # las fichas se leen
    assert not any(u.lower().endswith(".pdf") for u in seen)  # los PDF, no
    assert len(channel.disallowed) == 6
    coruna = next(i for i in items if "DEH-ACoruna" in i.external_id)
    assert coruna.raw["documentos"][0]["error"] == "robots.txt"


def test_un_pdf_sin_texto_se_anota_y_la_oferta_se_guarda():
    channel = PatrimonioEstado(pdf_reader=lambda content: ["", ""])
    items = list(channel.fetch(hacienda_client([])))
    assert len(items) == 5
    assert len(channel.unreadable) == 6
    assert channel.unreadable[0]["error"] == "sin texto (escaneado)"


# --- Contra la base -----------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_canal_de_punta_a_punta(migrated_database: str):
    from housefinder.offers.run import run_patrimonio

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM offers WHERE channel = 'patrimonio_estado'")
    first = run_patrimonio(migrated_database, hacienda_client([]), lambda content: LOT_SHEET)
    assert first["items"] == 5 and first["offers_new"] == 5 and first["pending_extraction"] == 5
    again = run_patrimonio(migrated_database, hacienda_client([]), lambda content: LOT_SHEET)
    assert again["items"] == 0 and again["unchanged"] == 5
    with psycopg.connect(migrated_database) as conn:
        rows = conn.execute(
            "SELECT kind, extraction_status, org_id, source_id FROM offers "
            "WHERE channel = 'patrimonio_estado'").fetchall()
        source = conn.execute("SELECT license FROM sources WHERE id = 'patrimonio-estado'"
                              ).fetchone()
    assert set(rows) == {("anuncio", "pendiente", None, "patrimonio-estado")}
    assert "Origen de los datos: Ministerio de Hacienda" in source[0]
