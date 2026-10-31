-- HouseFinder · 0013: series nacionales en market_references (ADR-0022): tipos de las hipotecas
-- del Banco de España y del INE, con nivel 'pais' y código 'ES'.
ALTER TABLE market_references DROP CONSTRAINT market_references_level_check;
ALTER TABLE market_references ADD CONSTRAINT market_references_level_check
    CHECK (level IN ('pais', 'seccion', 'distrito', 'municipio', 'provincia', 'comunidad'));
