"""Catálogo de tipos de regla (`kind`) con el esquema de sus parámetros.

Una regla de un tipo que no está aquí, o con parámetros que no encajan en su esquema,
no se carga. Este catálogo fija la FORMA de los parámetros; los valores legales viven
en data/rules/*.yaml con su fuente oficial (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


class TransferTaxParams(RuleParams):
    """ITP de inmuebles: un tipo único sobre todo el precio (`rate`) o tramos (`brackets`), una
    de las dos. Los tramos son progresivos (cada tipo solo en la parte del precio de su tramo, como
    en Cataluña) salvo con `whole_value: true`, en que el tipo del tramo del precio se aplica a todo
    el precio (como en la Comunitat Valenciana por encima de un millón)."""

    rate: Fraction | None = None
    brackets: tuple[Bracket, ...] | None = None
    whole_value: bool = False

    @model_validator(mode="after")
    def _one_of(self) -> TransferTaxParams:
        if (self.rate is None) == (self.brackets is None):
            raise ValueError("el ITP lleva `rate` o `brackets`, uno de los dos")
        if self.brackets is not None:
            BracketScale(brackets=self.brackets)  # mismas comprobaciones que una escala
        elif self.whole_value:
            raise ValueError("`whole_value` solo tiene sentido con `brackets`")
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


class TaxpayerMinimum(RuleParams):
    """Mínimo del contribuyente (Ley del IRPF, art. 57, o el autonómico que lo sustituya)."""

    general: Amount
    over_65_extra: Amount  # aumento si tiene más de 65 años
    over_75_extra: Amount  # aumento adicional si tiene más de 75 años


class DescendantsMinimum(RuleParams):
    """Mínimo por descendientes (Ley del IRPF, art. 58, o el autonómico que lo sustituya)."""

    first: Amount
    second: Amount
    third: Amount
    fourth_and_more: Amount  # por el cuarto y cada uno de los siguientes
    under_3_extra: Amount  # aumento por cada descendiente menor de tres años


class InterestRepairLimit(RuleParams):
    """Límite de intereses y gastos de reparación y conservación: no pueden superar los
    rendimientos íntegros del inmueble; el exceso se arrastra `carryforward_years` años."""

    carryforward_years: int = Field(gt=0)


class ZoneDeclaration(RuleParams):
    """Si el territorio es zona de mercado residencial tensionado (Ley 12/2023, art. 18).

    `checked_through`: fecha de la última resolución trimestral del Ministerio revisada.
    `area`: el ámbito declarado cuando no es todo el municipio (barrios, núcleos), como lo nombra
    la resolución.
    """

    declared: bool
    checked_through: date
    area: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _area_if_declared(self) -> ZoneDeclaration:
        if self.area is not None and not self.declared:
            raise ValueError("`area` solo tiene sentido con `declared: true`")
        return self


class Requirement(RuleParams):
    code: Condition  # identificador estable: «aprobacion-previa-comunidad»
    description: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https?://")


class RentalRegime(RuleParams):
    """Régimen jurídico de un tipo de alquiler y requisitos para ejercerlo.

    Los requisitos se suman entre niveles (estatal, autonómico, municipal).
    """

    regime: str = Field(min_length=1)
    allowed: bool = True  # False: el tipo de alquiler no se puede ejercer en el territorio
    requirements: tuple[Requirement, ...] = ()
    # Si la renta tiene la reducción del art. 23.2 de la Ley del IRPF (alquiler de vivienda).
    # None en un nivel: ese nivel no lo dice; en todos: por confirmar (ADR-0024)
    irpf_reduction: bool | None = None
    tax_note: str | None = Field(default=None, min_length=1)  # trato fiscal que no se modela



class FeeBand(RuleParams):
    from_amount: Amount = Field(alias="from")  # valor por encima del cual se aplica `rate`
    rate: Fraction  # sobre el exceso (4,5 por mil = 0.0045)


class FeeScale(RuleParams):
    """Arancel por tramos de valor (notarios, registradores).

    Hasta el primer `from`, una cantidad fija; después, cada tipo sobre el exceso de su tramo.
    El total se limita a [`min_fee`, `max_fee`] y luego se aplica la rebaja `rebate`.
    Por encima de `max_base` el arancel no fija la cantidad (pacto libre).
    """

    base_fee: Amount  # cantidad fija por el primer tramo
    bands: tuple[FeeBand, ...] = Field(min_length=1)
    min_fee: Amount | None = None
    max_fee: Amount | None = None
    max_base: Amount | None = None
    rebate: Fraction = Decimal(0)

    @model_validator(mode="after")
    def _ordered(self) -> FeeScale:
        starts = [b.from_amount for b in self.bands]
        if any(a >= b for a, b in zip(starts, starts[1:], strict=False)):
            raise ValueError("los inicios de tramo deben ser estrictamente crecientes")
        if self.min_fee is not None and self.max_fee is not None and self.min_fee > self.max_fee:
            raise ValueError("min_fee no puede superar max_fee")
        return self


class RateBand(RuleParams):
    up_to: Amount | None  # valor máximo de la banda, incluido; None = sin límite
    rate: Fraction


class BandedRate(RuleParams):
    """Tipo único que depende de la banda de valor y se aplica a TODA la base.

    `cap_jumps`: si al pasar de banda la cuota sube más que la base, se reduce el exceso
    (DL 1/2010 de Madrid, art. 37). `legal_person_rate`: tipo cuando el adquirente no es
    persona física, si la norma lo distingue.
    """

    bands: tuple[RateBand, ...] = Field(min_length=1)
    cap_jumps: bool = False
    legal_person_rate: Fraction | None = None

    @model_validator(mode="after")
    def _ordered(self) -> BandedRate:
        limits = [b.up_to for b in self.bands]
        if limits[-1] is not None or any(lim is None for lim in limits[:-1]):
            raise ValueError("solo la última banda puede no tener límite, y debe no tenerlo")
        bounded = [lim for lim in limits if lim is not None]
        if any(a >= b for a, b in zip(bounded, bounded[1:], strict=False)):
            raise ValueError("los límites de banda deben ser estrictamente crecientes")
        return self


class GainsCoefficients(RuleParams):
    """Coeficientes de la plusvalía municipal por periodo de generación (TRLRHL, art. 107.4).

    `by_years[0]` es el de menos de un año (se prorratea por meses completos), `by_years[n]`
    el de n años y el último, el de 20 años o más.
    """

    by_years: tuple[Fraction, ...] = Field(min_length=21, max_length=21)


class DeedPayer(RuleParams):
    """Quién paga, salvo pacto, el otorgamiento de la escritura de compraventa."""

    deed: Literal["vendedor", "comprador"]
    first_copy: Literal["vendedor", "comprador"]


class ByLandlord(RuleParams):
    """Un plazo que depende de si el arrendador es persona física o jurídica."""

    natural_person: int = Field(gt=0)
    legal_person: int = Field(gt=0)


class NonRenewalCompensation(RuleParams):
    """Indemnización al arrendatario si el arrendador no prorroga: la mayor de
    `flat_months` mensualidades o `months_per_year` mensualidades por año de residencia,
    calculadas sobre `basis`. No procede en los casos de `exceptions`."""

    flat_months: Decimal = Field(gt=0)
    months_per_year: Decimal = Field(gt=0)
    basis: str = Field(min_length=1)
    exceptions: tuple[Condition, ...] = ()


class LeaseExtension(RuleParams):
    """Duración mínima, prórroga tácita y preaviso del alquiler de vivienda habitual
    (LAU, arts. 9 y 10)."""

    minimum_years: ByLandlord
    tacit_period_years: ByLandlord  # duración de cada prórroga tácita
    tacit_max_years: int | None = Field(gt=0)  # None: prórrogas sucesivas sin límite
    landlord_notice_months: int = Field(gt=0)
    tenant_notice_months: int = Field(gt=0)
    compensation: NonRenewalCompensation | None = None

RENTAL_TYPES = ("habitual", "temporada", "habitaciones", "turistico")


@dataclass(frozen=True)
class KindSpec:
    params: type[RuleParams]
    description: str


KINDS: dict[str, KindSpec] = {
    "impuesto_compra_segunda_mano": KindSpec(
        TransferTaxParams,
        "Impuesto de compra de vivienda usada (ITP): tipo único o escala progresiva por tramos",
    ),
    "iva_vivienda_nueva": KindSpec(RateParams, "IVA de la compra de vivienda nueva"),
    "iva_tipo_general": KindSpec(RateParams, "Tipo general del IVA (honorarios, servicios)"),
    "ajd_compra_vivienda": KindSpec(
        BandedRate, "AJD de la escritura de compra de vivienda sujeta a IVA"
    ),
    "arancel_notarial": KindSpec(FeeScale, "Arancel notarial de los documentos de cuantía"),
    "arancel_registral": KindSpec(FeeScale, "Arancel registral de las inscripciones"),
    "pagador_escritura_compraventa": KindSpec(
        DeedPayer, "Quién paga la escritura de compraventa y su primera copia, salvo pacto"
    ),
    "reduccion_irpf_alquiler": KindSpec(
        ReductionCases, "Reducción del rendimiento neto positivo del alquiler de vivienda"
    ),
    "amortizacion_inmueble_alquiler": KindSpec(
        RateParams, "Amortización fiscal anual del inmueble alquilado"
    ),
    # Estatal y autonómica son tipos distintos: una comunidad sin escala cargada no hereda la
    # estatal (ADR-0007). Los mínimos sí se heredan: la parte autonómica usa los estatales
    # salvo que la comunidad los sustituya (Ley del IRPF, art. 56.3).
    "escala_irpf_general_estatal": KindSpec(
        BracketScale, "Escala estatal de la base liquidable general"
    ),
    "escala_irpf_general_autonomica": KindSpec(
        BracketScale, "Escala autonómica de la base liquidable general"
    ),
    "escala_irpf_ahorro_estatal": KindSpec(
        BracketScale, "Escala estatal de la base liquidable del ahorro"
    ),
    "escala_irpf_ahorro_autonomica": KindSpec(
        BracketScale, "Escala autonómica de la base liquidable del ahorro"
    ),
    "minimo_contribuyente": KindSpec(TaxpayerMinimum, "Mínimo del contribuyente en el IRPF"),
    "minimo_descendientes": KindSpec(DescendantsMinimum, "Mínimo por descendientes en el IRPF"),
    "limite_intereses_reparacion": KindSpec(
        InterestRepairLimit,
        "Límite de intereses y gastos de reparación en el rendimiento del capital inmobiliario",
    ),
    "zona_tensionada": KindSpec(
        ZoneDeclaration, "Declaración de zona de mercado residencial tensionado"
    ),
    # Un tipo de regla por tipo de alquiler: así cada uno tiene su vigencia sin solaparse.
    "regimen_alquiler_habitual": KindSpec(RentalRegime, "Alquiler de vivienda habitual"),
    "regimen_alquiler_temporada": KindSpec(RentalRegime, "Alquiler de temporada o temporal"),
    "regimen_alquiler_habitaciones": KindSpec(RentalRegime, "Alquiler por habitaciones"),
    "regimen_alquiler_turistico": KindSpec(RentalRegime, "Alquiler de uso turístico"),
    "prorroga_alquiler_habitual": KindSpec(
        LeaseExtension, "Duración mínima, prórroga tácita y preaviso del alquiler de vivienda"
    ),
    "tipo_ibi": KindSpec(RateParams, "Tipo del IBI sobre el valor catastral"),
    # Los coeficientes máximos son estatales; un municipio que fije otros menores carga una
    # regla propia del mismo tipo, que gana por ser más específica.
    "coeficientes_plusvalia": KindSpec(
        GainsCoefficients, "Coeficientes de la plusvalía municipal por años de tenencia"
    ),
    "tipo_plusvalia": KindSpec(RateParams, "Tipo de gravamen de la plusvalía municipal"),
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
