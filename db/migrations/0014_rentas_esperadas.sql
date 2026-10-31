-- HouseFinder · 0014: lo que el usuario espera sacar de una oferta con un tipo de alquiler sin
-- renta pública (ADR-0024). Es un supuesto suyo, por organización y oferta (también los lotes del
-- BOE, que son públicos): ingreso medio mensual a lo largo del año, con los meses vacíos y sin
-- limpieza, suministros ni comisiones de las plataformas.
CREATE TABLE offer_rent_expectations (
    org_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    offer_id       UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    rental_type    TEXT NOT NULL CHECK (rental_type IN ('temporada', 'habitaciones', 'turistico')),
    monthly_income NUMERIC NOT NULL CHECK (monthly_income > 0),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, offer_id, rental_type)
);
