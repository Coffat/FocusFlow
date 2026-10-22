-- =============================================================================
-- FocusFlow Relational Database Schema DDL (PostgreSQL 16)
-- Standards: ISO/IEC 9075 SQL, 3NF/BCNF, Defense-in-Depth Constraints
-- Engine: PostgreSQL 16+ (Sử dụng hàm gen_random_uuid() ANSI/Core từ PostgreSQL 13+)
-- =============================================================================

-- =============================================================================
-- 0. HÀM DÙNG CHUNG CẬP NHẬT THỜI GIAN (TRIGGER FUNCTION)
-- =============================================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 1. BẢNG USERS
-- =============================================================================
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

-- =============================================================================
-- 2. BẢNG WEBCAL_TOKENS
-- Lưu SHA-256 digest của 32-byte hex CSPRN sinh bởi secrets.token_hex(32)
-- =============================================================================
CREATE TABLE webcal_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at TIMESTAMPTZ,
    CONSTRAINT chk_webcal_token_hash CHECK (token_hash ~ '^[0-9a-f]{64}$')
);

-- =============================================================================
-- 3. BẢNG AI_QUOTAS
-- Hỗ trợ cơ chế 2 pha: Reserve -> Commit / Release chống Race Condition
-- =============================================================================
CREATE TABLE ai_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    monthly_limit INTEGER NOT NULL DEFAULT 30 CHECK (monthly_limit > 0),
    used_calls INTEGER NOT NULL DEFAULT 0 CHECK (used_calls >= 0),
    reserved_calls INTEGER NOT NULL DEFAULT 0 CHECK (reserved_calls >= 0),
    tokens_consumed BIGINT NOT NULL DEFAULT 0 CHECK (tokens_consumed >= 0),
    cycle_start TIMESTAMPTZ NOT NULL,
    cycle_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ai_quota_limit CHECK (used_calls + reserved_calls <= monthly_limit),
    CONSTRAINT chk_ai_quota_cycle CHECK (cycle_end > cycle_start)
);

-- =============================================================================
-- 4. BẢNG AI_QUOTA_RESERVATIONS
-- Nhật ký theo dõi giữ chỗ hạn ngạch AI 2 pha (Reserve -> Commit/Release)
-- Chống rò rỉ quota khi Celery Worker hoặc SSE stream gặp sự cố gián đoạn
-- =============================================================================
CREATE TABLE ai_quota_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'RESERVED' 
        CHECK (status IN ('RESERVED', 'COMMITTED', 'RELEASED', 'EXPIRED')),
    estimated_tokens INTEGER NOT NULL DEFAULT 0 CHECK (estimated_tokens >= 0),
    tokens_consumed INTEGER NOT NULL DEFAULT 0 CHECK (tokens_consumed >= 0),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 5. BẢNG AVAILABILITIES
-- Mỗi User có duy nhất 1 cấu hình quỹ thời gian rảnh
-- =============================================================================
CREATE TABLE availabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    mode VARCHAR(10) NOT NULL DEFAULT 'MODE_A' CHECK (mode IN ('MODE_A', 'MODE_B')),
    calendar_integration_mode VARCHAR(20) NOT NULL DEFAULT 'NONE' 
        CHECK (calendar_integration_mode IN ('NONE', 'EXPORT_ICS', 'CONNECTED')),
    weekly_schedule JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_availabilities_schedule_json CHECK (jsonb_typeof(weekly_schedule) = 'object')
);

-- =============================================================================
-- 6. BẢNG GOALS
-- =============================================================================
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    target_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_goals_id_user UNIQUE (id, user_id)
);

-- =============================================================================
-- 7. BẢNG ROADMAPS
-- Cho phép nhiều Roadmap ACTIVE song song phục vụ đa mục tiêu học tập
-- Khóa ngoại phức hợp (goal_id, user_id) bảo đảm cùng sở hữu (cross-tenant integrity)
-- ON DELETE NO ACTION ngăn lỗi cascade khi xóa user, đồng thời chặn xóa goal khi còn roadmap
-- =============================================================================
CREATE TABLE roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'INITIALIZED' 
        CHECK (status IN ('INITIALIZED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')),
    start_date DATE,
    target_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_roadmaps_id_user UNIQUE (id, user_id),
    CONSTRAINT fk_roadmaps_goal_user FOREIGN KEY (goal_id, user_id) 
        REFERENCES goals(id, user_id) ON DELETE NO ACTION,
    CONSTRAINT chk_roadmap_dates CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date)
);

-- =============================================================================
-- 8. BẢNG MILESTONES
-- Thứ tự tuần tự sequence_order là duy nhất trong cùng một Roadmap
-- DEFERRABLE INITIALLY DEFERRED cho phép hoán đổi thứ tự milestone trong cùng một giao dịch
-- =============================================================================
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL CHECK (sequence_order >= 1),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_milestone_roadmap_sequence UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT uq_milestone_id_roadmap UNIQUE (id, roadmap_id)
);

-- =============================================================================
-- 9. BẢNG SCHEDULE_PROPOSALS
-- Khóa ngoại phức hợp (roadmap_id, user_id) bảo đảm tính toàn vẹn cùng chủ sở hữu
-- =============================================================================
CREATE TABLE schedule_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    user_id UUID NOT NULL,
    proposal_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'APPLIED', 'DISCARDED')),
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_schedule_proposals_roadmap_user FOREIGN KEY (roadmap_id, user_id) 
        REFERENCES roadmaps(id, user_id) ON DELETE CASCADE,
    CONSTRAINT chk_proposal_data_json CHECK (jsonb_typeof(proposal_data) = 'object')
);

-- =============================================================================
-- 10. BẢNG OFFICIAL_SCHEDULES
-- =============================================================================
CREATE TABLE official_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL UNIQUE REFERENCES roadmaps(id) ON DELETE CASCADE,
    total_sessions INTEGER NOT NULL DEFAULT 0 CHECK (total_sessions >= 0),
    total_planned_minutes INTEGER NOT NULL DEFAULT 0 CHECK (total_planned_minutes >= 0),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 11. BẢNG TASKS
-- Bảo vệ tính nhất quán khung giờ và trạng thái hoàn thành
-- Khóa ngoại phức hợp (milestone_id, roadmap_id) ngăn chặn hoàn toàn lệch lộ trình
-- =============================================================================
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
        CHECK (status IN ('PENDING', 'TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    completed_at TIMESTAMPTZ,
    reschedule_count INTEGER NOT NULL DEFAULT 0 CHECK (reschedule_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tasks_id_roadmap UNIQUE (id, roadmap_id),
    CONSTRAINT fk_tasks_milestone_roadmap FOREIGN KEY (milestone_id, roadmap_id) 
        REFERENCES milestones(id, roadmap_id) ON DELETE CASCADE,
    CONSTRAINT chk_task_schedule_dates CHECK (scheduled_date IS NOT NULL OR (start_time IS NULL AND end_time IS NULL)),
    CONSTRAINT chk_task_time_window CHECK (start_time IS NULL OR end_time IS NULL OR start_time < end_time),
    CONSTRAINT chk_task_completed_at CHECK ((status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status != 'COMPLETED' AND completed_at IS NULL))
);

-- =============================================================================
-- 12. BẢNG STUDY_SESSIONS
-- Bảo vệ toàn vẹn thời gian học và trạng thái kết thúc phiên
-- Khóa ngoại phức hợp (roadmap_id, user_id) bảo đảm tính toàn vẹn cùng chủ sở hữu
-- =============================================================================
CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    roadmap_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    planned_minutes INTEGER NOT NULL CHECK (planned_minutes > 0),
    actual_minutes INTEGER NOT NULL DEFAULT 0 CHECK (actual_minutes >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS' 
        CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED')),
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_study_sessions_id_roadmap UNIQUE (id, roadmap_id),
    CONSTRAINT fk_study_sessions_roadmap_user FOREIGN KEY (roadmap_id, user_id) 
        REFERENCES roadmaps(id, user_id) ON DELETE CASCADE,
    CONSTRAINT chk_session_times CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT chk_session_status_ended CHECK ((status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL))
);

-- =============================================================================
-- 13. BẢNG SESSION_TASKS
-- Bảng liên kết quan hệ N:M giữa phiên học và các task thực hiện trong phiên
-- Khóa ngoại phức hợp kép (session_id, roadmap_id) và (task_id, roadmap_id)
-- ON DELETE RESTRICT trên task bảo vệ lịch sử học tập (chặn xóa task đã có phiên học)
-- =============================================================================
CREATE TABLE session_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    task_id UUID NOT NULL,
    roadmap_id UUID NOT NULL,
    allocated_minutes INTEGER NOT NULL DEFAULT 0 CHECK (allocated_minutes >= 0),
    is_completed_in_session BOOLEAN NOT NULL DEFAULT FALSE,
    time_spent_minutes INTEGER NOT NULL DEFAULT 0 CHECK (time_spent_minutes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_session_tasks_session FOREIGN KEY (session_id, roadmap_id) 
        REFERENCES study_sessions(id, roadmap_id) ON DELETE CASCADE,
    CONSTRAINT fk_session_tasks_task FOREIGN KEY (task_id, roadmap_id) 
        REFERENCES tasks(id, roadmap_id) ON DELETE RESTRICT,
    CONSTRAINT uq_session_task UNIQUE (session_id, task_id)
);

-- =============================================================================
-- 14. BẢNG STUDY_NOTES
-- Mỗi phiên học có duy nhất 1 Scratchpad và 1 Takeaway
-- =============================================================================
CREATE TABLE study_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE,
    note_type VARCHAR(20) NOT NULL CHECK (note_type IN ('SCRATCHPAD', 'TAKEAWAY')),
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_note_type UNIQUE (session_id, note_type)
);

-- =============================================================================
-- 15. BẢNG PAUSE_RECORDS
-- Ràng buộc tính toán số ngày tịnh tiến khớp chính xác khoảng thời gian tạm dừng
-- =============================================================================
CREATE TABLE pause_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    pause_start_date DATE NOT NULL,
    pause_end_date DATE NOT NULL,
    shifted_days INTEGER NOT NULL CHECK (shifted_days > 0),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_pause_dates CHECK (pause_end_date >= pause_start_date),
    CONSTRAINT chk_pause_duration CHECK (shifted_days = (pause_end_date - pause_start_date + 1))
);

-- =============================================================================
-- 16. BẢNG AI_REVIEWS
-- Khóa ngoại phức hợp (roadmap_id, user_id) bảo đảm cùng chủ sở hữu
-- Hỗ trợ phân biệt tường minh chu kỳ MILESTONE (gắn milestone_id) và WEEKLY (gắn kỳ báo cáo)
-- =============================================================================
CREATE TABLE ai_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    user_id UUID NOT NULL,
    milestone_id UUID REFERENCES milestones(id) ON DELETE CASCADE,
    review_cycle VARCHAR(20) NOT NULL CHECK (review_cycle IN ('WEEKLY', 'MILESTONE')),
    period_start DATE,
    period_end DATE,
    quantitative_summary JSONB NOT NULL,
    strengths_feedback TEXT NOT NULL,
    bottlenecks_feedback TEXT NOT NULL,
    action_recommendations TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ai_reviews_roadmap_user FOREIGN KEY (roadmap_id, user_id) 
        REFERENCES roadmaps(id, user_id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_review_period CHECK (
        (review_cycle = 'MILESTONE' AND milestone_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR
        (review_cycle = 'WEEKLY' AND milestone_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)
    ),
    CONSTRAINT chk_quantitative_summary_json CHECK (jsonb_typeof(quantitative_summary) = 'object')
);

-- =============================================================================
-- TỰ ĐỘNG CẬP NHẬT UPDATED_AT CHO TẤT CẢ CÁC BẢNG (TRIGGERS)
-- =============================================================================
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_ai_quotas_updated_at BEFORE UPDATE ON ai_quotas FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_ai_quota_reservations_updated_at BEFORE UPDATE ON ai_quota_reservations FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_availabilities_updated_at BEFORE UPDATE ON availabilities FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_goals_updated_at BEFORE UPDATE ON goals FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_roadmaps_updated_at BEFORE UPDATE ON roadmaps FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_milestones_updated_at BEFORE UPDATE ON milestones FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_schedule_proposals_updated_at BEFORE UPDATE ON schedule_proposals FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_official_schedules_updated_at BEFORE UPDATE ON official_schedules FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_study_sessions_updated_at BEFORE UPDATE ON study_sessions FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_study_notes_updated_at BEFORE UPDATE ON study_notes FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- CHỈ MỤC HIỆU NĂNG & BẢO VỆ ĐỒNG THỜI (INDEXES & CONCURRENCY CONSTRAINTS)
-- =============================================================================

-- 1. Bảo vệ tính duy nhất email không phân biệt hoa thường (Case-insensitive email uniqueness)
CREATE UNIQUE INDEX uq_users_lower_email ON users (LOWER(email));

-- 2. Bất biến duy nhất 1 Active Study Session cho mỗi User tại một thời điểm (Chống race condition)
CREATE UNIQUE INDEX uq_user_single_active_session ON study_sessions(user_id) WHERE status = 'IN_PROGRESS';

-- 3. Bất biến duy nhất 1 Proposal DRAFT cho mỗi Roadmap tại một thời điểm
CREATE UNIQUE INDEX uq_one_draft_per_roadmap ON schedule_proposals(roadmap_id) WHERE status = 'DRAFT';

-- 4. Chống tạo trùng báo cáo đánh giá AI Review tuần định kỳ (Idempotency cho Celery Retry)
CREATE UNIQUE INDEX uq_ai_reviews_weekly ON ai_reviews (roadmap_id, period_start, period_end) WHERE review_cycle = 'WEEKLY';

-- 5. Chống tạo trùng báo cáo đánh giá AI Review theo mốc (Idempotency cho Celery Retry)
CREATE UNIQUE INDEX uq_ai_reviews_milestone ON ai_reviews (roadmap_id, milestone_id) WHERE review_cycle = 'MILESTONE';

-- 6. Truy vấn nóng lịch sử học tập & Dashboard của User
CREATE INDEX idx_study_sessions_user_started ON study_sessions(user_id, started_at DESC);

-- 7. Truy vấn các Roadmap của User theo trạng thái
CREATE INDEX idx_roadmaps_user_status ON roadmaps(user_id, status);

-- 8. Truy vấn Task theo Roadmap và ngày xếp lịch
CREATE INDEX idx_tasks_roadmap_scheduled_date ON tasks(roadmap_id, scheduled_date);

-- 9. Phát hiện Task quá hạn tất định (Deterministic Overdue Formula - BUSR-06)
CREATE INDEX idx_tasks_overdue ON tasks(scheduled_date) WHERE status IN ('PENDING', 'TODO') AND scheduled_date IS NOT NULL;

-- 10. Monitor Heartbeat phiên học gián đoạn (Celery Beat Background Job - BUSR-09)
CREATE INDEX idx_study_sessions_in_progress ON study_sessions(last_heartbeat_at) WHERE status = 'IN_PROGRESS';

-- 11. Dọn dẹp reservation quota quá hạn (Background Sweeper)
CREATE INDEX idx_quota_reservations_cleanup ON ai_quota_reservations(expires_at) WHERE status = 'RESERVED';

-- 12. Bảo vệ Cascade Delete & tra cứu reservation theo người dùng
CREATE INDEX idx_quota_reservations_user_id ON ai_quota_reservations(user_id);

-- 13. Truy vấn Proposal theo trạng thái để kích hoạt (Strict Apply)
CREATE INDEX idx_schedule_proposals_roadmap_status ON schedule_proposals(roadmap_id, status);

-- 14. Báo cáo đánh giá AI Review định kỳ theo lộ trình
CREATE INDEX idx_ai_reviews_roadmap_cycle ON ai_reviews(roadmap_id, review_cycle, generated_at DESC);

-- 15. Tối ưu hóa thống kê giờ học theo Roadmap sắp xếp theo thời gian & bảo vệ Cascade Delete
CREATE INDEX idx_study_sessions_roadmap_started ON study_sessions(roadmap_id, started_at DESC);

-- 16. Tối ưu hóa tra cứu lịch sử phiên của Task & bảo vệ Cascade Delete
CREATE INDEX idx_session_tasks_task_id ON session_tasks(task_id);

-- 17. Tối ưu hóa tra cứu task theo roadmap trong session_tasks & bảo vệ Cascade Delete
CREATE INDEX idx_session_tasks_roadmap_id ON session_tasks(roadmap_id);

-- 18. Tối ưu hóa truy vấn tác vụ theo mốc và lộ trình & bảo vệ Cascade Delete
CREATE INDEX idx_tasks_milestone_roadmap ON tasks(milestone_id, roadmap_id);

-- 19. Tối ưu hóa tra cứu mục tiêu của người dùng & bảo vệ Cascade Delete
CREATE INDEX idx_goals_user_id ON goals(user_id);

-- 20. Tối ưu hóa tra cứu lộ trình theo mục tiêu & bảo vệ khóa ngoại
CREATE INDEX idx_roadmaps_goal_id ON roadmaps(goal_id);

-- 21. Tối ưu hóa tra cứu đề xuất lịch của người dùng & bảo vệ Cascade Delete
CREATE INDEX idx_schedule_proposals_user_id ON schedule_proposals(user_id);

-- 22. Tối ưu hóa tra cứu lịch sử tạm dừng của lộ trình & bảo vệ Cascade Delete
CREATE INDEX idx_pause_records_roadmap_id ON pause_records(roadmap_id);

-- 23. Tối ưu hóa tra cứu báo cáo AI của người dùng & bảo vệ Cascade Delete
CREATE INDEX idx_ai_reviews_user_id ON ai_reviews(user_id);

-- 24. Tối ưu hóa tra cứu báo cáo AI theo milestone & bảo vệ Cascade Delete
CREATE INDEX idx_ai_reviews_milestone_id ON ai_reviews(milestone_id);

-- =============================================================================
-- 17. BẢNG TASK_DEPENDENCIES (HẠNG MỤC 5 - TASK PREREQUISITE DEPENDENCY)
-- Lưu quan hệ phụ thuộc tiên quyết có hướng giữa các Task trong cùng Roadmap.
-- Ràng buộc chk_no_self_dependency ngăn phụ thuộc chính nó; chu trình được kiểm tra ở Domain Service.
-- =============================================================================
CREATE TABLE task_dependencies (
    predecessor_id UUID NOT NULL,
    successor_id UUID NOT NULL,
    roadmap_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (predecessor_id, successor_id),
    CONSTRAINT chk_no_self_dependency CHECK (predecessor_id <> successor_id),
    CONSTRAINT fk_task_deps_pred FOREIGN KEY (predecessor_id, roadmap_id) 
        REFERENCES tasks(id, roadmap_id) ON DELETE CASCADE,
    CONSTRAINT fk_task_deps_succ FOREIGN KEY (successor_id, roadmap_id) 
        REFERENCES tasks(id, roadmap_id) ON DELETE CASCADE
);

CREATE INDEX idx_task_deps_successor ON task_dependencies(successor_id);
CREATE INDEX idx_task_deps_predecessor ON task_dependencies(predecessor_id);
CREATE INDEX idx_task_deps_roadmap ON task_dependencies(roadmap_id);

-- =============================================================================
-- 18. BẢNG LEARNER_PROFILES (HẠNG MỤC 3 - LEARNER PROFILE MEMORY - ZIMMERMAN SRL)
-- Hồ sơ học tập cá nhân hóa được tổng hợp bất đồng bộ qua Celery định kỳ (N >= 5 phiên).
-- Dữ liệu hỗ trợ AI Planner hiệu chỉnh thời lượng task và độ dốc nhận thức.
-- =============================================================================
CREATE TABLE learner_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    optimal_focus_duration_mins INTEGER NOT NULL DEFAULT 25 
        CHECK (optimal_focus_duration_mins BETWEEN 15 AND 120),
    peak_productivity_slots JSONB NOT NULL DEFAULT '["MORNING", "EVENING"]'::jsonb,
    estimation_bias_factor NUMERIC(4, 2) NOT NULL DEFAULT 1.00 
        CHECK (estimation_bias_factor BETWEEN 0.50 AND 2.00),
    weekly_completion_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00 
        CHECK (weekly_completion_rate BETWEEN 0.00 AND 100.00),
    total_completed_sessions INTEGER NOT NULL DEFAULT 0 
        CHECK (total_completed_sessions >= 0),
    is_cold_start BOOLEAN NOT NULL DEFAULT TRUE,
    last_aggregated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 19. BẢNG SCHEDULE_CHANGE_LOGS (HẠNG MỤC 5 - AUDIT LOGGING)
-- Lưu vết các biến động lịch trình quan trọng (dời lịch, Domino Shift, Stalled, Backlog).
-- =============================================================================
CREATE TABLE schedule_change_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL 
        CHECK (actor_type IN ('USER', 'SYSTEM_ADAPT', 'SYSTEM_DOMINO', 'AI_PROPOSAL')),
    action VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_schedule_logs_roadmap ON schedule_change_logs(roadmap_id, created_at DESC);
CREATE INDEX idx_schedule_logs_task ON schedule_change_logs(task_id, created_at DESC);
