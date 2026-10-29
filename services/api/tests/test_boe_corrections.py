"""Correcciones de anuncios del BOE (F4.4) con anuncios reales de octubre de 2026:
- BOE-B-2026-35167 corrige la cuarta subasta de la TGSS de Salamanca (pág. 55514 del 20/10);
- BOE-B-2026-35104 corrige una subasta de Hacienda en Valencia (pág. 52908 del 7/10), cuyo
  título no dice que sean inmuebles;
- BOE-B-2026-35103 corrige los plazos de una subasta de material del Ejército (sin página)."""

from datetime import date
from pathlib import Path

import httpx
import pytest

from housefinder.agent.extraction import DocumentExtraction, LotExtraction, Quoted
from housefinder.ingestion.boe import BoeItem
from housefinder.offers.channels.boe_v import BoeSectionV, parse_announcement
from housefinder.offers.corrections import is_sale_correction, parse_citation, resolve

FIXTURES = Path(__file__).parent / "fixtures" / "boe" / "correcciones"
CORRECTION_DAY = date(2026, 10, 27)


def text_of(ident: str) -> str:
    return " ".join(parse_announcement((FIXTURES / f"{ident}.xml").read_bytes())["texto"])


@pytest.mark.parametrize("ident, published_on, number, page", [
    ("BOE-B-2026-35167", date(2026, 10, 20), 260, 55514),
    ("BOE-B-2026-35104", date(2026, 10, 7), 249, 52908),
    ("BOE-B-2026-35103", date(2026, 10, 21), 261, None),
])
def test_cita_del_anuncio_corregido(ident, published_on, number, page):
    citation = parse_citation(text_of(ident), CORRECTION_DAY)
    assert (citation.published_on, citation.number, citation.page) == (published_on, number, page)


def test_una_fecha_posterior_no_es_la_cita():
    text = "publicado en el BOE núm. 300, de 30 de noviembre de 2026, pág. 60000"
    assert parse_citation(text, CORRECTION_DAY) is None


def test_titulos_de_correcciones_de_ventas():
    assert is_sale_correction("Anuncio de corrección de errores en la Resolución … subasta pública")
    assert is_sale_correction("rectificación del anuncio de licitación de subasta patrimonial")
    assert not is_sale_correction("Anuncio de corrección de errores del concurso de traslados")
    assert not is_sale_correction("Resolución por la que se convoca subasta de un inmueble")


def item(ident, department="TGSS", section="5B", pages=None, title="Subasta"):
    return BoeItem(ident, title, None, None, date(2026, 10, 21), section, department, pages)


def test_por_pagina_por_departamento_y_por_expediente():
    correction = item("C", title="Corrección de la subasta del Expediente 2228/0002/26/00/11")
    by_page = resolve(correction, "", parse_citation("BOE núm. 1, de 20 de octubre de 2026, "
                                                      "pág. 55514", CORRECTION_DAY),
                      [item("A", pages=(55500, 55513)), item("B", pages=(55514, 55515))])
    assert (by_page.original.identifier, by_page.method) == ("B", "pagina")

    no_page = parse_citation("BOE número 261, de fecha 21 de octubre de 2026", CORRECTION_DAY)
    only = resolve(correction, "", no_page, [item("A"), item("Z", department="Otro")])
    assert (only.original.identifier, only.method) == ("A", "departamento")
    two = [item("A", title="Subasta del Expediente 2228/0001/26"),
           item("B", title="Subasta del Expediente 2228/0002/26/00/11")]
    by_number = resolve(correction, "", no_page, two)
    assert (by_number.original.identifier, by_number.method) == ("B", "expediente")
    unknown = resolve(item("C", title="Corrección"), "", no_page, two)
    assert unknown.original is None and unknown.method.startswith("2 anuncios")


# --- Canal -------------------------------------------------------------------------------------


def boe_client(seen: list[str] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if "/sumario/" in url:
            path = FIXTURES / f"sumario-{url.rsplit('/', 1)[1]}.json"
            return httpx.Response(200, content=path.read_bytes()) if path.exists() else (
                httpx.Response(404))
        if "xml.php?id=" in url:
            path = FIXTURES / f"{url.rsplit('=', 1)[1]}.xml"
            return httpx.Response(200, content=path.read_bytes()) if path.exists() else (
                httpx.Response(404))
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_el_canal_guarda_la_correccion_y_el_anuncio_corregido():
    channel = BoeSectionV([CORRECTION_DAY])
    items = list(channel.fetch(boe_client()))
    assert [i.external_id for i in items] == ["BOE-B-2026-34188", "BOE-B-2026-35167"]
    original, correction = items
    assert original.published_on == date(2026, 10, 20)
    assert correction.raw["corrige"]["boe"] == "BOE-B-2026-34188"
    assert channel.parse(correction)[0].extraction_status == "no_aplica"  # sin lotes nuevos
    assert channel.parse(original)[0].extraction_status == "pendiente"
    logs = {log.correction: log for log in channel.corrections}
    assert logs["BOE-B-2026-35167"].method == "pagina" and logs["BOE-B-2026-35167"].kept
    # Valencia: resuelta por página, pero el título del original no dice que sean inmuebles.
    assert (logs["BOE-B-2026-35104"].original, logs["BOE-B-2026-35104"].kept) == (
        "BOE-B-2026-32556", False)
    # Ejército: resuelta por departamento; es material, no inmuebles.
    assert (logs["BOE-B-2026-35103"].original, logs["BOE-B-2026-35103"].method,
            logs["BOE-B-2026-35103"].kept) == ("BOE-B-2026-34258", "departamento", False)


# --- Contra la base -----------------------------------------------------------------------------

psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_correccion_enlazada_con_su_anuncio(migrated_database: str):
    from housefinder.db.offers import corrections_of
    from housefinder.offers.run import run_boe_v

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        conn.execute("DELETE FROM watch_issues WHERE source = 'offers_boe_v' "
                     "AND issue_id = '2026-10-27'")
        # Guardada antes como anuncio pendiente, como pasó en la base de desarrollo.
        conn.execute("INSERT INTO offers (channel, external_id, kind, raw, raw_sha256, "
                     "extraction_status, published_on) VALUES ('boe_seccion_v', "
                     "'BOE-B-2026-35167', 'anuncio', '{}', 'x', 'pendiente', '2026-10-27') "
                     "ON CONFLICT (channel, external_id) DO UPDATE SET "
                     "extraction_status = 'pendiente', corrects_id = NULL")
    report = run_boe_v(migrated_database, boe_client(), CORRECTION_DAY, days=1,
                       geocoder=lambda address: None, parcels=lambda ref: None)
    assert report["corrections_linked"] == 1
    assert {c["correction"] for c in report["corrections"] if c["kept"]} == {"BOE-B-2026-35167"}
    with psycopg.connect(migrated_database) as conn:
        original = conn.execute("SELECT id, extraction_status FROM offers "
                                "WHERE external_id = 'BOE-B-2026-34188'").fetchone()
        assert original[1] == "pendiente"
        assert conn.execute("SELECT extraction_status FROM offers WHERE external_id = "
                            "'BOE-B-2026-35167'").fetchone() == ("no_aplica",)
        found = corrections_of(conn, original[0])
    assert [c.external_id for c in found] == ["BOE-B-2026-35167"]
    assert found[0].published_on == CORRECTION_DAY


@pytest.mark.db
def test_si_el_llm_ve_una_correccion_no_crea_lotes(migrated_database: str):
    from housefinder.agent.llm import FakeLLMClient
    from housefinder.offers.extract import extract_pending

    none = Quoted(value=None, evidence=None)
    duplicated = LotExtraction(
        label=none, property_type="garaje", property_type_evidence="plaza de garaje",
        address=none, municipality=none, province=none, cadastral_ref=none, built_area_m2=none,
        floor=none, price=none, deposit=none)
    llm = FakeLLMClient(lambda *a: DocumentExtraction(
        is_correction=True, corrected_reference=none, lots=[duplicated]))
    with psycopg.connect(migrated_database) as conn:
        conn.execute("INSERT INTO offers (channel, external_id, kind, raw, raw_sha256, "
                     "extraction_status) VALUES ('prueba_correccion', 'X-1', 'anuncio', "
                     "'{\"texto\": [\"Advertidos errores… plaza de garaje\"]}', 'x', 'pendiente') "
                     "ON CONFLICT (channel, external_id) DO UPDATE SET extraction_status = "
                     "'pendiente'")
        conn.commit()
        report = extract_pending(conn, llm, "prueba_correccion", lambda offer: None)
        assert (report.corrections, report.lots) == (1, 0)
        assert conn.execute("SELECT count(*) FROM offers o JOIN offers p ON o.parent_id = p.id "
                            "WHERE p.external_id = 'X-1'").fetchone()[0] == 0
