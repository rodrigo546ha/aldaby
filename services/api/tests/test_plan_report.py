"""PDF del plan (F6.8, ADR-0026): secciones, notas numeradas y anexo con cada fuente una vez."""

from datetime import date
from decimal import Decimal

import pytest
from test_offer_valuation import database  # noqa: F401
from test_plan_assumptions import references  # noqa: F401
from test_reverse_search import book, org, profile, rules, searchable  # noqa: F401

psycopg = pytest.importorskip("psycopg")

D = Decimal
TODAY = date(2026, 10, 31)


def weasyprint_or_skip() -> None:
    try:
        import weasyprint  # noqa: F401
    except OSError:
        pytest.skip("Sin pango para WeasyPrint: lanza los tests con make test (ADR-0026)")


@pytest.fixture
def plan(searchable, org):  # noqa: F811
    from test_offer_valuation import confirmed_offer

    from housefinder.plans.service import full_plan

    offer = confirmed_offer(searchable, org, "venta", "150000")
    with psycopg.connect(searchable) as conn:
        return full_plan(conn, book(), rules(), profile(management_fee_rate=D("0.08")), org,
                         offer, TODAY)


@pytest.mark.db
def test_html_con_notas_y_anexo_de_fuentes(searchable, plan):  # noqa: F811
    from housefinder.reports.pdf import plan_html, plan_sources

    with psycopg.connect(searchable) as conn:
        sources = plan_sources(conn, plan, rules(), book())
    html = plan_html(plan, sources, TODAY)
    for title in ("Capacidad de compra", "Hipoteca", "Prueba de estrés", "Tipo de alquiler",
                  "Argumentos para no comprar", "Hoja de ruta de compra", "Fuentes"):
        assert title in html
    assert "generado el 2026-10-31" in html
    # Cada fuente una vez y numerada; toda cifra cita las suyas
    refs = [e.number for e in sources.entries]
    assert refs == list(range(1, len(refs) + 1))
    assert all(sources.notes(f) for f in plan.figures())
    by_title = {e.title: e for e in sources.entries}
    ibi = by_title["ibi-28993"]  # la regla de prueba
    assert ibi.kind == "Norma" and ibi.url == "https://example" and "sin verificar" in ibi.detail
    bde = next(e for e in sources.entries if e.kind == "Datos" and e.url)
    assert "Licencia" in bde.detail
    assert any(e.kind == "Dato tuyo" and "perfil" in e.detail for e in sources.entries)
    assert "235.000" not in html and "150.000,00 €" in html  # formato español del precio


@pytest.mark.db
def test_pdf(searchable, plan):  # noqa: F811
    weasyprint_or_skip()
    from housefinder.reports.pdf import plan_html, plan_pdf, plan_sources

    with psycopg.connect(searchable) as conn:
        html = plan_html(plan, plan_sources(conn, plan, rules(), book()), TODAY)
    pdf = plan_pdf(html)
    assert pdf.startswith(b"%PDF") and len(pdf) > 10_000
