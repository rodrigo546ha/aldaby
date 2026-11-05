-- HouseFinder · 0027: consultas al asesor por organización y día (ADR-0065). Solo el número: ni la
-- pregunta ni la oferta. El día es el natural de Madrid; los días anteriores los borra el trabajo
-- nocturno de las conversaciones.
CREATE TABLE advisor_uses (
    org_id  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    day     DATE NOT NULL,
    uses    INTEGER NOT NULL CHECK (uses > 0),
    PRIMARY KEY (org_id, day)
);

ALTER TABLE advisor_uses ENABLE ROW LEVEL SECURITY;
CREATE POLICY advisor_uses_org ON advisor_uses
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
