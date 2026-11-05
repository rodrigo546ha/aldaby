-- HouseFinder · 0026: conversaciones con el asesor sobre el plan de una oferta (ADR-0064).
-- Una por cliente y oferta, cifrada como el perfil (ADR-0011): aquí solo hay bytes cifrados. Se
-- borra a los días de `data/conservacion.yaml` desde la última pregunta, con su cliente o con la
-- oferta.
CREATE TABLE advisor_conversations (
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id    UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    offer_id     UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    data_enc     BYTEA NOT NULL,
    dek_enc      BYTEA NOT NULL,
    key_id       TEXT NOT NULL,
    enc_version  SMALLINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, client_id, offer_id)
);
CREATE INDEX advisor_conversations_updated_idx ON advisor_conversations (updated_at);

ALTER TABLE advisor_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY advisor_conversations_org ON advisor_conversations
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
