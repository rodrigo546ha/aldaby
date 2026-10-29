-- HouseFinder · 0008: ofertas normalizadas, versiones de lo recibido y deduplicación (F4.6).
-- Las tablas offers y properties están vacías al aplicarla.

-- Una oferta es un anuncio (lo que publica el canal), un lote dentro de un anuncio o un enlace
-- pegado por el usuario. Lo recibido se guarda siempre (raw) y cada versión distinta, aparte.
ALTER TABLE offers ALTER COLUMN external_id SET NOT NULL;
ALTER TABLE offers
    ADD COLUMN kind TEXT NOT NULL DEFAULT 'anuncio' CHECK (kind IN ('anuncio', 'lote', 'enlace')),
    ADD COLUMN parent_id UUID REFERENCES offers(id),
    ADD COLUMN title TEXT,
    ADD COLUMN published_on DATE,
    ADD COLUMN description TEXT,
    ADD COLUMN address TEXT,
    ADD COLUMN cadastral_ref TEXT,
    ADD COLUMN built_area_m2 NUMERIC,
    -- Texto libre: los datos del inmueble se extraen (F6.1) y el usuario los confirma.
    ADD COLUMN extraction_status TEXT NOT NULL DEFAULT 'no_aplica'
        CHECK (extraction_status IN ('no_aplica', 'pendiente', 'extraida', 'confirmada')),
    ADD COLUMN location_source TEXT,
    ADD COLUMN raw_sha256 TEXT NOT NULL;
CREATE INDEX offers_property_idx ON offers (property_id);
CREATE INDEX offers_pending_extraction_idx ON offers (published_on)
    WHERE extraction_status = 'pendiente';

CREATE TABLE offer_raw_versions (
    id          BIGSERIAL PRIMARY KEY,
    offer_id    UUID NOT NULL REFERENCES offers(id),
    sha256      TEXT NOT NULL,
    raw         JSONB NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (offer_id, sha256)
);

-- Inmuebles: la unidad de deduplicación. Búsqueda por cercanía con PostGIS.
ALTER TABLE properties ADD COLUMN municipality TEXT;
CREATE INDEX properties_location_idx ON properties USING GIST (location);
