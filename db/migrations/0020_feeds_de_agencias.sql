-- HouseFinder · 0020: feeds XML de agencias, con su consentimiento (ADR-0038).
-- La URL va cifrada como el perfil (ADR-0011): puede llevar usuario, contraseña o un token.

CREATE TABLE agency_feeds (
    id              UUID PRIMARY KEY,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agency_name     TEXT NOT NULL,
    url_enc         BYTEA NOT NULL,
    dek_enc         BYTEA NOT NULL,
    key_id          TEXT NOT NULL,
    enc_version     SMALLINT NOT NULL,
    -- Alcance que dio la agencia: solo esa organización, o todos los usuarios de Aldaby.
    scope           TEXT NOT NULL CHECK (scope IN ('organizacion', 'todos')),
    consent_on      DATE NOT NULL,
    consent_ref     TEXT NOT NULL,          -- documento firmado: contrato de alta, anexo…
    active          BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_run_at     TIMESTAMPTZ,
    last_report     JSONB                   -- informe del último trabajo, sin la URL
);
CREATE INDEX agency_feeds_org_idx ON agency_feeds (org_id);

ALTER TABLE agency_feeds ENABLE ROW LEVEL SECURITY;
CREATE POLICY agency_feeds_org ON agency_feeds
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
