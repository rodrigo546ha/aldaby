"""Catálogo de tipos de regla (`kind`) con el esquema de sus parámetros.

Una regla de un tipo que no está aquí, o con parámetros que no encajan en su esquema,
no se carga. Este catálogo fija la FORMA de los parámetros; los valores legales viven
en data/rules/*.yaml con su fuente oficial (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Fraction = Annotated[Decimal, Field(ge=0, le=1)]  # tanto por uno
Amount = Annotated[Decimal, Field(ge=0)]  # euros
Condition = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]*$")]


class RuleParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class RateParams(RuleParams):
    """Un tipo único sobre una base (precio, valor catastral…)."""

    rate: Fraction


class Bracket(RuleParams):
    from_amount: Amount = Field(alias="from")  # base desde la que se aplica `rate`
    rate: Fraction


class BracketScale(RuleParams):
    """Escala por tramos: cada tipo se aplica a la parte de la base desde `from`."""

    brackets: tuple[Bracket, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _ordered(self) -> BracketScale:
        if self.brackets[0].from_amount != 0:
            raise ValueError("el primer tramo debe empezar en 0")
        starts = [b.from_amount for b in self.brackets]
        if any(a >= b for a, b in zip(starts, starts[1:], strict=False)):
            raise ValueError("los inicios de tramo deben ser estrictamente crecientes")
        return self


class ReductionCase(RuleParams):
    condition: Condition  # "general" o un caso concreto ("zona-tensionada-rebaja-renta"…)
    reduction: Fraction


class ReductionCases(RuleParams):
    """Reducción que depende de condiciones; siempre hay un caso «general»."""

    cases: tuple[ReductionCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _general(self) -> ReductionCases:
        conditions = [c.condition for c in self.cases]
        if len(set(conditions)) != len(conditions):
            raise ValueError("condiciones repetidas")
        if "general" not in conditions:
            raise ValueError("falta el caso 'general'")
        return self

    def case(self, condition: str) -> ReductionCase:
        for c in self.cases:
            if c.condition == condition:
                return c
        raise KeyError(condition)


@dataclass(frozen=True)
class KindSpec:
    params: type[RuleParams]
    description: str


KINDS: dict[str, KindSpec] = {
    "impuesto_compra_segunda_mano": KindSpec(
        RateParams, "Impuesto de compra de vivienda usada (ITP) sobre el precio"
    ),
    "iva_vivienda_nueva": KindSpec(RateParams, "IVA de la compra de vivienda nueva"),
    "ajd_vivienda_nueva": KindSpec(
        RateParams, "Actos jurídicos documentados de la compra de vivienda nueva"
    ),
    "reduccion_irpf_alquiler": KindSpec(
        ReductionCases, "Reducción del rendimiento neto positivo del alquiler de vivienda"
    ),
    "amortizacion_inmueble_alquiler": KindSpec(
        RateParams, "Amortización fiscal anual del inmueble alquilado"
    ),
    "escala_irpf_general": KindSpec(BracketScale, "Escala de la base liquidable general"),
    "escala_irpf_ahorro": KindSpec(BracketScale, "Escala de la base liquidable del ahorro"),
    "tipo_ibi": KindSpec(RateParams, "Tipo del IBI sobre el valor catastral"),
}


def parse_params(kind: str, params: dict[str, Any]) -> RuleParams:
    """Parámetros de una regla validados contra el esquema de su tipo."""
    spec = KINDS.get(kind)
    if spec is None:
        raise ValueError(f"tipo de regla desconocido: {kind!r}")
    try:
        return spec.params.model_validate(params)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or kind}: {e['msg']}" for e in exc.errors()
        )
        raise ValueError(f"parámetros no válidos para {kind}: {details}") from exc
