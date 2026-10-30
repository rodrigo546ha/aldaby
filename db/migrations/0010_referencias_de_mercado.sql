-- HouseFinder · 0010: referencias públicas de alquiler y de precio (G6, ADR-0018).
-- Formato largo: una fila por fuente, nivel, territorio, periodo, medida, tipología y estadístico.
CREATE TABLE market_references (
    source_id  TEXT NOT NULL REFERENCES sources(id),
    level      TEXT NOT NULL
               CHECK (level IN ('seccion', 'distrito', 'municipio', 'provincia', 'comunidad')),
    code       TEXT NOT NULL,              -- código INE: sección (10), distrito (7), municipio (5)…
    vintage    INT,                         -- seccionado de los códigos (SERPAVI: 2021)
    year       INT NOT NULL,
    quarter    INT NOT NULL DEFAULT 0 CHECK (quarter BETWEEN 0 AND 4),  -- 0: dato anual
    measure    TEXT NOT NULL,               -- 'renta_m2_mes', 'renta_mes', 'superficie',
                                            -- 'alquileres', 'valor_tasado_m2', 'ipv'
    typology   TEXT NOT NULL,               -- 'colectiva', 'unifamiliar', 'todas', 'nueva',
                                            -- 'segunda_mano'
    stat       TEXT NOT NULL,               -- 'n', 'p25', 'mediana', 'p75', 'valor', 'indice'
    value      NUMERIC NOT NULL,
    unit       TEXT NOT NULL,
    PRIMARY KEY (source_id, level, code, year, quarter, measure, typology, stat)
);
CREATE INDEX market_references_lookup_idx ON market_references (level, code, measure, year);
