"""API HTTP de HouseFinder (fase 1: simuladores; el resto llega por fases)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from housefinder.core.figures import SourceRef
from housefinder.engines import mortgage

app = FastAPI(title="HouseFinder API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class AffordabilityRequest(BaseModel):
    net_monthly_income: Decimal = Field(gt=0)
    existing_monthly_debt: Decimal = Field(ge=0, default=Decimal(0))
    available_savings: Decimal = Field(ge=0)
    age: int = Field(ge=18, le=90)
    annual_rate: Decimal = Field(ge=0, le=Decimal("0.2"))
    # Mientras no esté el motor fiscal, el cliente envía la tasa de gastos de compra.
    purchase_cost_rate: Decimal = Field(ge=0, le=Decimal("0.3"))


@app.post("/simulate/affordability")
def simulate_affordability(req: AffordabilityRequest) -> dict:
    try:
        result = mortgage.affordability(
            mortgage.BuyerFinances(
                net_monthly_income=req.net_monthly_income,
                existing_monthly_debt=req.existing_monthly_debt,
                available_savings=req.available_savings,
                age=req.age,
            ),
            annual_rate=req.annual_rate,
            purchase_cost_rate=req.purchase_cost_rate,
            rate_sources=(SourceRef("user_input", "tipo-de-interes"),),
            # PROVISIONAL hasta que el motor de normativa resuelva los gastos de compra (F2.7).
            purchase_cost_sources=(
                SourceRef("user_input", "tasa-de-gastos-de-compra", provisional=True),
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "max_price": result.max_price.to_dict(),
        "max_loan": result.max_loan.to_dict(),
        "max_payment": result.max_payment.to_dict(),
        "years": result.years.to_dict(),
        "binding_constraint": result.binding_constraint,
    }
