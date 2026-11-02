-- HouseFinder · 0021: aceptación de los textos legales por cuenta y versión, y aviso a los
-- clientes del profesional (ADR-0039). Sin IP ni navegador: la cuenta, la versión y la fecha bastan.

CREATE TABLE legal_acceptances (
    account_id   UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    document     TEXT NOT NULL,          -- id del documento: 'condiciones', 'privacidad'…
    version      INTEGER NOT NULL,
    accepted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, document, version)
);

-- Cuándo marcó el profesional que había informado a su cliente del tratamiento. NULL en los
-- clientes dados de alta antes de esta migración.
ALTER TABLE clients ADD COLUMN informed_at TIMESTAMPTZ;
