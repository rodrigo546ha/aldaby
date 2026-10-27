"""API HTTP de HouseFinder (fase 1: simuladores; el resto llega por fases)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from housefinder.core.figures import SourceRef
from housefinder.engines import mortgage
from housefinder.params.bank import bank_criteria
from housefinder.params.book import ParamBook, default_params_dir

app = FastAPI(title="HouseFinder API", version="0.1.0")

# La capacidad de compra aún no depende de la ubicación: criterios de ámbito nacional.
AFFORDABILITY_TERRITORY = "ES"


@lru_cache
def get_param_book() -> ParamBook:
    return ParamBook.from_dir(default_params_dir())


ParamBookDep = Annotated[ParamBook, Depends(get_param_book)]


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
def simulate_affordability(req: AffordabilityRequest, params: ParamBookDep) -> dict:
    try:
        criteria = bank_criteria(params, AFFORDABILITY_TERRITORY, date.today())
    except LookupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
            criteria=criteria,
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
