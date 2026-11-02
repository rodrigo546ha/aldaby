-- HouseFinder · 0023: recuento de visitas sin cookies ni identificadores (F8.6, ADR-0042).
-- Una fila por día (hora de Madrid), ruta normalizada, dominio de origen y utm_source. Nada más.

CREATE TABLE page_views (
    day       DATE NOT NULL,
    path      TEXT NOT NULL,           -- '/', '/plan/[offer]'…: nunca un identificador
    referrer  TEXT NOT NULL DEFAULT '', -- dominio del sitio de origen, si es otro
    source    TEXT NOT NULL DEFAULT '', -- utm_source
    views     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, path, referrer, source)
);
