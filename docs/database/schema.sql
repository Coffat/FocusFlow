-- =============================================================================
-- FocusFlow Relational Database Schema DDL (PostgreSQL 16)
-- Generated: 29/09/2026
-- Standards: ISO/IEC 9075 SQL, 3NF/BCNF
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. BẢNG USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    tier VARCHAR(20) NOT NULL DEFAULT 'FREE' CHECK (tier IN ('FREE', 'PREMIUM')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. BẢNG WEBCAL_TOKENS
CREATE TABLE webcal_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reset_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. BẢNG AI_QUOTAS
CREATE TABLE ai_quotas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    monthly_limit INTEGER NOT NULL DEFAULT 30 CHECK (monthly_limit > 0),
    used_calls INTEGER NOT NULL DEFAULT 0 CHECK (used_calls >= 0),
    tokens_consumed INTEGER NOT NULL DEFAULT 0 CHECK (tokens_consumed >= 0),
    cycle_start TIMESTAMPTZ NOT NULL,
    cycle_end TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. BẢNG AVAILABILITIES
CREATE TABLE availabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    mode VARCHAR(10) NOT NULL DEFAULT 'MODE_A' CHECK (mode IN ('MODE_A', 'MODE_B')),
    weekly_schedule JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. BẢNG GOALS
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    target_date TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. BẢNG ROADMAPS
CREATE TABLE roadmaps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'INITIALIZED' 
        CHECK (status IN ('INITIALIZED', 'ACTIVE', 'PAUSED', 'COMPLETED')),
    start_date DATE,
    target_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. BẢNG MILESTONES
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL CHECK (sequence_order >= 1),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. BẢNG SCHEDULE_PROPOSALS
CREATE TABLE schedule_proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    proposal_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'APPLIED', 'DISCARDED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. BẢNG OFFICIAL_SCHEDULES
CREATE TABLE official_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roadmap_id UUID NOT NULL UNIQUE REFERENCES roadmaps(id) ON DELETE CASCADE,
    total_sessions INTEGER NOT NULL DEFAULT 0 CHECK (total_sessions >= 0),
    total_hours INTEGER NOT NULL DEFAULT 0 CHECK (total_hours >= 0),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. BẢNG TASKS
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    official_schedule_id UUID REFERENCES official_schedules(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    estimated_minutes INTEGER NOT NULL CHECK (estimated_minutes BETWEEN 15 AND 240),
    scheduled_date DATE,
    start_time TIME,
    end_time TIME,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMPLETED')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. BẢNG STUDY_SESSIONS
CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    planned_minutes INTEGER NOT NULL CHECK (planned_minutes > 0),
    actual_minutes INTEGER NOT NULL DEFAULT 0 CHECK (actual_minutes >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS' 
        CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED')),
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. BẢNG SESSION_TASKS
CREATE TABLE session_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    is_completed_in_session BOOLEAN NOT NULL DEFAULT FALSE,
    time_spent_minutes INTEGER NOT NULL DEFAULT 0 CHECK (time_spent_minutes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_task UNIQUE (session_id, task_id)
);

-- 13. BẢNG STUDY_NOTES
CREATE TABLE study_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
    note_type VARCHAR(20) NOT NULL CHECK (note_type IN ('SCRATCHPAD', 'TAKEAWAY')),
    content TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. BẢNG PAUSE_RECORDS
CREATE TABLE pause_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    pause_start_date DATE NOT NULL,
    pause_end_date DATE NOT NULL,
    shifted_days INTEGER NOT NULL CHECK (shifted_days > 0),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_pause_dates CHECK (pause_end_date >= pause_start_date)
);

-- 15. BẢNG AI_REVIEWS
CREATE TABLE ai_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    review_cycle VARCHAR(20) NOT NULL CHECK (review_cycle IN ('WEEKLY', 'MILESTONE')),
    quantitative_summary JSONB NOT NULL,
    strengths_feedback TEXT NOT NULL,
    bottlenecks_feedback TEXT NOT NULL,
    action_recommendations TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- CHỈ MỤC HIỆU NĂNG (INDEXES)
-- =============================================================================
CREATE UNIQUE INDEX idx_webcal_tokens_token_hash ON webcal_tokens(token_hash) WHERE is_active = TRUE;
CREATE INDEX idx_tasks_roadmap_scheduled_date ON tasks(roadmap_id, scheduled_date);
CREATE INDEX idx_tasks_pending_overdue ON tasks(scheduled_date) WHERE status = 'PENDING' AND scheduled_date IS NOT NULL;
CREATE INDEX idx_study_sessions_in_progress ON study_sessions(last_heartbeat_at) WHERE status = 'IN_PROGRESS';
CREATE INDEX idx_ai_quotas_user_cycle ON ai_quotas(user_id, cycle_start, cycle_end);
CREATE INDEX idx_milestones_roadmap_seq ON milestones(roadmap_id, sequence_order);
CREATE INDEX idx_study_notes_session ON study_notes(session_id);
