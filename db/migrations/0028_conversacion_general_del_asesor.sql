-- HouseFinder · 0028: conversación con el asesor sin oferta fija, en «Mi plan» (ADR-0066). Una por
-- cliente, cifrada como las de cada oferta (0026, ADR-0064): aquí solo hay bytes cifrados, con el
-- mismo plazo y el mismo borrado nocturno.
CREATE TABLE advisor_general_conversations (
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id    UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    data_enc     BYTEA NOT NULL,
    dek_enc      BYTEA NOT NULL,
    key_id       TEXT NOT NULL,
    enc_version  SMALLINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, client_id)
);
CREATE INDEX advisor_general_conversations_updated_idx
    ON advisor_general_conversations (updated_at);

ALTER TABLE advisor_general_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY advisor_general_conversations_org ON advisor_general_conversations
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
