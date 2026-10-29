-- HouseFinder · 0009: correcciones de anuncios del BOE enlazadas con el anuncio que corrigen (F4.4).
-- La corrección es una oferta más (kind = 'anuncio', sin extracción); `corrects_id` apunta al
-- anuncio corregido cuando está guardado.
ALTER TABLE offers ADD COLUMN corrects_id UUID REFERENCES offers(id);
CREATE INDEX offers_corrects_idx ON offers (corrects_id) WHERE corrects_id IS NOT NULL;
