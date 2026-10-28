"""Catálogo de tipos de regla (`kind`) con el esquema de sus parámetros.

Una regla de un tipo que no está aquí, o con parámetros que no encajan en su esquema,
no se carga. Este catálogo fija la FORMA de los parámetros; los valores legales viven
en data/rules/*.yaml con su fuente oficial (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any, Literal

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


ContractType = Literal["primer-alquiler", "nuevo-contrato", "prorroga-tacita"]
RentChange = Literal[
    "rebaja-mas-5",  # renta inicial rebajada más de un 5 % respecto de la última
    "no-superior",  # no superior a la última renta (incluye rebajas de hasta el 5 %)
    "subida-hasta-5",
    "subida-5-a-10",
    "subida-10-a-15",
    "subida-15-a-20",
    "subida-mas-de-20",
]


class RentalFacts(RuleParams):
    """Situación de un contrato de alquiler de vivienda, en el vocabulario de las reglas.

    Los hechos que no se conocen valen False: solo desbloquean reducciones mayores, así que
    suponerlos falsos nunca da una reducción que no se pueda justificar. `large_holder` es
    obligatorio porque suponerlo falso sí podría darla.
    """

    contract: ContractType
    large_holder: bool  # gran tenedor (art. 3.k de la Ley 12/2023)
    rent_change: RentChange | None = None  # solo en «nuevo-contrato»
    below_reference_index: bool = False  # renta por debajo del índice de referencia
    stressed_zone: bool = False  # zona de mercado residencial tensionado declarada
    young_tenant: bool = False  # arrendatario de 18 a 35 años
    public_or_social_tenant: bool = False  # Administración, entidad sin fines lucrativos…
    recent_rehabilitation: bool = False  # rehabilitación terminada en los dos años anteriores
    same_tenant_after_term: bool = False  # nuevo contrato con el mismo arrendatario al acabar


class RentalConditions(RuleParams):
    """Hechos que exige un caso; los que no aparecen dan igual."""

    contract: ContractType | None = None
    large_holder: bool | None = None
    rent_change: RentChange | None = None
    below_reference_index: bool | None = None
    stressed_zone: bool | None = None
    young_tenant: bool | None = None
    public_or_social_tenant: bool | None = None
    recent_rehabilitation: bool | None = None
    same_tenant_after_term: bool | None = None

    def matches(self, facts: RentalFacts) -> bool:
        required = self.model_dump(exclude_none=True)
        return all(getattr(facts, name) == value for name, value in required.items())


class ReductionCase(RuleParams):
    condition: Condition  # nombre del supuesto ("general", "zona-tensionada-rebaja-renta"…)
    reduction: Fraction
    when: RentalConditions = RentalConditions()  # sin condiciones = se aplica siempre


class ReductionCases(RuleParams):
    """Reducción que depende de condiciones (un caso por supuesto de la norma).

    No se exige un caso «general»: hay redacciones sin supuesto residual (p. ej. el
    art. 23.2 de la Ley del IRPF tras el Real Decreto-ley 29/2026).
    """

    cases: tuple[ReductionCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> ReductionCases:
        conditions = [c.condition for c in self.cases]
        if len(set(conditions)) != len(conditions):
            raise ValueError("condiciones repetidas")
        return self

    def case(self, condition: str) -> ReductionCase:
        for c in self.cases:
            if c.condition == condition:
                return c
        raise KeyError(condition)

    def best(self, facts: RentalFacts) -> ReductionCase | None:
        """Caso de mayor reducción entre los que cumple la situación; None si ninguno.

        La norma aplica «la reducción de mayor cuantía» cuando se cumplen varios supuestos.
        """
        matching = [c for c in self.cases if c.when.matches(facts)]
        return max(matching, key=lambda c: c.reduction) if matching else None


@dataclass(frozen=True)
class KindSpec:
    params: type[RuleParams]
    description: str


# AJD de vivienda nueva: pendiente. En Madrid el tipo depende del valor y se aplica al total
# (art. 32 del DL 1/2010), una forma que no es ni tasa única ni escala por tramos.
KINDS: dict[str, KindSpec] = {
    "impuesto_compra_segunda_mano": KindSpec(
        RateParams, "Impuesto de compra de vivienda usada (ITP) sobre el precio"
    ),
    "iva_vivienda_nueva": KindSpec(RateParams, "IVA de la compra de vivienda nueva"),
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
