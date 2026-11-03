-- =============================================================================
-- FocusFlow Relational Database Schema DDL v3.0 (PostgreSQL 16)
-- Kiến trúc: Context-First Modular Monolith (4 Bounded Contexts + Shared Kernel)
-- Tổng số bảng vật lý: 24 Bảng chuẩn hóa nghiêm ngặt 3NF/BCNF
-- Tiêu chuẩn: ISO/IEC 9075:2023 SQL, Defense-in-Depth Constraints, ACID Outbox
-- Chiến lược Khóa chính: UUIDv7 sinh tại Backend (FastAPI - RFC 9562), fallback DB
-- Quy tắc Modular Monolith: Giữ FK vật lý ở tầng DB để bảo toàn toàn vẹn tham chiếu,
--                           nhưng cấm ORM JOIN chéo Context trong code (giao tiếp qua
--                           public_api.py và Transactional Outbox outbox_events).
-- Quản lý Thời gian: TIMESTAMPTZ (UTC) cho toàn bộ mốc thời gian; cột timezone trong users
-- =============================================================================

-- =============================================================================
-- 0. HÀM TRIGGER DÙNG CHUNG CẬP NHẬT UPDATED_AT (18 BẢNG CÓ CỘT UPDATED_AT)
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- BOUNDED CONTEXT 1: ACCOUNT (`account` — 9 BẢNG)
-- Trách nhiệm: Quản lý định danh, xác thực, hồ sơ năng lực SRL, cấu hình lịch rảnh
--              Mode A/B, hạn ngạch AI 2 pha và thanh toán nâng cấp gói dịch vụ.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. BẢNG USERS (Người dùng hệ thống)
-- Gốc quản lý định danh người học, phân quyền RBAC, gói dịch vụ và trạng thái khóa
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    role VARCHAR(20) NOT NULL DEFAULT 'LEARNER',
    tier VARCHAR(20) NOT NULL DEFAULT 'FREE',
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_role CHECK (role IN ('LEARNER', 'ADMIN')),
    CONSTRAINT chk_users_tier CHECK (tier IN ('FREE', 'PREMIUM'))
);

-- -----------------------------------------------------------------------------
-- 2. BẢNG LEARNER_PROFILES (Hồ sơ Năng lực & Trí nhớ Người học - Zimmerman SRL)
-- Quan hệ 1:1 với users, lưu trữ thói quen học tập được tổng hợp qua Taskiq Worker
-- -----------------------------------------------------------------------------
CREATE TABLE learner_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    optimal_focus_duration_mins INTEGER NOT NULL DEFAULT 25,
    peak_productivity_slots JSONB NOT NULL DEFAULT '["MORNING", "EVENING"]'::jsonb,
    estimation_bias_factor NUMERIC(4, 2) NOT NULL DEFAULT 1.00,
    weekly_completion_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    total_completed_sessions INTEGER NOT NULL DEFAULT 0,
    is_cold_start BOOLEAN NOT NULL DEFAULT TRUE,
    last_aggregated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_learner_profiles_user_id UNIQUE (user_id),
    CONSTRAINT fk_learner_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_learner_profiles_duration CHECK (optimal_focus_duration_mins BETWEEN 15 AND 120),
    CONSTRAINT chk_learner_profiles_bias CHECK (estimation_bias_factor BETWEEN 0.50 AND 2.00),
    CONSTRAINT chk_learner_profiles_rate CHECK (weekly_completion_rate BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_learner_profiles_sessions CHECK (total_completed_sessions >= 0)
);

-- -----------------------------------------------------------------------------
-- 3. BẢNG WEBCAL_TOKENS (Token Đồng bộ Lịch Ngoài iCal/WebCal & OAuth Sync Metadata)
-- Lưu SHA-256 digest của 32-byte hex CSPRN và token OAuth mã hóa Fernet (tùy chọn)
-- -----------------------------------------------------------------------------
CREATE TABLE webcal_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    oauth_refresh_token_encrypted TEXT,
    external_calendar_id VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    rotated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_webcal_tokens_user_id UNIQUE (user_id),
    CONSTRAINT uq_webcal_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_webcal_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_webcal_tokens_hash CHECK (token_hash ~ '^[0-9a-f]{64}$')
);

-- -----------------------------------------------------------------------------
-- 4. BẢNG AVAILABILITIES (Cấu hình Quỹ Thời gian Rảnh Tổng thể)
-- Mỗi người dùng có 1 bản ghi cấu hình chế độ rảnh (Mode A quỹ giờ / Mode B khung giờ)
-- -----------------------------------------------------------------------------
CREATE TABLE availabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'MODE_A',
    calendar_integration_mode VARCHAR(20) NOT NULL DEFAULT 'NONE',
    daily_quotas JSONB NOT NULL DEFAULT '{}'::jsonb,
    min_session_minutes INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_availabilities_user_id UNIQUE (user_id),
    CONSTRAINT fk_availabilities_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_availabilities_mode CHECK (mode IN ('MODE_A', 'MODE_B')),
    CONSTRAINT chk_availabilities_cal_mode CHECK (calendar_integration_mode IN ('NONE', 'EXPORT_ICS', 'CONNECTED')),
    CONSTRAINT chk_availabilities_min_session CHECK (min_session_minutes BETWEEN 15 AND 120)
);

-- -----------------------------------------------------------------------------
-- 5. BẢNG AVAILABILITY_SLOTS (Khung Giờ Rảnh Chi tiết - Chuẩn hóa 100% 3NF)
-- Ánh xạ trực tiếp sang Value Object WeeklySchedule & TimeSlot tại Repository Layer
-- -----------------------------------------------------------------------------
CREATE TABLE availability_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    availability_id UUID NOT NULL,
    day_of_week SMALLINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    end_day_offset SMALLINT NOT NULL DEFAULT 0,
    slot_type VARCHAR(20) NOT NULL DEFAULT 'ALLOWED',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_avail_slots_availability FOREIGN KEY (availability_id) REFERENCES availabilities(id) ON DELETE CASCADE,
    CONSTRAINT chk_avail_slots_day CHECK (day_of_week BETWEEN 0 AND 6),
    CONSTRAINT chk_avail_slots_offset CHECK (end_day_offset IN (0, 1)),
    CONSTRAINT chk_avail_slots_type CHECK (slot_type IN ('ALLOWED', 'FIXED')),
    CONSTRAINT chk_avail_slots_time CHECK (end_day_offset = 1 OR end_time > start_time)
);

-- -----------------------------------------------------------------------------
-- 6. BẢNG AI_QUOTAS (Hạn ngạch AI Chu kỳ Hiện tại - 2-Phase ACID Quota Guard)
-- Quản trị số lượt gọi AI theo chu kỳ tháng (Free: 30, Premium: 300) kèm reserved_calls
-- -----------------------------------------------------------------------------
CREATE TABLE ai_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    monthly_limit INTEGER NOT NULL DEFAULT 30,
    used_calls INTEGER NOT NULL DEFAULT 0,
    reserved_calls INTEGER NOT NULL DEFAULT 0,
    tokens_consumed BIGINT NOT NULL DEFAULT 0,
    cycle_start TIMESTAMPTZ NOT NULL,
    cycle_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ai_quotas_user_id UNIQUE (user_id),
    CONSTRAINT fk_ai_quotas_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_quotas_monthly_limit CHECK (monthly_limit > 0),
    CONSTRAINT chk_ai_quotas_used_calls CHECK (used_calls >= 0),
    CONSTRAINT chk_ai_quotas_reserved_calls CHECK (reserved_calls >= 0),
    CONSTRAINT chk_ai_quotas_tokens CHECK (tokens_consumed >= 0),
    CONSTRAINT chk_ai_quotas_limit CHECK (used_calls + reserved_calls <= monthly_limit),
    CONSTRAINT chk_ai_quotas_cycle CHECK (cycle_end > cycle_start)
);

-- -----------------------------------------------------------------------------
-- 7. BẢNG AI_QUOTA_RESERVATIONS (Sổ cái Giữ chỗ Hạn ngạch AI 2 Pha - NEW v3.0)
-- Đảm bảo 0% mất hạn ngạch khi luồng gọi LLM bị timeout hoặc ngắt kết nối SSE
-- -----------------------------------------------------------------------------
CREATE TABLE ai_quota_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quota_id UUID NOT NULL,
    user_id UUID NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'RESERVED',
    tokens_reserved INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT fk_ai_quota_res_quota FOREIGN KEY (quota_id) REFERENCES ai_quotas(id) ON DELETE CASCADE,
    CONSTRAINT fk_ai_quota_res_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_quota_res_status CHECK (status IN ('RESERVED', 'COMMITTED', 'RELEASED', 'EXPIRED')),
    CONSTRAINT chk_ai_quota_res_tokens CHECK (tokens_reserved >= 0),
    CONSTRAINT chk_ai_quota_res_resolved CHECK (
        (status = 'RESERVED' AND resolved_at IS NULL) OR
        (status != 'RESERVED' AND resolved_at IS NOT NULL)
    )
);

-- -----------------------------------------------------------------------------
-- 8. BẢNG AI_USAGE_LOGS (Nhật ký Kiểm toán Gọi Dịch vụ AI Chi tiết)
-- Ghi nhận lịch sử kiểm toán đa nhà cung cấp (Provider-Agnostic LLMPort)
-- -----------------------------------------------------------------------------
CREATE TABLE ai_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL DEFAULT 'gpt-4o-mini',
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ai_usage_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_usage_logs_action CHECK (action_type IN (
        'ROADMAP_GENERATION',
        'SCHEDULE_PROPOSAL',
        'AI_REVIEW_WEEKLY',
        'AI_REVIEW_MILESTONE',
        'MILESTONE_BREAKDOWN',
        'CHAT_ASSISTANT'
    )),
    CONSTRAINT chk_ai_usage_logs_tokens CHECK (prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0),
    CONSTRAINT chk_ai_usage_logs_latency CHECK (latency_ms >= 0),
    CONSTRAINT chk_ai_usage_logs_status CHECK (status IN ('SUCCESS', 'FAILED', 'RATE_LIMITED', 'TIMEOUT'))
);

-- -----------------------------------------------------------------------------
-- 9. BẢNG PAYMENT_TRANSACTIONS (Giao dịch Thanh toán Nâng cấp Gói - NEW v3.0)
-- Hỗ trợ cổng thanh toán PayOS, VNPay Sandbox và LocalMockPaymentAdapter
-- -----------------------------------------------------------------------------
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    transaction_ref VARCHAR(100) NOT NULL,
    gateway_provider VARCHAR(20) NOT NULL DEFAULT 'PAYOS',
    amount_vnd INTEGER NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'VND',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    qr_code_url TEXT,
    webhook_signature_verified BOOLEAN NOT NULL DEFAULT FALSE,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payment_transactions_ref UNIQUE (transaction_ref),
    CONSTRAINT fk_payment_transactions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_payment_transactions_provider CHECK (gateway_provider IN ('PAYOS', 'VNPAY', 'MOCK')),
    CONSTRAINT chk_payment_transactions_amount CHECK (amount_vnd > 0),
    CONSTRAINT chk_payment_transactions_status CHECK (status IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'REFUNDED')),
    CONSTRAINT chk_payment_transactions_paid_at CHECK (
        (status IN ('PAID', 'REFUNDED') AND paid_at IS NOT NULL) OR
        (status NOT IN ('PAID', 'REFUNDED') AND paid_at IS NULL)
    )
);

-- =============================================================================
-- BOUNDED CONTEXT 2: PLANNING (`planning` — 5 BẢNG)
-- Trách nhiệm: Quản lý mục tiêu, lộ trình, cột mốc, lịch học chính thức (Frozen Baseline)
--              và đề xuất lịch xem trước qua cổng kiểm duyệt AI 3 tầng.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 10. BẢNG GOALS (Mục tiêu Học tập)
-- Mục tiêu tổng quát của người học trước khi phân rã thành lộ trình
-- -----------------------------------------------------------------------------
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    target_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    prior_knowledge_level VARCHAR(50) NOT NULL DEFAULT 'BEGINNER',
    clarification_context TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_goals_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_goals_status CHECK (status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED'))
);

-- -----------------------------------------------------------------------------
-- 11. BẢNG ROADMAPS (Lộ trình Tự học Thích ứng)
-- Bản thiết kế học tập chia nhỏ từ mục tiêu, quản lý trạng thái vòng đời
-- -----------------------------------------------------------------------------
CREATE TABLE roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    goal_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'INITIALIZED',
    start_date DATE,
    target_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_roadmaps_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_roadmaps_goal FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    CONSTRAINT chk_roadmaps_status CHECK (status IN ('INITIALIZED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')),
    CONSTRAINT chk_roadmaps_dates CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date)
);

-- -----------------------------------------------------------------------------
-- 12. BẢNG MILESTONES (Các Mốc Kiến thức Tuần tự Cấp 1)
-- Thứ tự sequence_order là duy nhất trong cùng Roadmap, hỗ trợ hoán đổi thứ tự
-- -----------------------------------------------------------------------------
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    sequence_order INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_milestones_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT uq_milestones_roadmap_seq UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT chk_milestones_seq CHECK (sequence_order >= 1),
    CONSTRAINT chk_milestones_status CHECK (status IN ('PENDING', 'APPROVED', 'IN_PROGRESS', 'COMPLETED'))
);

-- -----------------------------------------------------------------------------
-- 13. BẢNG OFFICIAL_SCHEDULES (Lịch trình Học tập Chính thức - Frozen Baseline)
-- Đóng băng chỉ số kế hoạch cơ sở (total_sessions, total_planned_minutes) cho KPI 3
-- -----------------------------------------------------------------------------
CREATE TABLE official_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    total_sessions INTEGER NOT NULL DEFAULT 0,
    total_planned_minutes INTEGER NOT NULL DEFAULT 0,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_official_schedules_roadmap UNIQUE (roadmap_id),
    CONSTRAINT fk_official_schedules_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_official_schedules_sessions CHECK (total_sessions >= 0),
    CONSTRAINT chk_official_schedules_minutes CHECK (total_planned_minutes >= 0)
);

-- -----------------------------------------------------------------------------
-- 14. BẢNG SCHEDULE_PROPOSALS (Bản Đề xuất Lịch Xem trước từ AI - Preview Draft)
-- Chứa proposal_data JSONB xem trước, chỉ lưu sau khi qua 3-Tier Validation Gate
-- -----------------------------------------------------------------------------
CREATE TABLE schedule_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    user_id UUID NOT NULL,
    proposal_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_schedule_proposals_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_schedule_proposals_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_schedule_proposals_status CHECK (status IN ('DRAFT', 'APPLIED', 'DISCARDED')),
    CONSTRAINT chk_schedule_proposals_data CHECK (jsonb_typeof(proposal_data) = 'object')
);

-- -----------------------------------------------------------------------------
-- 14b. BẢNG LEARNING_CONCEPTS & CONCEPT_PREREQUISITES (Cơ sở Tri thức Học thuật Đã Xác thực)
-- Phục vụ tra cứu chỉ đọc (Read-only Tool Calling) cho AI Milestone Planner & Task Decomposer
-- -----------------------------------------------------------------------------
CREATE TABLE learning_concepts (
    concept_id VARCHAR(120) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    domain VARCHAR(100) NOT NULL,
    difficulty_level VARCHAR(50) NOT NULL DEFAULT 'BEGINNER',
    estimated_effort_minutes INTEGER NOT NULL DEFAULT 60,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    learning_outcomes JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED',
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_learning_concepts_verification_status CHECK (verification_status IN ('VERIFIED', 'UNVERIFIED', 'DEPRECATED')),
    CONSTRAINT chk_learning_concepts_effort_positive CHECK (estimated_effort_minutes > 0)
);

CREATE TABLE concept_prerequisites (
    source_concept_id VARCHAR(120) NOT NULL,
    prerequisite_concept_id VARCHAR(120) NOT NULL,
    relation_type VARCHAR(30) NOT NULL DEFAULT 'REQUIRES',
    rationale TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_concept_id, prerequisite_concept_id),
    CONSTRAINT fk_concept_prerequisites_source FOREIGN KEY (source_concept_id) REFERENCES learning_concepts(concept_id) ON DELETE CASCADE,
    CONSTRAINT fk_concept_prerequisites_prereq FOREIGN KEY (prerequisite_concept_id) REFERENCES learning_concepts(concept_id) ON DELETE CASCADE,
    CONSTRAINT chk_concept_prerequisites_relation_type CHECK (relation_type IN ('REQUIRES', 'RECOMMENDED_BEFORE')),
    CONSTRAINT chk_concept_prerequisites_no_self_loop CHECK (source_concept_id <> prerequisite_concept_id)
);

-- =============================================================================
-- BOUNDED CONTEXT 3: EXECUTION (`execution` — 5 BẢNG)
-- Trách nhiệm: Quản lý nhiệm vụ học tập chi tiết (tasks), đồ thị tiên quyết DAG
--              (task_dependencies), vận hành không gian học tập Pomodoro/Stopwatch,
--              ghi nhận Heartbeat 60s, thu hồi phiên học treo và ghi chú phiên học.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 15. BẢNG TASKS (Nhiệm vụ Học tập Chi tiết Cấp 2)
-- Lên lịch trực tiếp qua scheduled_date, scheduled_start, scheduled_end
-- -----------------------------------------------------------------------------
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    milestone_id UUID NOT NULL,
    official_schedule_id UUID,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    estimated_minutes INTEGER NOT NULL,
    scheduled_date DATE,
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'TODO',
    completed_at TIMESTAMPTZ,
    reschedule_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_tasks_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_tasks_milestone FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
    CONSTRAINT fk_tasks_official_schedule FOREIGN KEY (official_schedule_id) REFERENCES official_schedules(id) ON DELETE SET NULL,
    CONSTRAINT chk_tasks_estimated_minutes CHECK (estimated_minutes BETWEEN 15 AND 240),
    CONSTRAINT chk_tasks_status CHECK (status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    CONSTRAINT chk_tasks_reschedule_count CHECK (reschedule_count >= 0),
    CONSTRAINT chk_tasks_scheduled_time_order CHECK (
        (scheduled_start IS NULL AND scheduled_end IS NULL)
        OR (scheduled_start IS NOT NULL AND scheduled_end IS NOT NULL AND scheduled_end > scheduled_start)
    ),
    CONSTRAINT chk_tasks_completed_at CHECK (
        (status = 'COMPLETED' AND completed_at IS NOT NULL) OR
        (status != 'COMPLETED' AND completed_at IS NULL)
    )
);

-- -----------------------------------------------------------------------------
-- 16. BẢNG TASK_DEPENDENCIES (Quan hệ Tiên quyết Giữa các Nhiệm vụ - DAG)
-- Quản lý đồ thị có hướng không chu trình (DAG), kiểm định bởi DagCycleValidator
-- -----------------------------------------------------------------------------
CREATE TABLE task_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    predecessor_id UUID NOT NULL,
    successor_id UUID NOT NULL,
    roadmap_id UUID NOT NULL,
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_task_deps_pair UNIQUE (predecessor_id, successor_id),
    CONSTRAINT fk_task_deps_pred FOREIGN KEY (predecessor_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_task_deps_succ FOREIGN KEY (successor_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_task_deps_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_task_deps_not_self CHECK (predecessor_id <> successor_id)
);

-- -----------------------------------------------------------------------------
-- 17. BẢNG STUDY_SESSIONS (Phiên Thực thi Học tập Pomodoro / Stopwatch)
-- Ghi nhận thời lượng dự kiến, thời gian thực tế và tín hiệu duy trì Heartbeat 60s
-- -----------------------------------------------------------------------------
CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    roadmap_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    planned_minutes INTEGER NOT NULL,
    actual_minutes INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_study_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_study_sessions_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_study_sessions_planned_min CHECK (planned_minutes > 0),
    CONSTRAINT chk_study_sessions_actual_min CHECK (actual_minutes >= 0),
    CONSTRAINT chk_study_sessions_status CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED')),
    CONSTRAINT chk_study_sessions_times CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT chk_study_sessions_status_ended CHECK (
        (status = 'IN_PROGRESS' AND ended_at IS NULL) OR
        (status != 'IN_PROGRESS' AND ended_at IS NOT NULL)
    )
);

-- -----------------------------------------------------------------------------
-- 18. BẢNG SESSION_TASKS (Bảng Trung gian Nhiều - Nhiều giữa Phiên học và Nhiệm vụ)
-- Bảo vệ lịch sử: ON DELETE RESTRICT trên task_id chặn xóa cứng nhiệm vụ đã học
-- -----------------------------------------------------------------------------
CREATE TABLE session_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    task_id UUID NOT NULL,
    allocated_minutes INTEGER NOT NULL DEFAULT 0,
    actual_minutes INTEGER NOT NULL DEFAULT 0,
    status_after_session VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_tasks_session_task UNIQUE (session_id, task_id),
    CONSTRAINT fk_session_tasks_session FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_session_tasks_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_session_tasks_allocated CHECK (allocated_minutes >= 0),
    CONSTRAINT chk_session_tasks_actual CHECK (actual_minutes >= 0),
    CONSTRAINT chk_session_tasks_status_after CHECK (status_after_session IN ('TODO', 'IN_PROGRESS', 'COMPLETED'))
);

-- -----------------------------------------------------------------------------
-- 19. BẢNG STUDY_NOTES (Ghi chép Học tập: Scratchpad, Takeaway, Tổng quát)
-- Mỗi phiên học có tối đa 1 bản nháp Scratchpad và 1 bản đúc kết Takeaway
-- -----------------------------------------------------------------------------
CREATE TABLE study_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_id UUID,
    task_id UUID,
    note_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_study_notes_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_study_notes_session FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_study_notes_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT chk_study_notes_type CHECK (note_type IN ('SCRATCHPAD', 'TAKEAWAY', 'GENERAL')),
    CONSTRAINT uq_study_notes_session_type UNIQUE (session_id, note_type)
);

-- =============================================================================
-- BOUNDED CONTEXT 4: EVALUATION (`evaluation` — 3 BẢNG)
-- Trách nhiệm: Quản lý lịch sử tạm dừng & tịnh tiến Domino Shift (pause_records),
--              tính toán chỉ số định lượng (QuantitativeMetrics), sinh báo cáo
--              AI Review theo chu kỳ SRL và lưu vết kiểm toán biến động lịch.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 20. BẢNG PAUSE_RECORDS (Lịch sử Tạm dừng Lộ trình & Tịnh tiến Domino Shift)
-- shifted_days khớp chính xác số ngày tạm dừng (pause_end_date - pause_start_date + 1)
-- -----------------------------------------------------------------------------
CREATE TABLE pause_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    pause_start_date DATE NOT NULL,
    pause_end_date DATE NOT NULL,
    shifted_days INTEGER NOT NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_pause_records_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_pause_records_dates CHECK (pause_end_date >= pause_start_date),
    CONSTRAINT chk_pause_records_shifted CHECK (shifted_days > 0),
    CONSTRAINT chk_pause_records_duration CHECK (shifted_days = (pause_end_date - pause_start_date + 1)),
    CONSTRAINT chk_pause_records_status CHECK (status IN ('ACTIVE', 'COMPLETED', 'CANCELLED'))
);

-- -----------------------------------------------------------------------------
-- 21. BẢNG AI_REVIEWS (Báo cáo Đánh giá Tiến độ & Khuyến nghị Thích ứng từ AI)
-- quantitative_summary JSONB lưu 5 chỉ số của QuantitativeMetrics + 3 trường nhận xét TEXT + model_used
-- -----------------------------------------------------------------------------
CREATE TABLE ai_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    user_id UUID NOT NULL,
    milestone_id UUID,
    review_cycle VARCHAR(20) NOT NULL,
    period_start DATE,
    period_end DATE,
    quantitative_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    strengths_feedback TEXT NOT NULL,
    bottlenecks_feedback TEXT NOT NULL,
    action_recommendations TEXT NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ai_reviews_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_ai_reviews_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_ai_reviews_milestone FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_reviews_cycle CHECK (review_cycle IN ('WEEKLY', 'MILESTONE')),
    CONSTRAINT chk_ai_reviews_quantitative_summary CHECK (jsonb_typeof(quantitative_summary) = 'object'),
    CONSTRAINT chk_ai_reviews_period_order CHECK (
        (review_cycle = 'MILESTONE' AND milestone_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR
        (review_cycle = 'WEEKLY' AND milestone_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)
    )
);

-- -----------------------------------------------------------------------------
-- 22. BẢNG SCHEDULE_CHANGE_LOGS (Nhật ký Kiểm toán Biến động Lịch học - NEW v3.0)
-- Lưu vết bất biến mọi đợt dời lịch (Domino Shift, sửa tay, AI Replan, Calendar Sync)
-- -----------------------------------------------------------------------------
CREATE TABLE schedule_change_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    schedule_id UUID,
    task_id UUID,
    trigger_type VARCHAR(30) NOT NULL,
    reason TEXT,
    affected_tasks_count INTEGER NOT NULL DEFAULT 1,
    total_shifted_minutes INTEGER NOT NULL DEFAULT 0,
    diff_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_sched_change_logs_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_sched_change_logs_schedule FOREIGN KEY (schedule_id) REFERENCES official_schedules(id) ON DELETE SET NULL,
    CONSTRAINT fk_sched_change_logs_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT chk_sched_change_logs_trigger CHECK (trigger_type IN (
        'DOMINO_SHIFT',
        'MANUAL_EDIT',
        'AI_REPLAN',
        'CALENDAR_SYNC'
    )),
    CONSTRAINT chk_sched_change_logs_affected CHECK (affected_tasks_count >= 0),
    CONSTRAINT chk_sched_change_logs_minutes CHECK (total_shifted_minutes >= 0),
    CONSTRAINT chk_sched_change_logs_payload CHECK (jsonb_typeof(diff_payload) = 'object')
);

-- =============================================================================
-- BOUNDED CONTEXT 5 / SHARED KERNEL (`shared_kernel` — 2 BẢNG)
-- Trách nhiệm: Đảm bảo phát sự kiện liên Bounded Context tin cậy (Transactional Outbox)
--              và tiêu thụ sự kiện bất biến (Idempotent Consumer) trên Taskiq Worker.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 23. BẢNG OUTBOX_EVENTS (Hàng đợi Sự kiện Giao dịch Liên Context - NEW v3.0)
-- Ghi cùng giao dịch ACID với Aggregate Root, tiếp vận sang Taskiq Redis Streams
-- -----------------------------------------------------------------------------
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    correlation_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    CONSTRAINT chk_outbox_events_status CHECK (status IN ('PENDING', 'PUBLISHED', 'FAILED')),
    CONSTRAINT chk_outbox_events_retry CHECK (retry_count >= 0),
    CONSTRAINT chk_outbox_events_payload CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT chk_outbox_events_published CHECK (
        (status = 'PUBLISHED' AND published_at IS NOT NULL) OR
        (status != 'PUBLISHED' AND published_at IS NULL)
    )
);

-- -----------------------------------------------------------------------------
-- 24. BẢNG PROCESSED_EVENTS (Sổ cái Chống Xử lý Trùng Sự kiện - NEW v3.0)
-- Khóa chính kép (event_id, handler_name) bảo đảm Idempotent Consumer cho Taskiq
-- -----------------------------------------------------------------------------
CREATE TABLE processed_events (
    event_id UUID NOT NULL,
    handler_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_processed_events PRIMARY KEY (event_id, handler_name),
    CONSTRAINT fk_processed_events_outbox FOREIGN KEY (event_id) REFERENCES outbox_events(id) ON DELETE CASCADE
);

-- =============================================================================
-- 6. TRIGGERS: TỰ ĐỘNG CẬP NHẬT UPDATED_AT CHO TẤT CẢ 18 BẢNG CÓ CỘT UPDATED_AT
-- =============================================================================
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_learner_profiles_updated_at BEFORE UPDATE ON learner_profiles FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_webcal_tokens_updated_at BEFORE UPDATE ON webcal_tokens FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_availabilities_updated_at BEFORE UPDATE ON availabilities FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_availability_slots_updated_at
    BEFORE UPDATE ON availability_slots
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_ai_quotas_updated_at BEFORE UPDATE ON ai_quotas FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_payment_transactions_updated_at BEFORE UPDATE ON payment_transactions FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_goals_updated_at BEFORE UPDATE ON goals FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_roadmaps_updated_at BEFORE UPDATE ON roadmaps FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_milestones_updated_at BEFORE UPDATE ON milestones FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_official_schedules_updated_at BEFORE UPDATE ON official_schedules FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_schedule_proposals_updated_at BEFORE UPDATE ON schedule_proposals FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_study_sessions_updated_at BEFORE UPDATE ON study_sessions FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_session_tasks_updated_at BEFORE UPDATE ON session_tasks FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_study_notes_updated_at BEFORE UPDATE ON study_notes FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_pause_records_updated_at BEFORE UPDATE ON pause_records FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_ai_reviews_updated_at BEFORE UPDATE ON ai_reviews FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =============================================================================
-- CHỈ MỤC HIỆU NĂNG & BẢO VỆ ĐỒNG THỜI (INDEXES & PARTIAL CONSTRAINTS)
-- =============================================================================

-- 1. BẢO VỆ TÍNH DUY NHẤT & BẤT BIẾN ĐỒNG THỜI
-- 1.1 Email duy nhất không phân biệt hoa thường
CREATE UNIQUE INDEX uq_users_lower_email ON users (LOWER(email));

-- 1.2 Mỗi người dùng tại một thời điểm chỉ có tối đa 1 phiên học đang chạy (IN_PROGRESS)
CREATE UNIQUE INDEX uq_study_sessions_user_active ON study_sessions(user_id) WHERE status = 'IN_PROGRESS';

-- 1.3 Mỗi lộ trình tại một thời điểm chỉ có tối đa 1 bản đề xuất lịch ở dạng nháp (DRAFT)
CREATE UNIQUE INDEX uq_schedule_proposals_roadmap_draft ON schedule_proposals(roadmap_id) WHERE status = 'DRAFT';

-- 1.4 Chống tạo trùng báo cáo đánh giá AI Review tuần (Idempotency cho Taskiq Retry)
CREATE UNIQUE INDEX uq_ai_reviews_weekly ON ai_reviews (roadmap_id, period_start, period_end) WHERE review_cycle = 'WEEKLY';

-- 1.5 Chống tạo trùng báo cáo đánh giá AI Review theo mốc kiến thức (Idempotency cho Taskiq Retry)
CREATE UNIQUE INDEX uq_ai_reviews_milestone ON ai_reviews (roadmap_id, milestone_id) WHERE review_cycle = 'MILESTONE';

-- 2. TỐI ƯU HÓA TRUY VẤN NÓNG (HOT QUERIES), QUOTA SWEEPER, OUTBOX RELAY & DASHBOARD
-- 2.1 Quét nhanh các bản ghi giữ chỗ Quota quá hạn (Taskiq QuotaSweeper mỗi 60s)
CREATE INDEX idx_quota_reservations_cleanup ON ai_quota_reservations(expires_at) WHERE status = 'RESERVED';
CREATE INDEX idx_quota_reservations_user_status ON ai_quota_reservations(user_id, status, created_at DESC);

-- 2.2 Truy vấn lịch sử giao dịch thanh toán của người dùng và đối soát trạng thái
CREATE INDEX idx_payment_transactions_user_created ON payment_transactions(user_id, created_at DESC);
CREATE INDEX idx_payment_transactions_status ON payment_transactions(status, created_at DESC);

-- 2.3 Lịch sử phiên học của người dùng sắp xếp giảm dần theo thời gian bắt đầu
CREATE INDEX idx_study_sessions_user_started ON study_sessions(user_id, started_at DESC);

-- 2.4 Lịch sử phiên học theo lộ trình
CREATE INDEX idx_study_sessions_roadmap_started ON study_sessions(roadmap_id, started_at DESC);

-- 2.5 Quét Heartbeat định kỳ phát hiện phiên học gián đoạn (Taskiq AbandonedSessionSweeper mỗi 60s)
CREATE INDEX idx_study_sessions_heartbeat ON study_sessions(last_heartbeat_at) WHERE status = 'IN_PROGRESS';

-- 2.6 Lộ trình theo người dùng và trạng thái hoạt động
CREATE INDEX idx_roadmaps_user_status ON roadmaps(user_id, status);

-- 2.7 Lộ trình theo mục tiêu
CREATE INDEX idx_roadmaps_goal_id ON roadmaps(goal_id);

-- 2.8 Truy vấn nhiệm vụ theo lộ trình và ngày lên lịch
CREATE INDEX idx_tasks_roadmap_scheduled_date ON tasks(roadmap_id, scheduled_date);

-- 2.9 Truy vấn nhiệm vụ theo mốc thời gian bắt đầu (phục vụ Calendar View)
CREATE INDEX idx_tasks_scheduled_start ON tasks(scheduled_start) WHERE scheduled_start IS NOT NULL;

-- 2.10 Phát hiện nhiệm vụ quá hạn (Deterministic Overdue Query)
CREATE INDEX idx_tasks_overdue ON tasks(scheduled_date) WHERE status IN ('TODO', 'IN_PROGRESS') AND scheduled_date IS NOT NULL;

-- 2.11 Nhiệm vụ theo mốc kiến thức và lịch chính thức
CREATE INDEX idx_tasks_milestone_id ON tasks(milestone_id);
CREATE INDEX idx_tasks_official_schedule_id ON tasks(official_schedule_id);

-- 2.12 Đồ thị phụ thuộc nhiệm vụ (DAG: tra cứu task trước và sau)
CREATE INDEX idx_task_deps_successor ON task_dependencies(successor_id);
CREATE INDEX idx_task_deps_predecessor ON task_dependencies(predecessor_id);
CREATE INDEX idx_task_deps_roadmap ON task_dependencies(roadmap_id);

-- 2.13 Tra cứu liên kết phiên học và nhiệm vụ
CREATE INDEX idx_session_tasks_task_id ON session_tasks(task_id);
CREATE INDEX idx_session_tasks_session_id ON session_tasks(session_id);

-- 2.14 Kiểm toán và thống kê lượng gọi AI của người dùng
CREATE INDEX idx_ai_usage_logs_user_action ON ai_usage_logs(user_id, action_type, created_at DESC);

-- 2.15 Khung giờ rảnh theo cấu hình tuần
CREATE INDEX idx_avail_slots_availability_day ON availability_slots(availability_id, day_of_week);

-- 2.16 Mục tiêu theo người dùng
CREATE INDEX idx_goals_user_id ON goals(user_id);

-- 2.17 Đề xuất lịch theo lộ trình và trạng thái
CREATE INDEX idx_schedule_proposals_roadmap_status ON schedule_proposals(roadmap_id, status);
CREATE INDEX idx_schedule_proposals_user_id ON schedule_proposals(user_id);

-- 2.18 Lịch sử tạm dừng lộ trình
CREATE INDEX idx_pause_records_roadmap_id ON pause_records(roadmap_id);

-- 2.19 Báo cáo AI theo lộ trình và chu kỳ
CREATE INDEX idx_ai_reviews_roadmap_cycle ON ai_reviews(roadmap_id, review_cycle, generated_at DESC);
CREATE INDEX idx_ai_reviews_user_id ON ai_reviews(user_id);

-- 2.20 Ghi chép học tập theo người dùng và phiên
CREATE INDEX idx_study_notes_user_session ON study_notes(user_id, session_id);
CREATE INDEX idx_study_notes_task_id ON study_notes(task_id);

-- 2.21 Nhật ký biến động lịch trình theo lộ trình và loại tác nhân
CREATE INDEX idx_sched_change_logs_roadmap_created ON schedule_change_logs(roadmap_id, created_at DESC);
CREATE INDEX idx_sched_change_logs_trigger ON schedule_change_logs(trigger_type, created_at DESC);

-- 2.22 Quét nhanh sự kiện Outbox đang chờ phát (Taskiq OutboxRelayTask)
CREATE INDEX idx_outbox_events_pending ON outbox_events(created_at ASC) WHERE status = 'PENDING';
CREATE INDEX idx_outbox_events_aggregate ON outbox_events(aggregate_type, aggregate_id);

-- 2.23 Chỉ mục Cơ sở Tri thức Học thuật (Knowledge Base)
CREATE INDEX idx_learning_concepts_domain_level ON learning_concepts(domain, difficulty_level, verification_status);
CREATE INDEX idx_concept_prerequisites_source ON concept_prerequisites(source_concept_id);
CREATE INDEX idx_concept_prerequisites_prereq ON concept_prerequisites(prerequisite_concept_id);
