"""Lectura de hojas de un `.xlsx` con la biblioteca estándar (ADR-0018).

Un `.xlsx` es un zip con XML. Se lee en streaming (`iterparse`), fila a fila, para ficheros grandes
como la base de datos del SERPAVI (una hoja de más de 200 MB de XML). Cada fila se devuelve como un
diccionario {cabecera: valor en texto}; las celdas vacías no aparecen en el XML y no aparecen aquí.
Las celdas se colocan por su referencia de columna («AB12»), no por su posición en la fila.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from pathlib import Path

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RELS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
COLUMN = re.compile(r"[A-Z]+")


def sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as book:
        return list(_sheet_paths(book))


def iter_rows(path: Path, sheet: str) -> Iterator[dict[str, str]]:
    """Filas de datos de la hoja `sheet`, con la primera fila como cabecera."""
    with zipfile.ZipFile(path) as book:
        paths = _sheet_paths(book)
        if sheet not in paths:
            raise KeyError(f"El libro no tiene la hoja «{sheet}» (tiene {', '.join(paths)})")
        strings = _shared_strings(book)
        header: dict[str, str] | None = None
        with book.open(paths[sheet]) as stream:
            for _, element in ET.iterparse(stream):
                if element.tag != MAIN + "row":
                    continue
                cells = _cells(element, strings)
                element.clear()
                if header is None:
                    header = cells
                    continue
                row = {header[col]: value for col, value in cells.items() if col in header}
                if row:
                    yield row


def _sheet_paths(book: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target", "") for r in rels.iter(PKG_RELS + "Relationship")}
    paths = {}
    for sheet in workbook.iter(MAIN + "sheet"):
        relative = target[sheet.get(RELS + "id")].lstrip("/")
        paths[sheet.get("name", "")] = relative if relative.startswith("xl/") else f"xl/{relative}"
    return paths


def _shared_strings(book: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in book.namelist():
        return []
    strings = []
    with book.open("xl/sharedStrings.xml") as stream:
        for _, element in ET.iterparse(stream):
            if element.tag == MAIN + "si":
                strings.append("".join(t.text or "" for t in element.iter(MAIN + "t")))
                element.clear()
    return strings


def _cells(row: ET.Element, strings: list[str]) -> dict[str, str]:
    cells = {}
    for cell in row.findall(MAIN + "c"):
        kind = cell.get("t")
        if kind == "inlineStr":
            value: str | None = "".join(t.text or "" for t in cell.iter(MAIN + "t"))
        else:
            raw = cell.find(MAIN + "v")
            value = None if raw is None or raw.text is None else (
                strings[int(raw.text)] if kind == "s" else raw.text)
        if value is not None and value != "":
            match = COLUMN.match(cell.get("r", ""))
            if match:
                cells[match.group(0)] = value
    return cells
