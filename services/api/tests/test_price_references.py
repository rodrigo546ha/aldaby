"""Referencias de precio (F5.1, F5.5, ADR-0018): valor tasado municipal de la Comunidad de Madrid
e índice de precios de vivienda del INE. Muestras copiadas de las respuestas reales del
2026-10-30."""

from decimal import Decimal

import httpx
import pytest

from housefinder.ingestion import ine_ipc_alquiler, ine_ipv, valor_tasado

# CSV real: Latin-1, «;», el código es el del INE sin provincia y con dígito de control.
CSV = (
    "Año;Tipo territorio;Código territorio;Territorio;Valor;Unidad;Estado dato\r\n"
    "2025;Municipios;0014;Acebeda (La);-;Euros/m2;\r\n"
    "2024;Municipios;0796;Madrid;4224.9;Euros/m2;\r\n"
    "2025;Municipios;0796;Madrid;4993.3;Euros/m2;\r\n"
    "2025;Municipios;9036;Tres Cantos;3867.3;Euros/m2;\r\n"
).encode("latin-1")


def series(cod, region, region_name, kind, data_type, points):
    return {"COD": cod, "Nombre": f"{region_name}. {kind}. {data_type}. ",
            "MetaData": [{"Codigo": region, "Nombre": region_name},
                         {"Codigo": "", "Nombre": kind},
                         {"Codigo": "0" if data_type == "Índice" else "1", "Nombre": data_type}],
            "Data": [{"Anyo": y, "T3_Periodo": q, "Valor": v, "T3_TipoDato": "Definitivo"}
                     for y, q, v in points]}


IPV = [
    series("IPV1437", "13", "Madrid, Comunidad de", "General", "Índice",
           [(2026, "T2", 111.85), (2026, "T1", 107.296)]),
    series("IPV1447", "13", "Madrid, Comunidad de", "Vivienda segunda mano", "Índice",
           [(2026, "T2", 112.649)]),
    series("IPV1441", "13", "Madrid, Comunidad de", "General", "Variación anual",
           [(2026, "T2", 14.2)]),  # no es un índice: fuera
    series("IPV1300", "01", "Andalucía", "General", "Índice", [(2026, "T2", 108.0)]),
]


def test_valor_tasado_por_municipio_con_codigo_del_ine():
    rows, empty = valor_tasado.parse(CSV)
    assert empty == 1
    found = {(r.code, r.year): r.value for r in rows}
    assert found == {("28079", 2024): Decimal("4224.9"), ("28079", 2025): Decimal("4993.3"),
                     ("28903", 2025): Decimal("3867.3")}  # Tres Cantos: 9036 → 28903
    assert all(r.measure == "valor_tasado_m2" and r.unit == "EUR/m2" for r in rows)


def test_valor_tasado_con_otra_unidad_no_se_carga():
    bad = CSV.replace(b"4993.3;Euros/m2", b"4993.3;Euros")
    with pytest.raises(ValueError, match="Unidad inesperada"):
        valor_tasado.parse(bad)


def test_ipv_solo_indices_de_la_comunidad():
    rows = ine_ipv.parse(IPV, "13")
    found = {(r.typology, r.year, r.quarter): r.value for r in rows}
    assert found == {("todas", 2026, 2): Decimal("111.85"), ("todas", 2026, 1): Decimal("107.296"),
                     ("segunda_mano", 2026, 2): Decimal("112.649")}
    assert all(r.level == "comunidad" and r.code == "13" and r.stat == "indice" for r in rows)


psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_carga_de_las_dos_fuentes(migrated_database: str):
    def handler(request: httpx.Request) -> httpx.Response:
        if "datos.comunidad.madrid" in str(request.url):
            return httpx.Response(200, content=CSV)
        if "servicios.ine.es" in str(request.url):
            return httpx.Response(200, json=IPV)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    tasado = valor_tasado.load(migrated_database, client)
    ipv = ine_ipv.load("13", migrated_database, client)
    assert (tasado["loaded"], tasado["municipalities"], tasado["empty"]) == (3, 2, 1)
    assert (ipv["loaded"], ipv["last"]) == (3, "2026T2")
    with psycopg.connect(migrated_database) as conn:
        value = conn.execute(
            "SELECT value FROM market_references WHERE source_id = %s AND code = '28079' "
            "AND year = 2025", (valor_tasado.SOURCE_ID,)).fetchone()[0]
        licence = conn.execute("SELECT license FROM sources WHERE id = %s",
                               (valor_tasado.SOURCE_ID,)).fetchone()[0]
    assert value == Decimal("4993.3")
    assert licence.startswith("CC BY 4.0") and "Ministerio de Vivienda" in licence


def test_ipc_de_alquiler_mensual_de_la_comunidad():
    def ipc(region, region_name, subgroup, subgroup_name, data_type, points):
        return {"Nombre": f"{region_name}. {subgroup_name}. {data_type}. ",
                "MetaData": [{"Codigo": region, "Nombre": region_name},
                             {"Codigo": subgroup, "Nombre": subgroup_name},
                             {"Codigo": "0" if data_type == "Índice" else "2",
                              "Nombre": data_type}],
                "Data": [{"Anyo": y, "T3_Periodo": p, "Valor": v} for y, p, v in points]}

    payload = [
        ipc("13", "Madrid, Comunidad de", "04.1", "Alquiler de vivienda", "Índice",
            [(2026, "M09", 103.426), (2026, "M08", 103.3)]),
        ipc("13", "Madrid, Comunidad de", "04.1", "Alquiler de vivienda", "Variación anual",
            [(2026, "M09", 2.9)]),
        ipc("13", "Madrid, Comunidad de", "04.5", "Electricidad, gas", "Índice",
            [(2026, "M09", 99.0)]),
        ipc("01", "Andalucía", "04.1", "Alquiler de vivienda", "Índice", [(2026, "M09", 101.0)]),
    ]
    rows = ine_ipc_alquiler.parse(payload, "13")
    assert {(r.year, r.month): r.value for r in rows} == {(2026, 9): Decimal("103.426"),
                                                          (2026, 8): Decimal("103.3")}
    assert all(r.measure == "ipc_alquiler" and r.quarter == 0 for r in rows)
