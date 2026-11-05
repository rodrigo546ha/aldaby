-- HouseFinder · 0025: lo que el usuario calcula que costaría reformar cada oferta.
-- La valoración es la de una vivienda en el estado habitual de la zona: si el anuncio dice «a
-- reformar», el usuario indica la reforma y el plan la suma a la compra. Como la renta esperada
-- (0014), es de la organización y se separa con Row-Level Security (0015).
CREATE TABLE offer_renovations (
    org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    offer_id   UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    amount     NUMERIC NOT NULL CHECK (amount > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, offer_id)
);

ALTER TABLE offer_renovations ENABLE ROW LEVEL SECURITY;
CREATE POLICY offer_renovations_org ON offer_renovations
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
