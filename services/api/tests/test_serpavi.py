"""SERPAVI (F5.2, ADR-0018): lector de .xlsx sin dependencias y carga de las referencias de
alquiler. El libro de prueba imita al real (una hoja por nivel, una columna por medida y año) con
los valores reales de 2024 de la sección 2807901001 (Madrid, Centro)."""

import zipfile
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from housefinder.ingestion import serpavi
from housefinder.ingestion.xlsx import iter_rows, sheet_names

HEADER = ["CPRO", "LITPRO", "CUMUN", "LITMUN", "CUSEC", "BI_ALVHEPCO_TVC_24",
          "BI_ALVHEPCO_TVU_24", "ALQM2_LV_M_VC_24", "ALQM2_LV_25_VC_24", "ALQM2_LV_75_VC_24",
          "ALQTBID12_M_VC_24", "SLVM2_M_VC_24", "ALQM2_LV_M_VU_24"]
MADRID_1001 = ["28", "Madrid", "28079", "Madrid", "2807901001", "169", "0",
               "17.815448651571845", "12.951090274009767", "21.59976870748299",
               "1276.6666666666667", "74", None]  # unifamiliar sin dato: menos de 10


def column(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def write_xlsx(path: Path, sheets: dict[str, list[list[str | None]]]) -> Path:
    """Libro mínimo con cadenas compartidas, como los que exporta Excel."""
    strings: list[str] = []

    def cell(ref: str, value: str | None) -> str:
        if value is None:
            return ""  # Excel no escribe las celdas vacías
        try:
            float(value)
            return f'<c r="{ref}"><v>{value}</v></c>'
        except ValueError:
            strings.append(value)
            return f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>'

    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path, "w") as book:
        entries, rels = [], []
        for n, (name, rows) in enumerate(sheets.items(), start=1):
            xml_rows = "".join(
                f'<row r="{i}">' + "".join(cell(f"{column(j)}{i}", v) for j, v in enumerate(row))
                + "</row>" for i, row in enumerate(rows, start=1))
            sheet_xml = f'<worksheet xmlns="{main}"><sheetData>{xml_rows}</sheetData></worksheet>'
            book.writestr(f"xl/worksheets/sheet{n}.xml", sheet_xml)
            entries.append(f'<sheet name="{escape(name)}" sheetId="{n}" r:id="rId{n}"/>')
            rels.append(f'<Relationship Id="rId{n}" Target="worksheets/sheet{n}.xml" '
                        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                        'relationships/worksheet"/>')
        book.writestr("xl/workbook.xml", f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets>'
                      + "".join(entries) + "</sheets></workbook>")
        book.writestr("xl/_rels/workbook.xml.rels",
                      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                      'relationships">' + "".join(rels) + "</Relationships>")
        book.writestr("xl/sharedStrings.xml", f'<sst xmlns="{main}">' + "".join(
            f"<si><t>{escape(s)}</t></si>" for s in strings) + "</sst>")
    return path


@pytest.fixture
def book(tmp_path: Path) -> Path:
    municipal = ["CPRO", "NPRO", "CUMUN", "NMUN", "BI_ALVHEPCO_TVC_24", "ALQM2_LV_M_VC_24"]
    return write_xlsx(tmp_path / "serpavi.xlsx", {
        "Metadatos": [["Sistema Estatal Índices Alquiler de Vivienda"]],
        "Secciones censales": [
            HEADER, MADRID_1001,
            ["01", "Araba/Álava", "01001", "Alegría-Dulantzi", "0100101001", "34", "13", "5.79"],
        ],
        "Distritos": [["CPRO", "LITPRO", "CUMUN", "LITMUN", "CUDIS", "ALQM2_LV_M_VC_24"],
                      ["28", "Madrid", "28079", "Madrid", "2807901", "17.5"]],
        "Municipios": [municipal, ["28", "Madrid", "28079", "Madrid", "198000", "16.9"]],
        "Provincias": [["CPRO", "LITPRO", "ALQM2_LV_M_VC_24"], ["28", "Madrid", "15.1"]],
    })


def test_lector_de_xlsx(book: Path):
    assert sheet_names(book)[0] == "Metadatos"
    rows = list(iter_rows(book, "Secciones censales"))
    assert rows[0]["CUSEC"] == "2807901001"
    assert rows[0]["ALQM2_LV_M_VC_24"] == "17.815448651571845"
    assert "ALQM2_LV_M_VU_24" not in rows[0]  # celda vacía: no aparece
    assert rows[1]["LITPRO"] == "Araba/Álava"
    with pytest.raises(KeyError, match="no tiene la hoja"):
        list(iter_rows(book, "Barrios"))


def test_solo_la_provincia_pedida_y_cada_columna_en_su_medida(book: Path):
    parsed = serpavi.parse(book, "28")
    assert dict(parsed.territories) == {"seccion": 1, "distrito": 1, "municipio": 1,
                                        "provincia": 1}
    section = {(r.measure, r.typology, r.stat): r.value
               for r in parsed.rows if r.code == "2807901001"}
    assert section[("renta_m2_mes", "colectiva", "mediana")] == Decimal("17.8154")
    assert section[("renta_m2_mes", "colectiva", "p25")] == Decimal("12.9511")
    assert section[("renta_m2_mes", "colectiva", "p75")] == Decimal("21.5998")
    assert section[("renta_mes", "colectiva", "mediana")] == Decimal("1276.6667")
    assert section[("superficie", "colectiva", "mediana")] == Decimal("74")
    assert section[("alquileres", "colectiva", "n")] == Decimal("169")
    assert section[("alquileres", "unifamiliar", "n")] == Decimal("0")
    assert ("renta_m2_mes", "unifamiliar", "mediana") not in section
    assert parsed.years == [2024]
    assert all(r.vintage == 2021 and r.year == 2024 for r in parsed.rows)
    assert not any(r.code.startswith("01") for r in parsed.rows)  # Álava no


psycopg = pytest.importorskip("psycopg")


@pytest.mark.db
def test_carga_idempotente(book: Path, migrated_database: str):
    from conftest import add_section

    add_section(migrated_database, "2807901001", -3.70, 40.41)  # cartografía 2025 de prueba
    cache = book.parent / "cache"
    cache.mkdir()
    (cache / "serpavi.xlsx").write_bytes(book.read_bytes())
    url = "https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/serpavi.xlsx"
    first = serpavi.load("28", migrated_database, url, cache)  # sin red: ya está en la caché
    again = serpavi.load("28", migrated_database, url, cache)
    # Sección: 2 recuentos, 3 percentiles de renta €/m², renta mensual y superficie (7);
    # distrito 1; municipio 2; provincia 1. Álava no.
    assert first["loaded"] == again["loaded"] == 11
    assert first["sections_without_map"] == 1  # la sección de prueba está en 2025, no en 2021
    with psycopg.connect(migrated_database) as conn:
        rows = conn.execute(
            "SELECT level, value, unit FROM market_references WHERE source_id = 'serpavi' "
            "AND measure = 'renta_m2_mes' AND stat = 'mediana' ORDER BY level").fetchall()
        source = conn.execute("SELECT license, notes FROM sources WHERE id = 'serpavi'").fetchone()
    assert rows == [("distrito", Decimal("17.5000"), "EUR/m2 mes"),
                    ("municipio", Decimal("16.9000"), "EUR/m2 mes"),
                    ("provincia", Decimal("15.1000"), "EUR/m2 mes"),
                    ("seccion", Decimal("17.8154"), "EUR/m2 mes")]
    assert source[0].startswith("Aviso legal del Ministerio") and "sha256" in source[1]


@pytest.mark.db
def test_cargar_una_provincia_no_borra_las_demas(migrated_database: str):
    """Una carga por provincia o comunidad solo sustituye lo suyo (antes borraba toda la fuente)."""
    from datetime import UTC, datetime

    import psycopg

    from housefinder.db.references import ReferenceRow, replace_references
    from housefinder.db.sections import SourceRecord

    source = SourceRecord("prueba-ambito", "Prueba", "https://x", "CC BY", datetime.now(UTC))

    def row(code: str, value: str) -> ReferenceRow:
        return ReferenceRow("provincia", code, None, 2024, 0, "renta_m2_mes", "colectiva",
                            "mediana", Decimal(value), "EUR/m2 mes")

    with psycopg.connect(migrated_database) as conn:
        replace_references(conn, source, [row("28", "15")], scope="28")
        replace_references(conn, source, [row("08", "17")], scope="08")
        replace_references(conn, source, [row("28", "16")], scope="28")  # Madrid otra vez
        values = dict(conn.execute(
            "SELECT code, value FROM market_references WHERE source_id = 'prueba-ambito'"
        ).fetchall())
        assert values == {"28": Decimal("16"), "08": Decimal("17")}
        replace_references(conn, source, [row("46", "12")])  # sin ámbito: la serie entera
        codes = {r[0] for r in conn.execute(
            "SELECT code FROM market_references WHERE source_id = 'prueba-ambito'").fetchall()}
        assert codes == {"46"}
        conn.rollback()
