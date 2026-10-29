-- HouseFinder · 0003: cada indicador por sección guarda su unidad (F3.3).
-- «EUR», «años», «personas» o «ratio» (tanto por uno). La tabla está vacía al aplicarla.
ALTER TABLE section_indicators ADD COLUMN unit TEXT NOT NULL;
