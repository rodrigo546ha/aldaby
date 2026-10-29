-- HouseFinder · 0005: cola de trabajos (ADR-0010). Sin datos personales en `payload`.
CREATE TABLE jobs (
    id            BIGSERIAL PRIMARY KEY,
    kind          TEXT NOT NULL,                  -- tipo registrado en housefinder.jobs
    payload       JSONB NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'pendiente'
                  CHECK (status IN ('pendiente', 'en_curso', 'hecho', 'fallido')),
    attempts      INT NOT NULL DEFAULT 0,
    max_attempts  INT NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
    run_after     TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at     TIMESTAMPTZ,
    locked_by     TEXT,
    dedupe_key    TEXT,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Trabajos listos para reservar, por orden de llegada.
CREATE INDEX jobs_ready_idx ON jobs (run_after, id) WHERE status = 'pendiente';
-- Una sola copia viva por clave.
CREATE UNIQUE INDEX jobs_dedupe_idx ON jobs (dedupe_key)
    WHERE dedupe_key IS NOT NULL AND status IN ('pendiente', 'en_curso');

CREATE TABLE job_runs (
    id           BIGSERIAL PRIMARY KEY,
    job_id       BIGINT NOT NULL REFERENCES jobs(id),
    attempt      INT NOT NULL,
    worker       TEXT NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL,
    finished_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ok           BOOLEAN NOT NULL,
    result       JSONB,
    error        TEXT
);
CREATE INDEX job_runs_job_idx ON job_runs (job_id);

CREATE TABLE job_schedules (
    name              TEXT PRIMARY KEY,           -- también es la dedupe_key del trabajo
    kind              TEXT NOT NULL,
    payload           JSONB NOT NULL DEFAULT '{}',
    interval_seconds  INT NOT NULL CHECK (interval_seconds > 0),
    next_run_at       TIMESTAMPTZ NOT NULL,
    enabled           BOOLEAN NOT NULL DEFAULT true,
    last_enqueued_at  TIMESTAMPTZ
);
