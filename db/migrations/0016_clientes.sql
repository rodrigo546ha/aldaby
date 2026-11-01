-- HouseFinder · 0016: varios clientes por profesional (F7.2, ADR-0029). El nombre se cifra como el
-- perfil (ADR-0011); perfiles y entrevistas pasan a ser de un cliente y se borran con él.

CREATE TABLE clients (
    id           UUID PRIMARY KEY,
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name_enc     BYTEA NOT NULL,
    dek_enc      BYTEA NOT NULL,
    key_id       TEXT NOT NULL,
    enc_version  SMALLINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX clients_org_idx ON clients (org_id, created_at);

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
CREATE POLICY clients_org ON clients USING (org_id = app_org()) WITH CHECK (org_id = app_org());

-- Sin perfiles ni entrevistas guardados al aplicar esta migración: la columna nace obligatoria.
ALTER TABLE user_profiles
    ADD COLUMN client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE;
CREATE INDEX user_profiles_client_idx ON user_profiles (client_id, updated_at);
ALTER TABLE profile_interviews
    ADD COLUMN client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE;
CREATE INDEX profile_interviews_client_idx ON profile_interviews (client_id, status, updated_at);
