-- HouseFinder · 0024: punto aproximado de una oferta que no se pudo ubicar (ADR-0054).
-- El centro del municipio, solo para enseñarla en el mapa con la marca «ubicación aproximada». No
-- crea inmueble ni sección: el plan no la usa. Al ubicarla de verdad, se vacía.
ALTER TABLE offers ADD COLUMN approx_location geography(Point, 4326);
