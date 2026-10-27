-- HouseFinder · esquema inicial (fase 1-3). PostgreSQL 16 + PostGIS.
CREATE EXTENSION IF NOT EXISTS postgis;

-- Fuentes de datos: toda fila con cifras apunta a una fuente.
CREATE TABLE sources (
    id           TEXT PRIMARY KEY,               -- p. ej. 'ine-adrh-2023', 'boe-sumario'
    name         TEXT NOT NULL,
    url          TEXT,
    license      TEXT,
    fetched_at   TIMESTAMPTZ,
    notes        TEXT
);

-- Secciones censales (INE): la llave para cruzar todo.
CREATE TABLE census_sections (
    code         TEXT PRIMARY KEY,               -- código de sección censal INE (10 dígitos)
    municipality TEXT NOT NULL,                  -- código municipio INE
    geom         GEOMETRY(MultiPolygon, 4326) NOT NULL,
    vintage      INT NOT NULL                    -- año de la cartografía
);
CREATE INDEX census_sections_geom_idx ON census_sections USING GIST (geom);

-- Indicadores por sección (renta, población, edad...). Formato largo para no migrar al añadir.
CREATE TABLE section_indicators (
    section_code TEXT REFERENCES census_sections(code),
    indicator    TEXT NOT NULL,                  -- p. ej. 'renta_media_hogar'
    year         INT NOT NULL,
    value        NUMERIC NOT NULL,
    source_id    TEXT REFERENCES sources(id),
    PRIMARY KEY (section_code, indicator, year)
);

-- Inmuebles físicos (deduplicados) y anuncios u ofertas que los referencian.
CREATE TABLE properties (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cadastral_ref    TEXT UNIQUE,                -- referencia catastral si se conoce
    address          TEXT,
    location         GEOGRAPHY(Point, 4326),
    section_code     TEXT REFERENCES census_sections(code),
    built_area_m2    NUMERIC,
    year_built       INT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE offers (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id      UUID REFERENCES properties(id),
    channel          TEXT NOT NULL,              -- 'url_usuario' | 'boe_subasta' | 'boe_seccion_v' | 'servicer'
    external_id      TEXT,
    url              TEXT,
    asking_price     NUMERIC,
    auction_min_bid  NUMERIC,
    deposit_required NUMERIC,
    possession       TEXT,                       -- 'libre' | 'ocupado' | 'alquilado' | 'desconocido'
    raw              JSONB NOT NULL,             -- lo recibido, tal cual
    extracted        JSONB,                      -- lo extraído por el agente (con confianza)
    first_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen        TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_id        TEXT REFERENCES sources(id),
    UNIQUE (channel, external_id)
);

-- Perfiles y planes. Datos financieros personales: cifrar en reposo (RGPD).
CREATE TABLE user_profiles (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id     TEXT NOT NULL,                  -- usuario o profesional que gestiona el perfil
    data         JSONB NOT NULL,                 -- perfil estructurado (cifrado a nivel de app)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id   UUID REFERENCES user_profiles(id),
    offer_id     UUID REFERENCES offers(id),
    as_of        DATE NOT NULL,
    figures      JSONB NOT NULL,                 -- lista de Figure (valor, fórmula, fuentes)
    rule_ids     TEXT[] NOT NULL,                -- reglas de normativa aplicadas
    narrative    TEXT,                           -- texto del agente (sin cifras propias)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
