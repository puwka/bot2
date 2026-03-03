-- ============================================================
-- Migration: Trendwatching Bot — new tables
-- Run this in Supabase SQL Editor
-- Existing tables (topics, sources, videos) are NOT touched.
-- ============================================================

-- 1. Enum for user roles
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('ADMIN', 'UPLOADER', 'DISTRIBUTOR');
    END IF;
END $$;

-- 2. users
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id   BIGINT NOT NULL UNIQUE,
    username      TEXT,
    full_name     TEXT,
    role          user_role NOT NULL DEFAULT 'DISTRIBUTOR',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- 3. user_categories — links users to topics they are assigned to
CREATE TABLE IF NOT EXISTS user_categories (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id      UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, topic_id)
);

CREATE INDEX IF NOT EXISTS idx_user_categories_user ON user_categories (user_id);
CREATE INDEX IF NOT EXISTS idx_user_categories_topic ON user_categories (topic_id);

-- 4. video_distribution — tracks which video was sent to which distributor
CREATE TABLE IF NOT EXISTS video_distribution (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id      UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed     BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ,
    UNIQUE (video_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_vdist_user ON video_distribution (user_id);
CREATE INDEX IF NOT EXISTS idx_vdist_video ON video_distribution (video_id);
CREATE INDEX IF NOT EXISTS idx_vdist_completed ON video_distribution (completed);

-- 5. video_results — result links submitted by distributors
CREATE TABLE IF NOT EXISTS video_results (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    distribution_id   UUID NOT NULL REFERENCES video_distribution(id) ON DELETE CASCADE,
    url               TEXT NOT NULL UNIQUE,
    platform          TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vresults_dist ON video_results (distribution_id);
CREATE INDEX IF NOT EXISTS idx_vresults_url ON video_results (url);

-- 6. action_logs — full audit trail
CREATE TABLE IF NOT EXISTS action_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    telegram_id   BIGINT,
    action        TEXT NOT NULL,
    details       JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_action_logs_user ON action_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_action ON action_logs (action);
CREATE INDEX IF NOT EXISTS idx_action_logs_created ON action_logs (created_at DESC);

-- 7. Helper: auto-update updated_at on users
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
