-- HouseFinder · 0018: por qué una oferta se quedó sin ubicar y si merece otro intento (ADR-0031).
-- location_retry: un servicio falló o su provincia no tiene secciones cargadas; extract_offers
-- vuelve a ubicarla sin pasar otra vez por el LLM. Al ubicarla, las dos columnas se vacían.
ALTER TABLE offers
    ADD COLUMN location_issue TEXT,
    ADD COLUMN location_retry BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX offers_location_retry_idx ON offers (channel) WHERE location_retry;
