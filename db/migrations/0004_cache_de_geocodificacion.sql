-- HouseFinder · 0004: caché de geocodificación (ADR-0009).
-- Una fila por consulta normalizada; se reutiliza un año. Sin datos del usuario.
CREATE TABLE geocode_cache (
    query          TEXT PRIMARY KEY,               -- dirección normalizada
    lon            DOUBLE PRECISION NOT NULL,
    lat            DOUBLE PRECISION NOT NULL,
    match_type     TEXT NOT NULL,                  -- 'portal' | 'callejero'
    matched        TEXT NOT NULL,                  -- dirección encontrada por el geocodificador
    municipality   TEXT,                           -- código INE del municipio
    cadastral_ref  TEXT,                           -- referencia catastral, si la da
    source_id      TEXT NOT NULL REFERENCES sources(id),
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
