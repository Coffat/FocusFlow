-- =============================================================================
-- FocusFlow Relational Database Schema DDL (PostgreSQL 16)
-- Standards: ISO/IEC 9075 SQL, 3NF/BCNF, Defense-in-Depth Constraints
-- Engine: PostgreSQL 16+ (Sử dụng hàm gen_random_uuid() ANSI/Core)
-- =============================================================================

-- 1. BẢNG USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    role VARCHAR(20) NOT NULL DEFAULT 'LEARNER' CHECK (role IN ('LEARNER', 'ADMIN')),
    tier VARCHAR(20) NOT NULL DEFAULT 'FREE' CHECK (tier IN ('FREE', 'PREMIUM')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. BẢNG WEBCAL_TOKENS
-- Lưu SHA-256 digest của 32-byte hex CSPRN sinh bởi secrets.token_hex(32)
CREATE TABLE webcal_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reset_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. BẢNG AI_QUOTAS
-- Hỗ trợ cơ chế 2 pha: Reserve -> Commit / Release chống Race Condition
CREATE TABLE ai_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    monthly_limit INTEGER NOT NULL DEFAULT 30 CHECK (monthly_limit > 0),
    used_calls INTEGER NOT NULL DEFAULT 0 CHECK (used_calls >= 0),
    reserved_calls INTEGER NOT NULL DEFAULT 0 CHECK (reserved_calls >= 0),
    tokens_consumed INTEGER NOT NULL DEFAULT 0 CHECK (tokens_consumed >= 0),
    cycle_start TIMESTAMPTZ NOT NULL,
    cycle_end TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ai_quota_limit CHECK (used_calls + reserved_calls <= monthly_limit),
    CONSTRAINT chk_ai_quota_cycle CHECK (cycle_end > cycle_start)
);

-- 4. BẢNG AVAILABILITIES
-- Mỗi User có duy nhất 1 cấu hình quỹ thời gian rảnh
CREATE TABLE availabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    mode VARCHAR(10) NOT NULL DEFAULT 'MODE_A' CHECK (mode IN ('MODE_A', 'MODE_B')),
    weekly_schedule JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. BẢNG GOALS
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    target_date TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. BẢNG ROADMAPS
-- Cho phép nhiều Roadmap ACTIVE song song phục vụ đa mục tiêu học tập
CREATE TABLE roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'INITIALIZED' 
        CHECK (status IN ('INITIALIZED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')),
    start_date DATE,
    target_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_roadmap_dates CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date)
);

-- 7. BẢNG MILESTONES
-- Thứ tự tuần tự sequence_order là duy nhất trong cùng một Roadmap
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL CHECK (sequence_order >= 1),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_milestone_roadmap_sequence UNIQUE (roadmap_id, sequence_order),
    CONSTRAINT uq_milestone_id_roadmap UNIQUE (id, roadmap_id)
);

-- 8. BẢNG SCHEDULE_PROPOSALS
CREATE TABLE schedule_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    proposal_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'APPLIED', 'DISCARDED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. BẢNG OFFICIAL_SCHEDULES
CREATE TABLE official_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL UNIQUE REFERENCES roadmaps(id) ON DELETE CASCADE,
    total_sessions INTEGER NOT NULL DEFAULT 0 CHECK (total_sessions >= 0),
    total_hours INTEGER NOT NULL DEFAULT 0 CHECK (total_hours >= 0),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. BẢNG TASKS
-- Bảo vệ tính nhất quán khung giờ và trạng thái hoàn thành
-- Khóa ngoại phức hợp (milestone_id, roadmap_id) ngăn chặn hoàn toàn lệch lộ trình
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    milestone_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    estimated_minutes INTEGER NOT NULL CHECK (estimated_minutes BETWEEN 15 AND 240),
    scheduled_date DATE,
    start_time TIME,
    end_time TIME,
    status VARCHAR(20) NOT NULL DEFAULT 'TODO' 
        CHECK (status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_tasks_milestone_roadmap FOREIGN KEY (milestone_id, roadmap_id) 
        REFERENCES milestones(id, roadmap_id) ON DELETE CASCADE,
    CONSTRAINT chk_task_time_window CHECK (start_time IS NULL OR end_time IS NULL OR start_time < end_time),
    CONSTRAINT chk_task_completed_at CHECK ((status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status != 'COMPLETED' AND completed_at IS NULL))
);

-- 11. BẢNG STUDY_SESSIONS
-- Bảo vệ toàn vẹn thời gian học và trạng thái kết thúc phiên
CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    planned_minutes INTEGER NOT NULL CHECK (planned_minutes > 0),
    actual_minutes INTEGER NOT NULL DEFAULT 0 CHECK (actual_minutes >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS' 
        CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED')),
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_session_times CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT chk_session_status_ended CHECK ((status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL))
);

-- 12. BẢNG SESSION_TASKS
-- Bảng liên kết quan hệ N:M giữa phiên học và các task thực hiện trong phiên
CREATE TABLE session_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    allocated_minutes INTEGER NOT NULL DEFAULT 0 CHECK (allocated_minutes >= 0),
    is_completed_in_session BOOLEAN NOT NULL DEFAULT FALSE,
    time_spent_minutes INTEGER NOT NULL DEFAULT 0 CHECK (time_spent_minutes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_task UNIQUE (session_id, task_id)
);

-- 13. BẢNG STUDY_NOTES
-- Mỗi phiên học có duy nhất 1 Scratchpad và 1 Takeaway
CREATE TABLE study_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
    note_type VARCHAR(20) NOT NULL CHECK (note_type IN ('SCRATCHPAD', 'TAKEAWAY')),
    content TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_note_type UNIQUE (session_id, note_type)
);

-- 14. BẢNG PAUSE_RECORDS
CREATE TABLE pause_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
-- CHỈ MỤC HIỆU NĂNG & BẢO VỆ ĐỒNG THỜI (INDEXES & CONCURRENCY CONSTRAINTS)
-- =============================================================================

-- 1. Bất biến duy nhất 1 Active Study Session cho mỗi User tại một thời điểm (Chống race condition)
CREATE UNIQUE INDEX uq_user_single_active_session ON study_sessions(user_id) WHERE status = 'IN_PROGRESS';

-- 2. Truy vấn nóng lịch sử học tập & Dashboard của User
CREATE INDEX idx_study_sessions_user_started ON study_sessions(user_id, started_at DESC);

-- 3. Truy vấn các Roadmap của User theo trạng thái
CREATE INDEX idx_roadmaps_user_status ON roadmaps(user_id, status);

-- 4. Truy vấn Task theo Roadmap và ngày xếp lịch
CREATE INDEX idx_tasks_roadmap_scheduled_date ON tasks(roadmap_id, scheduled_date);

-- 5. Phát hiện Task quá hạn tất định (Deterministic Overdue Formula - BUSR-06)
CREATE INDEX idx_tasks_todo_overdue ON tasks(scheduled_date) WHERE status = 'TODO' AND scheduled_date IS NOT NULL;

-- 6. Monitor Heartbeat phiên học gián đoạn (Celery Beat Background Job - BUSR-09)
CREATE INDEX idx_study_sessions_in_progress ON study_sessions(last_heartbeat_at) WHERE status = 'IN_PROGRESS';

-- 7. Kiểm tra Quota AI theo chu kỳ của User
CREATE INDEX idx_ai_quotas_user_cycle ON ai_quotas(user_id, cycle_start, cycle_end);

-- 8. Truy vấn Proposal theo trạng thái để kích hoạt (Strict Apply)
CREATE INDEX idx_schedule_proposals_roadmap_status ON schedule_proposals(roadmap_id, status);

-- 9. Báo cáo đánh giá AI Review định kỳ theo lộ trình
CREATE INDEX idx_ai_reviews_roadmap_cycle ON ai_reviews(roadmap_id, review_cycle, generated_at DESC);

-- 10. Tối ưu hóa thống kê giờ học theo Roadmap & bảo vệ Cascade Delete
CREATE INDEX idx_study_sessions_roadmap_id ON study_sessions(roadmap_id);

-- 11. Tối ưu hóa tra cứu lịch sử phiên của Task & bảo vệ Cascade Delete
CREATE INDEX idx_session_tasks_task_id ON session_tasks(task_id);

-- 12. Tối ưu hóa truy vấn tác vụ theo mốc học tập & bảo vệ Cascade Delete (FIND-DB-02)
CREATE INDEX idx_tasks_milestone_id ON tasks(milestone_id);

-- 13. Tối ưu hóa tra cứu mục tiêu của người dùng & bảo vệ Cascade Delete (FIND-DB-03)
CREATE INDEX idx_goals_user_id ON goals(user_id);

-- 14. Tối ưu hóa kiểm tra RESTRICT khi xóa mục tiêu & tra cứu lộ trình (FIND-DB-03)
CREATE INDEX idx_roadmaps_goal_id ON roadmaps(goal_id);

-- 15. Tối ưu hóa tra cứu đề xuất lịch của người dùng & bảo vệ Cascade Delete (FIND-DB-03)
CREATE INDEX idx_schedule_proposals_user_id ON schedule_proposals(user_id);

-- 16. Tối ưu hóa tra cứu lịch sử tạm dừng của lộ trình & bảo vệ Cascade Delete (FIND-DB-03)
CREATE INDEX idx_pause_records_roadmap_id ON pause_records(roadmap_id);

-- 17. Tối ưu hóa tra cứu báo cáo AI của người dùng & bảo vệ Cascade Delete (FIND-DB-03)
CREATE INDEX idx_ai_reviews_user_id ON ai_reviews(user_id);
