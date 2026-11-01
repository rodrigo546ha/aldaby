-- HouseFinder · 0019: lote que una extracción nueva de su anuncio ya no encuentra (ADR-0033).
-- No se borra: queda `retirada`, sin inmueble, con el motivo en location_issue.
ALTER TABLE offers DROP CONSTRAINT offers_extraction_status_check;
ALTER TABLE offers ADD CONSTRAINT offers_extraction_status_check
    CHECK (extraction_status IN ('no_aplica', 'pendiente', 'extraida', 'confirmada', 'retirada'));
