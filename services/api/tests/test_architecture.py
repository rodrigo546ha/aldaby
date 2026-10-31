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
    "jobs": {"agent", "core", "db", "ingestion", "jobs", "offers", "watch"},
    "watch": {"core", "db", "ingestion", "watch"},
    "crypto": {"core", "crypto"},
    "profiles": {"agent", "core", "crypto", "db", "profiles"},  # extracción de la entrevista
    "offers": {"agent", "core", "db", "geo", "ingestion", "offers", "territory"},
    "valuation": {"core", "db", "engines", "params", "valuation"},
    "agent": {"agent", "core"},
    "advisor": {"advisor", "agent", "core", "crypto", "db", "params", "plans", "profiles",
                "regulation", "search", "territory", "valuation"},
    "documents": {"core", "documents"},
    # Orquesta la búsqueda inversa (F6.5): valoración, supuestos y el plan de planning/
    # engines solo por los tipos (MortgageTerms, la comparación del plan completo)
    "search": {"core", "db", "engines", "params", "planning", "profiles", "regulation", "search",
               "valuation"},
    # Plan completo (F6.7): el camino de la búsqueda más estrés, pendientes, argumentos y pasos
    "plans": {"core", "db", "engines", "params", "planning", "plans", "profiles", "regulation",
              "search", "valuation"},
    # PDF del plan (F6.8): el plan, las fuentes de reglas, parámetros y datos
    "reports": {"core", "db", "params", "planning", "plans", "regulation", "reports"},
    # Evaluaciones (F6.9): el asesor, la extracción y el plan, con el perfil de desarrollo
    "evaluations": {"advisor", "agent", "core", "crypto", "db", "evaluations", "params", "plans",
                    "profiles", "regulation", "search"},
}
FORBIDDEN_EXTERNAL = {"anthropic", "boto3", "botocore", "httpx", "requests", "openai", "fastapi",
                      "pypdf", "pypdfium2", "pytesseract", "PIL", "xlrd", "weasyprint"}
# Solo db/ habla con la base de datos (ADR-0008).
DB_DRIVERS = {"psycopg", "psycopg_pool"}
# Solo la ingesta descarga datos de la red.
# La ingesta lee además PDF y Excel antiguos de fuentes públicas (ADR-0022).
ALLOWED_EXTERNAL = {"ingestion": {"httpx", "pypdf", "xlrd"}, "geo": {"httpx"}, "jobs": {"httpx"},
                    "watch": {"httpx"}, "offers": {"httpx"}, "agent": {"httpx"},
                    # Solo documents/ lee PDF y hace OCR (ADR-0021)
                    "documents": {"pypdf", "pypdfium2", "pytesseract", "PIL"},
                    # Solo reports/ genera PDF (ADR-0026)
                    "reports": {"weasyprint"}}


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
    for file in sorted((PACKAGE / module).rglob("*.py")):
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
