-- HouseFinder · 0007: datos personales cifrados (ADR-0011). Las tablas están vacías al aplicarla.
-- Cada fila: contenido cifrado con su clave de datos (DEK), la DEK envuelta con la clave maestra
-- `key_id` y la versión del formato. En claro solo los metadatos para filtrar y auditar.

ALTER TABLE user_profiles DROP COLUMN data;
ALTER TABLE user_profiles
    ADD COLUMN data_enc     BYTEA NOT NULL,
    ADD COLUMN dek_enc      BYTEA NOT NULL,
    ADD COLUMN key_id       TEXT NOT NULL,
    ADD COLUMN enc_version  SMALLINT NOT NULL;
CREATE INDEX user_profiles_key_idx ON user_profiles (key_id);

-- El plan guarda entradas, cifras y texto del agente en un solo sobre; quedan en claro la versión
-- del motor, las huellas de reglas y parámetros y las reglas aplicadas (D9).
ALTER TABLE plans DROP COLUMN figures;
ALTER TABLE plans DROP COLUMN narrative;
ALTER TABLE plans
    ADD COLUMN content_enc  BYTEA NOT NULL,
    ADD COLUMN dek_enc      BYTEA NOT NULL,
    ADD COLUMN key_id       TEXT NOT NULL,
    ADD COLUMN enc_version  SMALLINT NOT NULL;
