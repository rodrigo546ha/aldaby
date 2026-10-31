"""Perfil del inversor: los datos personales que alimentan su plan.

Nunca se muestra en texto: `repr`, `str` y los errores de validación ocultan los valores
(ADR-0011). Para guardarlo se serializa y se cifra entero.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

REDACTED = "UserProfile(<redactado>)"


class ProfileError(ValueError):
    """Perfil no válido. El mensaje nombra los campos, nunca sus valores."""


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    net_monthly_income: Decimal = Field(ge=0)
    existing_monthly_debt: Decimal = Field(default=Decimal(0), ge=0)
    available_savings: Decimal = Field(ge=0)
    birth_year: int = Field(ge=1900, le=2100)
    residence: str = Field(pattern=r"^ES-\d{2}$")  # comunidad autónoma de residencia
    taxable_base: Decimal | None = Field(default=None, ge=0)  # base general sin el alquiler
    marginal_rate: Decimal | None = Field(default=None, ge=0, le=1)
    savings_base: Decimal = Field(default=Decimal(0), ge=0)
    descendant_birth_years: tuple[int, ...] = ()
    goal: Literal["renta", "patrimonio", "mixto"] | None = None
    horizon_years: int | None = Field(default=None, ge=1, le=50)
    risk_tolerance: Literal["baja", "media", "alta"] | None = None
    management: Literal["activa", "pasiva"] | None = None
    # Supuestos de búsqueda sin fuente oficial: los pone el usuario (ADR-0022), en tanto por uno
    vacancy_rate: Decimal | None = Field(default=None, ge=0, le=1)  # parte del año vacía
    management_fee_rate: Decimal | None = Field(default=None, ge=0, le=1)  # sobre la renta
    other_purchase_cost_rate: Decimal | None = Field(default=None, ge=0, le=1)  # gestoría, tasación
    sale_cost_rate: Decimal | None = Field(default=None, ge=0, le=1)  # agencia y gastos de venta
    min_monthly_cashflow: Decimal | None = None  # restricción de la búsqueda inversa (F6.5)
    large_holder: bool | None = None  # gran tenedor: cambia la reducción del IRPF del alquiler

    def __repr__(self) -> str:
        return REDACTED

    def __str__(self) -> str:
        return REDACTED

    def __format__(self, spec: str) -> str:
        return REDACTED

    @classmethod
    def parse(cls, data: dict[str, object] | bytes | str) -> UserProfile:
        """Valida el perfil. Si falla, `ProfileError` con los campos, sin los valores."""
        try:
            if isinstance(data, (bytes, str)):
                return cls.model_validate_json(data)
            return cls.model_validate(data)
        except ValidationError as exc:
            fields = sorted({".".join(str(p) for p in e["loc"]) or "perfil" for e in exc.errors()})
            raise ProfileError(f"Perfil no válido en: {', '.join(fields)}") from None
