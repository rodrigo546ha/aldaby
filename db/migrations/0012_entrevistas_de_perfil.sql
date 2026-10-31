-- HouseFinder · 0012: entrevista de perfil cifrada (ADR-0020). Respuestas literales y borrador en
-- un sobre (ADR-0011); en claro solo la organización, el estado, las fechas y el perfil confirmado.

CREATE TABLE profile_interviews (
    id           UUID PRIMARY KEY,
    org_id       UUID NOT NULL REFERENCES organizations(id),
    owner_id     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'en_curso' CHECK (status IN ('en_curso', 'confirmada')),
    profile_id   UUID REFERENCES user_profiles(id),
    data_enc     BYTEA NOT NULL,
    dek_enc      BYTEA NOT NULL,
    key_id       TEXT NOT NULL,
    enc_version  SMALLINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX profile_interviews_org_idx ON profile_interviews (org_id, status, updated_at);
CREATE INDEX profile_interviews_key_idx ON profile_interviews (key_id);
