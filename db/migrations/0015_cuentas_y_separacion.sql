-- HouseFinder · 0015: cuentas con contraseña, sesiones y Row-Level Security por organización
-- (F7.1, ADR-0028).

CREATE TABLE accounts (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email            TEXT NOT NULL,                  -- en minúsculas
    password_hash    TEXT,                           -- argon2id; NULL hasta que elige contraseña
    role             TEXT NOT NULL CHECK (role IN ('admin', 'profesional')),
    failed_attempts  INTEGER NOT NULL DEFAULT 0,
    locked_until     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT accounts_email_lower CHECK (email = lower(email))
);
CREATE UNIQUE INDEX accounts_email_idx ON accounts (email);

-- Enlaces de un solo uso para elegir o restablecer la contraseña: solo el hash del token.
CREATE TABLE account_tokens (
    token_hash   TEXT PRIMARY KEY,                   -- SHA-256 en hexadecimal
    account_id   UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    expires_at   TIMESTAMPTZ NOT NULL,
    used_at      TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    token_hash   TEXT PRIMARY KEY,                   -- SHA-256 del token de la cookie
    account_id   UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL
);
CREATE INDEX sessions_account_idx ON sessions (account_id);

-- La organización de la petición, que fija la API con set_config('app.org_id', …).
CREATE FUNCTION app_org() RETURNS UUID LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.org_id', true), '')::uuid
$$;

-- Rol de la API: sin privilegios de propietario, así que las políticas le aplican. El worker y
-- las migraciones siguen con el propietario, que ve todo. Los roles son del servidor entero.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'housefinder_api') THEN
        CREATE ROLE housefinder_api NOLOGIN;
    END IF;
END
$$;
GRANT housefinder_api TO CURRENT_USER;
GRANT USAGE ON SCHEMA public TO housefinder_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO housefinder_api;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO housefinder_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO housefinder_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO housefinder_api;

-- Datos de una organización: solo los suyos.
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_profiles_org ON user_profiles
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY plans_org ON plans USING (org_id = app_org()) WITH CHECK (org_id = app_org());
ALTER TABLE profile_interviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY profile_interviews_org ON profile_interviews
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
ALTER TABLE offer_rent_expectations ENABLE ROW LEVEL SECURITY;
CREATE POLICY offer_rent_expectations_org ON offer_rent_expectations
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());

-- Ofertas: las suyas y las públicas (lotes del BOE, org_id NULL), que solo escribe el worker.
ALTER TABLE offers ENABLE ROW LEVEL SECURITY;
CREATE POLICY offers_read ON offers FOR SELECT USING (org_id IS NULL OR org_id = app_org());
CREATE POLICY offers_write ON offers FOR INSERT WITH CHECK (org_id = app_org());
CREATE POLICY offers_update ON offers FOR UPDATE
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
CREATE POLICY offers_delete ON offers FOR DELETE USING (org_id = app_org());

-- Lo recibido de cada oferta: lo que se ve de su oferta.
ALTER TABLE offer_raw_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY offer_raw_versions_offer ON offer_raw_versions
    USING (EXISTS (SELECT 1 FROM offers o WHERE o.id = offer_id));
