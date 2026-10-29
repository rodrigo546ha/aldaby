"""Dirección de dependencias entre módulos (docs/PLAN_DISENO.md, §2).

Los motores son puros: solo importan `core`. Ni los motores, ni la normativa, ni los
parámetros llaman a un LLM ni hacen E/S de red.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "housefinder"

ALLOWED_INTERNAL = {
    "engines": {"core", "engines"},
    "regulation": {"core", "regulation", "engines"},  # engines solo por los tipos (TaxParams)
    "params": {"core", "params", "engines"},  # engines solo por los tipos (BankCriteria)
    "planning": {"core", "engines", "regulation", "params", "planning"},
    "core": {"core"},
    "db": {"core", "db"},
    "ingestion": {"core", "db", "ingestion"},
    "geo": {"core", "geo"},
    "territory": {"core", "db", "geo", "ingestion", "territory"},
}
FORBIDDEN_EXTERNAL = {"anthropic", "boto3", "botocore", "httpx", "requests", "openai", "fastapi"}
# Solo db/ habla con la base de datos (ADR-0008).
DB_DRIVERS = {"psycopg", "psycopg_pool"}
# Solo la ingesta descarga datos de la red.
ALLOWED_EXTERNAL = {"ingestion": {"httpx"}, "geo": {"httpx"}}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


@pytest.mark.parametrize("module", sorted(ALLOWED_INTERNAL))
def test_dependencias_permitidas(module: str):
    for file in sorted((PACKAGE / module).glob("*.py")):
        for name in _imports(file):
            top, _, rest = name.partition(".")
            if top == "housefinder":
                internal = rest.split(".")[0]
                assert internal in ALLOWED_INTERNAL[module], f"{file.name} importa {name}"
            else:
                allowed = ALLOWED_EXTERNAL.get(module, set())
                assert top not in FORBIDDEN_EXTERNAL - allowed, f"{file.name} importa {name}"
                if module != "db":
                    assert top not in DB_DRIVERS, f"{file.name} importa {name}"
