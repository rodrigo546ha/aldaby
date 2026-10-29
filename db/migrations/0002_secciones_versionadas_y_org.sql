-- HouseFinder · 0002: secciones censales por cartografía, organizaciones y reproducibilidad.
-- Ver docs/PLAN_DISENO.md (D9, D10) y ADR-0008. Las tablas tocadas están vacías al aplicarla.

-- Secciones: el INE publica una cartografía por año y los códigos cambian entre años. La
-- clave pasa a ser (código, año de la cartografía) y todo lo que cita una sección dice cuál.
ALTER TABLE census_sections DROP CONSTRAINT census_sections_pkey CASCADE;
ALTER TABLE census_sections ADD PRIMARY KEY (code, vintage);
ALTER TABLE census_sections ADD COLUMN source_id TEXT REFERENCES sources(id);

ALTER TABLE section_indicators DROP CONSTRAINT section_indicators_pkey;
ALTER TABLE section_indicators ADD COLUMN section_vintage INT NOT NULL;
ALTER TABLE section_indicators ALTER COLUMN section_code SET NOT NULL;
ALTER TABLE section_indicators ALTER COLUMN source_id SET NOT NULL;
ALTER TABLE section_indicators
    ADD PRIMARY KEY (section_code, section_vintage, indicator, year),
    ADD FOREIGN KEY (section_code, section_vintage) REFERENCES census_sections (code, vintage);

ALTER TABLE properties ADD COLUMN section_vintage INT;
ALTER TABLE properties
    ADD CONSTRAINT properties_section_fkey
    FOREIGN KEY (section_code, section_vintage) REFERENCES census_sections (code, vintage);

-- Organizaciones (D10): un particular es una organización de una persona; un profesional
-- gestiona varios perfiles dentro de la suya. Row-Level Security llega en G8.
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('particular', 'profesional')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE user_profiles ADD COLUMN org_id UUID NOT NULL REFERENCES organizations(id);
ALTER TABLE plans ADD COLUMN org_id UUID NOT NULL REFERENCES organizations(id);
-- Ofertas privadas (enlaces pegados) pertenecen a una organización; las públicas (BOE,
-- servicers) no.
ALTER TABLE offers ADD COLUMN org_id UUID REFERENCES organizations(id);
CREATE INDEX user_profiles_org_idx ON user_profiles (org_id);
CREATE INDEX plans_org_idx ON plans (org_id);

-- Reproducibilidad del plan (D9): con qué código, reglas y parámetros se calculó.
ALTER TABLE plans ADD COLUMN engine_version TEXT NOT NULL;  -- versión del paquete + commit
ALTER TABLE plans ADD COLUMN rules_digest TEXT NOT NULL;    -- sha256 de data/rules
ALTER TABLE plans ADD COLUMN params_digest TEXT NOT NULL;   -- sha256 de data/params
