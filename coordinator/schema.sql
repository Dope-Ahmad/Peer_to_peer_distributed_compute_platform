CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS workers(
    id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname    TEXT NOT NULL,
    ip_address  TEXT NOT NULL,
    port    INTEGER NOT NULL,
    cpu_cores   INTEGER NOT NULL,
    memory_mb   INTEGER NOT NULL,
    status  TEXT NOT NULL DEFAULT 'idle',
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs(
    id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   TEXT NOT NULL DEFAULT 'anonymous',
    code TEXT NOT NULL,
    input_data  JSONB NOT NULL DEFAULT '{}',
    cpu_limit FLOAT NOT NULL DEFAULT 1.0,
    memory_limit_mb INTEGER NOT NULL DEFAULT 512,
    timeout_secs INTEGER NOT NULL DEFAULT 300,
    priority    INTEGER NOT NULL DEFAULT 5,
    status  TEXT NOT NULL DEFAULT 'queued',
    worker_id   UUID REFERENCES workers(id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 2
);

CREATE INDEX IF NOT EXISTS idx_jobs_queue
    ON jobs (status, priority, submitted_at);
