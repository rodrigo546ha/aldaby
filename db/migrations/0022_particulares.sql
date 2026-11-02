-- HouseFinder · 0022: particulares (F8.1 y F8.2, ADR-0041): rol, lista de espera y planes completos
-- usados en el nivel gratuito.

ALTER TABLE accounts DROP CONSTRAINT accounts_role_check;
ALTER TABLE accounts ADD CONSTRAINT accounts_role_check
    CHECK (role IN ('admin', 'profesional', 'particular'));

-- Lista de espera de la página de presentación. Sin IP ni navegador.
CREATE TABLE waitlist (
    email            TEXT PRIMARY KEY CHECK (email = lower(email)),
    kind             TEXT NOT NULL CHECK (kind IN ('particular', 'profesional')),
    privacy_version  INTEGER NOT NULL,      -- versión de la política de privacidad aceptada
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    invited_at       TIMESTAMPTZ            -- cuando el administrador dio el alta
);

-- Ofertas con plan completo abierto por una organización: el nivel gratuito tiene un tope.
CREATE TABLE plan_uses (
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    offer_id    UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    first_used  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, offer_id)
);
ALTER TABLE plan_uses ENABLE ROW LEVEL SECURITY;
CREATE POLICY plan_uses_org ON plan_uses USING (org_id = app_org()) WITH CHECK (org_id = app_org());
