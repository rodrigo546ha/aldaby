-- HouseFinder · 0017: marca del profesional en sus planes (F7.3, ADR-0030).
CREATE TABLE org_branding (
    org_id        UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    display_name  TEXT CHECK (char_length(display_name) <= 80),
    contact       TEXT CHECK (char_length(contact) <= 120),
    color         TEXT CHECK (color ~ '^#[0-9a-f]{6}$'),
    intro         TEXT CHECK (char_length(intro) <= 600),
    logo_png      BYTEA,                         -- reescrito por branding/logo.py, nunca el subido
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE org_branding ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_branding_org ON org_branding
    USING (org_id = app_org()) WITH CHECK (org_id = app_org());
