-- HouseFinder · 0006: vigilancia del BOE y del BOCM (F2.6).
-- Una tarea por publicación que pasa los filtros de data/watch/vigilancia.yaml. La IA escribirá
-- el resumen (G5); una persona decide.
CREATE TABLE review_tasks (
    id             BIGSERIAL PRIMARY KEY,
    source         TEXT NOT NULL CHECK (source IN ('boe', 'bocm')),
    external_id    TEXT NOT NULL,                 -- BOE-A-2026-20823, BOCM-20261009-1
    published_on   DATE NOT NULL,
    title          TEXT NOT NULL,
    url            TEXT NOT NULL,
    section        TEXT NOT NULL,
    department     TEXT NOT NULL DEFAULT '',
    tags           TEXT[] NOT NULL,
    rule_ids       TEXT[] NOT NULL DEFAULT '{}',  -- reglas afectadas, si se sabe
    notes          TEXT[] NOT NULL DEFAULT '{}',
    summary        TEXT,                          -- resumen de la IA (G5)
    status         TEXT NOT NULL DEFAULT 'abierta'
                   CHECK (status IN ('abierta', 'descartada', 'aplicada')),
    decided_by     TEXT,
    decided_at     TIMESTAMPTZ,
    decision_note  TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, external_id)
);
CREATE INDEX review_tasks_open_idx ON review_tasks (published_on) WHERE status = 'abierta';

-- Boletines ya leídos, para no volver a descargarlos.
CREATE TABLE watch_issues (
    source      TEXT NOT NULL,
    issue_id    TEXT NOT NULL,                    -- '2026-10-07' (BOE) o 'BOCM-20261029-260'
    read_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    items       INT NOT NULL,                     -- publicaciones leídas
    tasks       INT NOT NULL,                     -- tareas abiertas
    PRIMARY KEY (source, issue_id)
);
