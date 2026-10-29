"""Prueba de oro de F1: el motor reproduce los planes manuales de F0 con menos de 1 € de error.

Cada plan es un YAML con la petición a `POST /simulate/investment` y las cifras esperadas por
clave. Los planes reales de F0 tienen datos personales y van en `tests/fixtures/private/planes/`
(ignorada por git); su versión anonimizada, en `tests/fixtures/planes/`.
"""

from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from housefinder.api.main import app

FIXTURES = Path(__file__).parent / "fixtures"
PLANS = sorted((FIXTURES / "planes").glob("*.yaml")) + sorted(
    (FIXTURES / "private" / "planes").glob("*.yaml")
)
TOLERANCE = {"EUR": Decimal(1), "EUR/mes": Decimal(1), "EUR/año": Decimal(1),
             "ratio": Decimal("0.0001"), "años": Decimal(0)}

client = TestClient(app)


@pytest.mark.parametrize("path", PLANS, ids=[p.stem for p in PLANS])
def test_el_motor_reproduce_el_plan_manual(path: Path):
    plan = yaml.safe_load(path.read_text(encoding="utf-8"))
    resp = client.post("/simulate/investment", json=plan["request"])
    assert resp.status_code == 200, resp.text
    figures = resp.json()["figures"]
    errors = []
    for key, expected in plan["expected"].items():
        assert key in figures, f"{path.name}: el motor no da la cifra {key}"
        fig = figures[key]
        diff = abs(Decimal(fig["value"]) - Decimal(str(expected)))
        if diff > TOLERANCE[fig["unit"]]:
            errors.append(f"{key}: motor {fig['value']} {fig['unit']}, plan {expected}")
    assert not errors, f"{path.name}:\n" + "\n".join(errors)
