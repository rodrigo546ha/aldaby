-- HouseFinder · 0011: referencias mensuales (componente de alquiler del IPC, ADR-0018).
-- month = 0 para datos anuales o trimestrales; 1–12 para mensuales.
ALTER TABLE market_references
    ADD COLUMN month INT NOT NULL DEFAULT 0 CHECK (month BETWEEN 0 AND 12);
ALTER TABLE market_references DROP CONSTRAINT market_references_pkey;
ALTER TABLE market_references
    ADD PRIMARY KEY (source_id, level, code, year, quarter, month, measure, typology, stat);
