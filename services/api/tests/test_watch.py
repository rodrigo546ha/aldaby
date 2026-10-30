"""Vigilancia del BOE y del BOCM (F2.6) con sumarios reales recortados (tests/fixtures/boe, bocm).

BOE del 07/10/2026: RDL 28/2026 y 29/2026. BOE del 02/10/2026: edición extraordinaria con las
derogaciones de los RDL 26/2026 y 27/2026. BOCM del 09/10/2026: Ley 6/2026 de Madrid.
"""

import json
import re
from datetime import date
from pathlib import Path

import httpx
import pytest

from housefinder.ingestion.bocm import Pace, parse_summary
from housefinder.regulation.rules import RuleBook, default_rules_dir
from housefinder.watch.rules import Publication, load_rules, match
from housefinder.watch.run import bocm_publications, boe_publications, tasks_for

NO_WAIT = Pace(sleep=lambda seconds: None)  # en los tests no se espera al BOCM

FIXTURES = Path(__file__).parent / "fixtures"
RULES = load_rules()


def boe(day: str):
    payload = json.loads((FIXTURES / "boe" / f"sumario-{day}.json").read_text("utf-8"))
    return boe_publications(payload, date(int(day[:4]), int(day[4:6]), int(day[6:])))


def bocm():
    return bocm_publications(parse_summary((FIXTURES / "bocm" / "sumario-20261009.xml")
                                           .read_bytes()))


def test_los_rdl_de_vivienda_se_siguen_con_sus_reglas():
    tasks = {t.external_id: t for t in tasks_for(boe("20261007"), RULES)}
    rdl29 = tasks["BOE-A-2026-20823"]
    assert rdl29.tags == ("seguimiento",)
    assert "irpf-reduccion-alquiler-rdl-29-2026" in rdl29.rule_ids
    assert "convalidación" in rdl29.notes[0]
    rdl28 = tasks["BOE-A-2026-20822"]
    assert rdl28.rule_ids == ("prorroga-alquiler-habitual-rdl-28-2026",)
    assert "15/11/2026" in rdl28.notes[0]
    assert rdl28.section == "1" and rdl28.department == "JEFATURA DEL ESTADO"


def test_las_derogaciones_de_la_edicion_extraordinaria():
    pubs = boe("20261002")
    tasks = {t.external_id: t for t in tasks_for(pubs, RULES)}
    assert {"BOE-A-2026-20526", "BOE-A-2026-20527"} <= tasks.keys()
    assert "decreto-ley" in tasks["BOE-A-2026-20526"].tags
    # Nada de la sección II.A (nombramientos) abre tarea.
    personnel = [p.identifier for p in pubs if p.section == "2A"]
    assert personnel and not set(personnel) & tasks.keys()


def test_bocm_ley_de_madrid_y_sin_personal_ni_anuncios():
    pubs = bocm()
    tasks = tasks_for(pubs, RULES)
    titles = {t.external_id: t.title for t in tasks}
    assert any("Ley 6/2026" in title for title in titles.values())
    parts = {p.identifier: p.part for p in pubs}
    assert all(parts[t] not in {"B) Autoridades y Personal", "D) Anuncios"} for t in titles)


def publication(title, section="1", department="MINISTERIO DE HACIENDA", source="boe"):
    return Publication(source, "X", title, "https://x", date(2026, 10, 1), section,
                       department=department)


def test_exclusion_y_patron_que_siempre_pasa():
    assert match(publication("Real Decreto 1/2026 de subvenciones de vivienda"), RULES) is None
    forced = match(publication("Real Decreto 2/2026 de subvenciones a las comunidades que "
                               "hayan declarado zonas de mercado residencial tensionado"), RULES)
    assert forced is not None and "vivienda" in forced.tags


def test_departamentos_de_otras_comunidades():
    law = "Ley 3/2026, de vivienda de Cataluña"
    assert match(publication(law, department="COMUNIDAD AUTÓNOMA DE CATALUÑA"), RULES) is None
    assert match(publication(law, department="COMUNIDAD DE MADRID"), RULES) is not None


def test_lo_que_se_sigue_pasa_en_cualquier_seccion():
    found = match(publication("Acuerdo de convalidación del Real Decreto-ley 29/2026",
                              section="5B"), RULES)
    assert found is not None and found.tags == ("seguimiento",)


def test_fuera_de_seccion_no_abre_tarea():
    assert match(publication("Anuncio sobre arrendamiento de vivienda", section="5B"),
                 RULES) is None


def test_cada_regla_pendiente_se_vigila_y_cada_regla_vigilada_existe():
    book = RuleBook.from_dir(default_rules_dir())
    ids = {r.id for r in book.rules}
    pending = {r.id for r in book.rules if r.status == "pendiente_convalidacion"}
    tracked = {rule for t in RULES.tracked for rule in t.rules}
    assert pending <= tracked, f"Reglas pendientes sin vigilar: {pending - tracked}"
    assert tracked <= ids, f"Reglas vigiladas que no existen: {tracked - ids}"


# --- Contra la base de datos, con un servidor falso -----------------------------------------

psycopg = pytest.importorskip("psycopg")


class FakeBulletins:
    """Sirve los sumarios de las fixtures y cuenta las peticiones."""

    def __init__(self):
        self.requests: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if "/datosabiertos/api/boe/sumario/" in url:
            day = url.rsplit("/", 1)[1]
            path = FIXTURES / "boe" / f"sumario-{day}.json"
            return (httpx.Response(200, content=path.read_bytes()) if path.exists()
                    else httpx.Response(404))
        if url.endswith("/sumarios.rss"):
            return httpx.Response(200, content=(FIXTURES / "bocm" / "sumarios.rss").read_bytes())
        if "/boletin-completo/" in url:
            day, number = re.search(r"BOCM-(\d{8})/(\d+)", url).groups()
            href = f"/boletin/CM_Boletin_BOCM/x/BOCM-{day}{number}.xml"
            return httpx.Response(200, text=f'<a href="{href}">XML</a>')
        if "/CM_Boletin_BOCM/" in url:
            return httpx.Response(
                200, content=(FIXTURES / "bocm" / "sumario-20261009.xml").read_bytes())
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


@pytest.mark.db
def test_vigilancia_del_boe_sin_repetir(migrated_database: str):
    from housefinder.watch.run import watch_boe

    fake = FakeBulletins()
    today = date(2026, 10, 8)  # lee 08/10 (aún sin BOE: no se marca), 07/10 y 06/10 (404)
    result = watch_boe(migrated_database, fake.client(), today, days=3)
    assert result == {"days_read": 1, "tasks_opened": result["tasks_opened"]}
    assert result["tasks_opened"] >= 2
    first = len(fake.requests)
    again = watch_boe(migrated_database, fake.client(), today, days=3)
    assert again == {"days_read": 0, "tasks_opened": 0}
    assert len(fake.requests) - first == 1  # solo vuelve a pedir hoy, que no estaba marcado
    with psycopg.connect(migrated_database) as conn:
        rdl = conn.execute("SELECT tags, rule_ids FROM review_tasks "
                           "WHERE external_id = 'BOE-A-2026-20823'").fetchone()
    assert rdl[0] == ["seguimiento"] and "plusvalia-coeficientes-maximos-rdl-29-2026" in rdl[1]


@pytest.mark.db
def test_vigilancia_del_bocm_sin_repetir(migrated_database: str):
    from housefinder.watch.run import watch_bocm

    fake = FakeBulletins()
    result = watch_bocm(migrated_database, fake.client(), pace=NO_WAIT)
    # Tres boletines en el RSS; el falso sirve el mismo sumario a los tres: las tareas no se
    # repiten porque la clave es la publicación.
    assert result["bulletins_read"] == 3 and result["tasks_opened"] >= 1
    before = len(fake.requests)
    assert watch_bocm(migrated_database, fake.client(), pace=NO_WAIT) == {"bulletins_read": 0,
                                                             "tasks_opened": 0}
    assert len(fake.requests) - before == 1  # solo el RSS


@pytest.mark.db
def test_decidir_una_tarea(migrated_database: str):
    from housefinder.db.review_tasks import NewTask, decide, list_tasks, open_task

    with psycopg.connect(migrated_database, autocommit=True) as conn:
        task_id = open_task(conn, NewTask("boe", "BOE-A-TEST-1", date(2026, 10, 1), "t", "u",
                                          "1", "", ("vivienda",), (), ()))
        assert open_task(conn, NewTask("boe", "BOE-A-TEST-1", date(2026, 10, 1), "t", "u",
                                       "1", "", ("vivienda",), (), ())) is None
        assert decide(conn, task_id, "descartada", "Rodrigo", "no afecta")
        assert task_id not in {t.id for t in list_tasks(conn)}
        assert not decide(conn, 10**9, "aplicada", "Rodrigo", None)
        with pytest.raises(ValueError, match="abierta"):
            decide(conn, task_id, "abierta", "Rodrigo", None)


def test_el_bocm_se_lee_con_10_segundos_entre_peticiones():
    now = [0.0]
    waits: list[float] = []

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds

    pace = Pace(sleep=sleep, clock=lambda: now[0])
    pace.wait()  # la primera no espera
    now[0] += 3  # han pasado 3 s
    pace.wait()
    pace.wait()
    assert waits == [7.0, 10.0]
