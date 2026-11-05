"""Velocidad sin cambiar ninguna cifra: el índice de las reglas, el cuadro de amortización que se
calcula una vez y la caché de planes por contenido (la búsqueda, la ficha y el plan completo)."""

from datetime import date
from decimal import Decimal

import pytest
from test_offer_valuation import database  # noqa: F401
from test_plan_assumptions import references  # noqa: F401
from test_reverse_search import book, profile, rules, searchable  # noqa: F401

from housefinder.core.dated import containing
from housefinder.engines.mortgage import amortization_schedule
from housefinder.regulation.rules import Rule, RuleBook

D = Decimal
psycopg = pytest.importorskip("psycopg")


def rule(id: str, territory: str, rate: str, since: str = "2026-01-01") -> Rule:
    return Rule(id=id, kind="tipo_ibi", territory=territory,
                effective_from=date.fromisoformat(since), effective_to=None, status="vigente",
                params={"rate": rate}, source_url="https://example", verified=True)


def test_los_territorios_que_contienen_a_otro() -> None:
    assert containing("ES") == ["ES"]
    assert containing("ES-13") == ["ES", "ES-13"]
    assert containing("ES-13-28079") == ["ES", "ES-13", "ES-13-28079", "ES-13-28"]
    assert containing("ES-16-48020") == ["ES", "ES-16", "ES-16-48020", "ES-16-48"]
    assert containing("ES-16-48") == ["ES", "ES-16", "ES-16-48"]


def test_el_indice_da_la_misma_regla_que_recorrerlas_todas() -> None:
    book = RuleBook([rule("estatal", "ES", "0.01"), rule("madrid", "ES-13", "0.02"),
                     rule("bizkaia", "ES-16-48", "0.03"), rule("bilbao", "ES-16-48020", "0.04"),
                     rule("getafe", "ES-13-28065", "0.05", "2025-01-01")])
    on = date(2026, 6, 1)
    assert book.resolve("tipo_ibi", "ES-13-28065", on).id == "getafe"
    assert book.resolve("tipo_ibi", "ES-13-28079", on).id == "madrid"
    assert book.resolve("tipo_ibi", "ES-16-48020", on).id == "bilbao"
    assert book.resolve("tipo_ibi", "ES-16-48013", on).id == "bizkaia"  # la provincia foral
    assert book.resolve("tipo_ibi", "ES-09-08019", on).id == "estatal"
    assert book.resolve("otro_tipo", "ES-13", on) is None
    # Una regla añadida después a la lista también cuenta: el índice se rehace
    book.rules.append(rule("madrid-capital", "ES-13-28079", "0.06"))
    assert book.resolve("tipo_ibi", "ES-13-28079", on).id == "madrid-capital"


def test_el_cuadro_de_amortizacion_se_reutiliza_sin_compartir_la_lista() -> None:
    first = amortization_schedule(D("100000"), D("0.03"), 25)
    first.pop()  # quien llama puede tocar su lista
    again = amortization_schedule(D("100000"), D("0.03"), 25)
    assert len(again) == 300 and again[-1].balance == D("0.00")


@pytest.mark.db
def test_la_cache_da_el_mismo_plan_y_recalcula_cuando_algo_cambia(searchable, org,  # noqa: F811
                                                                   monkeypatch):
    from test_offer_valuation import confirmed_offer

    import housefinder.search.service as service
    from housefinder.db.offers import set_rent_expectation

    cheap = confirmed_offer(searchable, org, "venta", "150000")
    dear = confirmed_offer(searchable, org, "venta", "900000")
    calls: list[object] = []
    real = service._score
    monkeypatch.setattr(service, "_score", lambda *a, **k: calls.append(a[5]) or real(*a, **k))
    cache: service.ContentCache = service.ContentCache()
    rb, pb = rules(), book()
    with psycopg.connect(searchable) as conn:
        plain = service.search(conn, pb, rb, profile(), org)
        computed = len(calls)
        first = service.search(conn, pb, rb, profile(), org, cache=cache)
        again = service.search(conn, pb, rb, profile(), org, cache=cache)
        assert len(calls) == 2 * computed  # la segunda vez, con caché, no calcula nada
        assert [s.offer_id for s in again.ranked] == [s.offer_id for s in plain.ranked] \
            == [cheap, dear]
        assert again.ranked == first.ranked == plain.ranked  # las mismas cifras, una a una

        # La ficha de una oferta da lo mismo que la búsqueda, sin puntuar las demás
        before = len(calls)
        one = service.score_offer(conn, pb, rb, profile(), org, cheap, cache=cache)
        assert one == plain.ranked[0] and len(calls) == before

        # Otro perfil, u otra renta esperada para una oferta: se calcula de nuevo
        service.search(conn, pb, rb, profile(available_savings=D("120000")), org, cache=cache)
        assert len(calls) == before + computed
        set_rent_expectation(conn, org, cheap, "temporada", D("1500"))
        before = len(calls)
        service.search(conn, pb, rb, profile(), org, cache=cache)
        assert [c.offer_id for c in calls[before:]] == [cheap]  # solo esa oferta


@pytest.fixture
def org(searchable):  # noqa: F811
    from uuid import uuid4

    from housefinder.db.profiles import create_organization

    with psycopg.connect(searchable) as conn:
        org_id = create_organization(conn, f"Caché {uuid4()}", "particular")
        conn.commit()
    return org_id
