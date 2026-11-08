-- =============================================================================
-- FocusFlow Relational Database Schema DDL v3.2 (PostgreSQL 16 + pgvector)
-- Kiến trúc: Context-First Modular Monolith + FocusFlow Learning Intelligence Harness
--            (4 Bounded Contexts + Shared Kernel)
-- Tổng số bảng vật lý: 35 Bảng chuẩn hóa 3NF/BCNF kết hợp Controlled JSONB Value Objects có ràng buộc CHECK nghiêm ngặt
--                      (12 account, 10 planning, 5 execution, 4 evaluation, 4 shared_kernel)
-- Tiêu chuẩn: ISO/IEC 9075:2023 SQL, Defense-in-Depth Constraints, ACID Outbox
-- Chiến lược Khóa chính: UUIDv7 sinh tại Backend (FastAPI - RFC 9562), fallback DB
-- Quy tắc Modular Monolith: Giữ FK vật lý ở tầng DB để bảo toàn toàn vẹn tham chiếu,
--                           nhưng cấm ORM JOIN chéo Context trong code (giao tiếp qua
--                           public_api.py và Transactional Outbox outbox_events).
-- Quản lý Thời gian: TIMESTAMPTZ (UTC) cho toàn bộ mốc thời gian; cột timezone trong users
-- =============================================================================

-- =============================================================================
-- KÍCH HOẠT EXTENSION PGVECTOR (HYBRID RAG: TSVECTOR GIN + PGVECTOR HNSW)
-- PostgreSQL 16 (pgvector) cung cấp khả năng truy xuất ngữ nghĩa (semantic chunk
-- retrieval) kết hợp cùng tìm kiếm toàn văn bản native (tsvector GIN) ngay trong
-- cùng cụm CSDL quan hệ mà không cần triển khai thêm container Vector DB riêng biệt.
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- 0. HÀM TRIGGER DÙNG CHUNG CẬP NHẬT UPDATED_AT (26 BẢNG CÓ CỘT UPDATED_AT)
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- BOUNDED CONTEXT 1: ACCOUNT (`account` — 12 BẢNG)
-- Trách nhiệm: Quản lý định danh, xác thực, hồ sơ năng lực SRL, trí nhớ người học
--              cấu trúc hóa (4 Categories × 3 Epistemic Levels), mức độ thành thạo
--              khái niệm (Skill Mastery), cấu hình lịch rảnh Mode A/B, kết nối lịch
--              OAuth 2 chiều, hạn ngạch AI 2 pha và thanh toán.
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
    premium_expires_at TIMESTAMPTZ NULL,
    last_login_at TIMESTAMPTZ NULL,
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
-- 3. BẢNG WEBCAL_TOKENS (Token Đồng bộ Lịch Ngoài 1 Chiều iCal/WebCal Feed)
-- Lưu SHA-256 digest của 32-byte hex CSPRN cho URL đăng ký iCal riêng tư (.ics)
-- -----------------------------------------------------------------------------
CREATE TABLE webcal_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
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
-- 4. BẢNG CALENDAR_CONNECTIONS (Kết nối Lịch Ngoại vi 2 Chiều OAuth - Chuẩn hóa 3NF/BCNF)
-- Tách biệt hoàn toàn khỏi WebCal 1 chiều (.ics), quản lý refresh token mã hóa Fernet (SRS §12)
-- -----------------------------------------------------------------------------
CREATE TABLE calendar_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    provider VARCHAR(30) NOT NULL DEFAULT 'GOOGLE',
    external_calendar_id VARCHAR(255) NOT NULL DEFAULT 'primary',
    oauth_refresh_token_encrypted TEXT NOT NULL,
    sync_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    last_synced_at TIMESTAMPTZ,
    error_detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_calendar_connections_user_provider UNIQUE (user_id, provider),
    CONSTRAINT fk_calendar_connections_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_calendar_connections_provider CHECK (provider IN ('GOOGLE', 'OUTLOOK', 'LOCAL_MOCK')),
    CONSTRAINT chk_calendar_connections_status CHECK (sync_status IN ('ACTIVE', 'REVOKED', 'ERROR'))
);

-- -----------------------------------------------------------------------------
-- 5. BẢNG AVAILABILITIES (Cấu hình Quỹ Thời gian Rảnh Tổng thể)
-- Mỗi người dùng có 1 bản ghi cấu hình chế độ rảnh (Mode A quỹ giờ / Mode B khung giờ)
-- Hàm kiểm định miền giá trị Controlled JSONB Value Object cho daily_quotas:
--   (1) jsonb_typeof(p_quotas) = 'object'
--   (2) Mọi key thuộc ('MON'..'SUN', 'MONDAY'..'SUNDAY')
--   (3) Mọi value là kiểu number và nằm trong miền [0.5, 14.0] giờ/ngày
--   (4) Khi mode = 'MODE_A', bắt buộc có ít nhất 1 ngày được cấu hình (p_quotas <> '{}'::jsonb)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_validate_daily_quotas(p_quotas JSONB, p_mode VARCHAR)
RETURNS BOOLEAN
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT
        p_quotas IS NOT NULL
        AND jsonb_typeof(p_quotas) = 'object'
        AND (p_mode <> 'MODE_A' OR p_quotas <> '{}'::jsonb)
        AND NOT EXISTS (
            SELECT 1
            FROM jsonb_each(p_quotas) AS e(key, value)
            WHERE e.key NOT IN (
                'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN',
                'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'
            )
            OR jsonb_typeof(e.value) <> 'number'
            OR (
                CASE
                    WHEN jsonb_typeof(e.value) = 'number'
                    THEN ((e.value::text)::numeric NOT BETWEEN 0.5 AND 14.0)
                    ELSE TRUE
                END
            )
        );
$$;

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
    CONSTRAINT chk_availabilities_quotas_json CHECK (fn_validate_daily_quotas(daily_quotas, mode)),
    CONSTRAINT chk_availabilities_min_session CHECK (min_session_minutes BETWEEN 15 AND 120)
);

-- -----------------------------------------------------------------------------
-- 6. BẢNG AVAILABILITY_SLOTS (Khung Giờ Rảnh Chi tiết - Chuẩn hóa 100% 3NF)
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
    energy_level VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_avail_slots_availability FOREIGN KEY (availability_id) REFERENCES availabilities(id) ON DELETE CASCADE,
    CONSTRAINT chk_avail_slots_day CHECK (day_of_week BETWEEN 0 AND 6),
    CONSTRAINT chk_avail_slots_offset CHECK (end_day_offset IN (0, 1)),
    CONSTRAINT chk_avail_slots_type CHECK (slot_type IN ('ALLOWED', 'FIXED')),
    CONSTRAINT chk_avail_slots_energy CHECK (energy_level IN ('LOW', 'MEDIUM', 'HIGH')),
    CONSTRAINT chk_avail_slots_time CHECK (end_day_offset = 1 OR end_time > start_time)
);

-- -----------------------------------------------------------------------------
-- 7. BẢNG AI_QUOTAS (Hạn ngạch AI Chu kỳ Hiện tại - 2-Phase ACID Quota Guard)
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
-- 8. BẢNG AI_QUOTA_RESERVATIONS (Sổ cái Giữ chỗ Hạn ngạch AI 2 Pha - NEW v3.0)
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
-- 9. BẢNG AI_USAGE_LOGS (Nhật ký Kiểm toán Gọi Dịch vụ AI Chi tiết)
-- Ghi nhận lịch sử kiểm toán đa nhà cung cấp (Provider-Agnostic LLMPort)
-- -----------------------------------------------------------------------------
CREATE TABLE ai_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    reservation_id UUID NULL REFERENCES ai_quota_reservations(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL DEFAULT 'gemini-2.5-flash',
    attempt_no SMALLINT NOT NULL DEFAULT 1 CHECK (attempt_no BETWEEN 1 AND 5),
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.000000 CHECK (estimated_cost_usd >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ai_usage_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_usage_logs_action CHECK (action_type IN (
        'ROADMAP_GENERATION',
        'MILESTONE_BREAKDOWN',
        'SCHEDULE_PROPOSAL',
        'AI_RESCHEDULE',
        'TASK_MICRO_STEPPING',
        'MILESTONE_PROVE_CHECK',
        'AI_REVIEW_WEEKLY',
        'AI_REVIEW_MILESTONE',
        'CHAT_ASSISTANT',
        'KNOWLEDGE_INGESTION',
        'WHAT_IF_SIMULATION'
    )),
    CONSTRAINT chk_ai_usage_logs_tokens CHECK (prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0),
    CONSTRAINT chk_ai_usage_logs_latency CHECK (latency_ms >= 0),
    CONSTRAINT chk_ai_usage_logs_status CHECK (status IN ('SUCCESS', 'FAILED', 'RATE_LIMITED', 'TIMEOUT'))
);

-- -----------------------------------------------------------------------------
-- 10. BẢNG PAYMENT_TRANSACTIONS (Giao dịch Thanh toán Nâng cấp Gói - NEW v3.0)
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
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payment_transactions_ref UNIQUE (transaction_ref),
    CONSTRAINT fk_payment_transactions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_payment_transactions_provider CHECK (gateway_provider IN ('PAYOS', 'VNPAY', 'MOCK')),
    CONSTRAINT chk_payment_transactions_amount CHECK (amount_vnd > 0),
    CONSTRAINT chk_payment_transactions_status CHECK (status IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED')),
    CONSTRAINT chk_payment_transactions_paid_at CHECK (
        (status = 'PAID' AND paid_at IS NOT NULL) OR
        (status != 'PAID' AND paid_at IS NULL)
    )
);

-- -----------------------------------------------------------------------------
-- 11. BẢNG LEARNER_MEMORY_ITEMS (Trí nhớ Người học Cấu trúc hóa - NEW v3.2)
-- Phân tầng 4 Danh mục (PROFILE, BEHAVIORAL, KNOWLEDGE, INTERACTION) × 3 Mức nhận thức
-- (EXPLICIT, OBSERVED, INFERRED) kèm độ tin cậy, kích thước mẫu và xác nhận của người học
-- -----------------------------------------------------------------------------
CREATE TABLE learner_memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    memory_category VARCHAR(30) NOT NULL,
    epistemic_type VARCHAR(20) NOT NULL,
    memory_key VARCHAR(120) NOT NULL,
    claim_value JSONB NOT NULL,
    source_evidence TEXT NOT NULL DEFAULT '',
    sample_size INTEGER NOT NULL DEFAULT 1,
    observation_window_days INTEGER NULL,
    confidence_score NUMERIC(4, 3) NOT NULL DEFAULT 1.000,
    confirmation_status VARCHAR(25) NOT NULL DEFAULT 'UNCONFIRMED',
    confirmed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_learner_memory_items_user_cat_key UNIQUE (user_id, memory_category, memory_key),
    CONSTRAINT fk_learner_memory_items_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_learner_memory_items_category CHECK (
        memory_category IN ('PROFILE', 'BEHAVIORAL', 'KNOWLEDGE', 'INTERACTION')
    ),
    CONSTRAINT chk_learner_memory_items_epistemic CHECK (
        epistemic_type IN ('EXPLICIT', 'OBSERVED', 'INFERRED')
    ),
    CONSTRAINT chk_learner_memory_items_claim_json CHECK (jsonb_typeof(claim_value) = 'object'),
    CONSTRAINT chk_learner_memory_items_sample_size CHECK (sample_size >= 0),
    CONSTRAINT chk_learner_memory_items_window CHECK (
        observation_window_days IS NULL OR observation_window_days >= 0
    ),
    CONSTRAINT chk_learner_memory_items_confidence CHECK (
        confidence_score BETWEEN 0.000 AND 1.000
    ),
    CONSTRAINT chk_learner_memory_items_confirmation CHECK (
        confirmation_status IN ('UNCONFIRMED', 'CONFIRMED', 'REJECTED', 'EDITED')
    )
);

-- -----------------------------------------------------------------------------
-- 12. BẢNG LEARNER_CONCEPT_MASTERIES (Theo dõi Thành thạo Khái niệm & Ôn tập Thông minh - NEW v3.2)
-- Lưu vết điểm thành thạo (0..100), cấp độ năng lực, mẫu lỗi sai và lịch ôn tập tiếp theo
-- -----------------------------------------------------------------------------
CREATE TABLE learner_concept_masteries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    concept_id VARCHAR(120) NOT NULL,
    mastery_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    mastery_level VARCHAR(20) NOT NULL DEFAULT 'NOVICE',
    evidence_count INTEGER NOT NULL DEFAULT 0,
    mistake_pattern_summary JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_practiced_at TIMESTAMPTZ NULL,
    next_review_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_learner_concept_masteries_user_concept UNIQUE (user_id, concept_id),
    CONSTRAINT fk_learner_mastery_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_learner_mastery_score CHECK (mastery_score BETWEEN 0.00 AND 100.00),
    CONSTRAINT chk_learner_mastery_level CHECK (
        mastery_level IN ('NOVICE', 'DEVELOPING', 'PROFICIENT', 'MASTERED')
    ),
    CONSTRAINT chk_learner_mastery_evidence CHECK (evidence_count >= 0),
    CONSTRAINT chk_learner_mastery_mistakes_json CHECK (jsonb_typeof(mistake_pattern_summary) = 'array')
);

-- =============================================================================
-- BOUNDED CONTEXT 2: PLANNING (`planning` — 10 BẢNG)
-- Trách nhiệm: Quản lý mục tiêu, lộ trình, cột mốc, lịch học chính thức (Frozen Baseline
--              kèm Resilience Policy), đề xuất lịch xem trước (What-If Simulation),
--              cơ sở tri thức, Knowledge Engine (RAG Ingestion & Hybrid Retrieval)
--              và các khối lịch học chi tiết (schedule_blocks).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 13. BẢNG GOALS (Mục tiêu Học tập)
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
    CONSTRAINT chk_goals_status CHECK (status IN ('DRAFT', 'CLARIFIED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ABANDONED'))
);

-- -----------------------------------------------------------------------------
-- 14. BẢNG ROADMAPS (Lộ trình Tự học Thích ứng)
-- Bản thiết kế học tập chia nhỏ từ mục tiêu, quản lý trạng thái, budget dời lịch & dormant
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
    weekly_reschedule_budget SMALLINT NOT NULL DEFAULT 3,
    weekly_reschedule_used SMALLINT NOT NULL DEFAULT 0,
    budget_week_start DATE NOT NULL DEFAULT CURRENT_DATE,
    last_study_activity_at TIMESTAMPTZ,
    reset_ritual_count SMALLINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_roadmaps_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_roadmaps_goal FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    CONSTRAINT uq_roadmaps_goal UNIQUE (goal_id),
    CONSTRAINT chk_roadmaps_status CHECK (status IN ('INITIALIZED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')),
    CONSTRAINT chk_roadmaps_dates CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date),
    CONSTRAINT chk_roadmaps_weekly_budget CHECK (weekly_reschedule_budget BETWEEN 1 AND 10),
    CONSTRAINT chk_roadmaps_weekly_used CHECK (weekly_reschedule_used >= 0),
    CONSTRAINT chk_roadmaps_reset_count CHECK (reset_ritual_count >= 0)
);

-- -----------------------------------------------------------------------------
-- 15. BẢNG MILESTONES (Các Mốc Kiến thức Tuần tự Cấp 1)
-- Thứ tự sequence_order là duy nhất trong cùng Roadmap, hỗ trợ trạng thái kiểm chứng Prove
-- -----------------------------------------------------------------------------
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    sequence_order INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    proof_status VARCHAR(20) NOT NULL DEFAULT 'UNVERIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_milestones_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT uq_milestones_roadmap_seq UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT chk_milestones_seq CHECK (sequence_order >= 1),
    CONSTRAINT chk_milestones_status CHECK (status IN ('PENDING', 'APPROVED', 'IN_PROGRESS', 'COMPLETED')),
    CONSTRAINT chk_milestones_proof_status CHECK (
        proof_status IN ('UNVERIFIED', 'PENDING_REVIEW', 'PROVEN', 'NEEDS_REVIEW')
    )
);

-- -----------------------------------------------------------------------------
-- 16. BẢNG OFFICIAL_SCHEDULES (Lịch trình Học tập Chính thức - Frozen Baseline & Resilience Policy)
-- Đóng băng chỉ số kế hoạch cơ sở cho KPI 3 và lưu chính sách chống đứt gãy (Buffer, Cap, Stability)
-- -----------------------------------------------------------------------------
CREATE TABLE official_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1 CHECK (version_number >= 1),
    strategy VARCHAR(20) NOT NULL DEFAULT 'MERGE_EXISTING' CHECK (strategy IN ('MERGE_EXISTING', 'REPLACE_ALL')),
    total_sessions INTEGER NOT NULL DEFAULT 0,
    total_planned_minutes INTEGER NOT NULL DEFAULT 0,
    buffer_minutes_per_week INTEGER NOT NULL DEFAULT 60,
    recovery_window_days SMALLINT NOT NULL DEFAULT 7,
    daily_workload_cap_minutes INTEGER NOT NULL DEFAULT 180,
    stability_weight NUMERIC(3, 2) NOT NULL DEFAULT 0.80,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_official_schedules_roadmap UNIQUE (roadmap_id),
    CONSTRAINT fk_official_schedules_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_official_schedules_sessions CHECK (total_sessions >= 0),
    CONSTRAINT chk_official_schedules_minutes CHECK (total_planned_minutes >= 0),
    CONSTRAINT chk_official_schedules_buffer CHECK (buffer_minutes_per_week >= 0),
    CONSTRAINT chk_official_schedules_recovery_window CHECK (recovery_window_days BETWEEN 1 AND 30),
    CONSTRAINT chk_official_schedules_daily_cap CHECK (daily_workload_cap_minutes BETWEEN 15 AND 720),
    CONSTRAINT chk_official_schedules_stability_weight CHECK (stability_weight BETWEEN 0.00 AND 1.00)
);

-- -----------------------------------------------------------------------------
-- 17. BẢNG SCHEDULE_PROPOSALS (Bản Đề xuất Lịch Xem trước & What-If Simulation)
-- Chứa proposal_data JSONB xem trước, hỗ trợ đo KPI AI Proposal Edit Rate và Snapshot gốc
-- -----------------------------------------------------------------------------
CREATE TABLE schedule_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    user_id UUID NOT NULL,
    proposal_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    proposal_type VARCHAR(30) NOT NULL DEFAULT 'INITIAL_SCHEDULE',
    original_proposal_data JSONB,
    user_edit_count INTEGER NOT NULL DEFAULT 0,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_schedule_proposals_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_schedule_proposals_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_schedule_proposals_status CHECK (status IN ('DRAFT', 'APPLIED', 'DISCARDED')),
    CONSTRAINT chk_schedule_proposals_data CHECK (jsonb_typeof(proposal_data) = 'object'),
    CONSTRAINT chk_schedule_proposals_type CHECK (
        proposal_type IN (
            'INITIAL_SCHEDULE',
            'AI_RECOVERY',
            'POST_FAILURE_RESET',
            'WHAT_IF_SIMULATION',
            'SCHEDULE_ONLY_REOPTIMIZE'
        )
    ),
    CONSTRAINT chk_schedule_proposals_edits CHECK (user_edit_count >= 0)
);

-- -----------------------------------------------------------------------------
-- 18. BẢNG LEARNING_CONCEPTS (Cơ sở Tri thức Học thuật Đã Xác thực - Knowledge Base)
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

-- Bổ sung khóa ngoại từ learner_concept_masteries (account BC) sang learning_concepts (planning BC)
ALTER TABLE learner_concept_masteries
    ADD CONSTRAINT fk_learner_mastery_concept
    FOREIGN KEY (concept_id) REFERENCES learning_concepts(concept_id) ON DELETE CASCADE;

-- -----------------------------------------------------------------------------
-- 19. BẢNG CONCEPT_PREREQUISITES (Quan hệ Tiên quyết Giữa các Khái niệm Tri thức)
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- 20. BẢNG KNOWLEDGE_SOURCES (Nguồn Tài liệu Học tập Đầu vào - Knowledge Engine - NEW v3.2)
-- Quản lý tài liệu PDF/DOCX/TXT và URL người học cung cấp, kiểm soát SSRF & Provenance
-- -----------------------------------------------------------------------------
CREATE TABLE knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    goal_id UUID NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_uri TEXT NULL,
    content_hash VARCHAR(64) NOT NULL,
    ingestion_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    provenance_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_detail TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_knowledge_sources_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_sources_goal FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    CONSTRAINT chk_knowledge_sources_type CHECK (source_type IN ('PDF', 'DOCX', 'TXT', 'URL')),
    CONSTRAINT chk_knowledge_sources_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_knowledge_sources_status CHECK (
        ingestion_status IN ('PENDING', 'PROCESSING', 'INDEXED', 'FAILED', 'QUARANTINED')
    ),
    CONSTRAINT chk_knowledge_sources_chunks CHECK (chunk_count >= 0),
    CONSTRAINT chk_knowledge_sources_provenance CHECK (jsonb_typeof(provenance_metadata) = 'object')
);

-- -----------------------------------------------------------------------------
-- 21. BẢNG KNOWLEDGE_CHUNKS (Phân đoạn Tri thức RAG - Hybrid TSVECTOR + PGVECTOR - NEW v3.2)
-- Lưu từng phân đoạn văn bản, chỉ mục tìm kiếm từ khóa (tsvector) và vector ngữ nghĩa 768 chiều
-- -----------------------------------------------------------------------------
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL,
    goal_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    section_title VARCHAR(255) NULL,
    page_number INTEGER NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    search_vector TSVECTOR NULL,
    embedding vector(768) NULL,
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_knowledge_chunks_source_idx UNIQUE (source_id, chunk_index),
    CONSTRAINT fk_knowledge_chunks_source FOREIGN KEY (source_id) REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_chunks_goal FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    CONSTRAINT chk_knowledge_chunks_index CHECK (chunk_index >= 0),
    CONSTRAINT chk_knowledge_chunks_page CHECK (page_number IS NULL OR page_number >= 1),
    CONSTRAINT chk_knowledge_chunks_tokens CHECK (token_count > 0),
    CONSTRAINT chk_knowledge_chunks_provenance CHECK (jsonb_typeof(provenance_json) = 'object')
);

-- -----------------------------------------------------------------------------
-- 22. BẢNG SCHEDULE_BLOCKS (Khối Lịch Học Thực thi & Ánh xạ Sự kiện Lịch Ngoại vi - NEW v3.2)
-- Tách biệt hoàn toàn khối lượng ước tính của Task (tasks.estimated_minutes) với thời lượng
-- phân bổ trên từng khung lịch (scheduled_duration_minutes), hỗ trợ Buffer/Revision/Recovery
-- và lưu external_calendar_event_id để đồng bộ Google/Outlook Calendar 2 chiều chuẩn 3NF
-- -----------------------------------------------------------------------------
CREATE TABLE schedule_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    official_schedule_id UUID NOT NULL,
    task_id UUID NULL,
    sequence_in_task SMALLINT NOT NULL DEFAULT 1,
    block_type VARCHAR(20) NOT NULL DEFAULT 'STUDY',
    block_date DATE NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    scheduled_duration_minutes INTEGER NOT NULL,
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'PLANNED',
    external_calendar_event_id VARCHAR(255) NULL,
    placement_rationale TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_schedule_blocks_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_schedule_blocks_schedule FOREIGN KEY (official_schedule_id) REFERENCES official_schedules(id) ON DELETE CASCADE,
    CONSTRAINT chk_schedule_blocks_seq CHECK (sequence_in_task >= 1),
    CONSTRAINT chk_schedule_blocks_type CHECK (block_type IN ('STUDY', 'BUFFER', 'REVISION', 'RECOVERY')),
    CONSTRAINT chk_schedule_blocks_duration CHECK (scheduled_duration_minutes BETWEEN 10 AND 240),
    CONSTRAINT chk_schedule_blocks_status CHECK (
        status IN ('PLANNED', 'COMPLETED', 'MISSED', 'RESCHEDULED', 'CANCELLED')
    ),
    CONSTRAINT chk_schedule_blocks_time_order CHECK (end_time > start_time)
);

-- =============================================================================
-- BOUNDED CONTEXT 3: EXECUTION (`execution` — 5 BẢNG)
-- Trách nhiệm: Quản lý nhiệm vụ học tập chi tiết (tasks kèm trích dẫn nguồn RAG),
--              đồ thị tiên quyết DAG (task_dependencies), vận hành không gian học tập
--              Pomodoro/Stopwatch kèm Daily Check-in, Heartbeat 60s và ghi chú.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 23. BẢNG TASKS (Nhiệm vụ Học tập Chi tiết Cấp 2)
-- Lưu ý: estimated_minutes đại diện cho nỗ lực ước tính bởi AI (estimated_effort),
-- trong khi schedule_blocks.scheduled_duration_minutes đại diện cho thời lượng phân bổ lịch.
-- Cột learning_resources_json lưu danh sách trích dẫn nguồn từ Knowledge Engine.
-- -----------------------------------------------------------------------------
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    milestone_id UUID NOT NULL,
    official_schedule_id UUID,
    parent_task_id UUID,
    concept_id VARCHAR(120),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    estimated_minutes INTEGER NOT NULL,
    learning_resources_json JSONB NOT NULL DEFAULT '[]'::jsonb,
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
    CONSTRAINT fk_tasks_parent_task FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT fk_tasks_concept FOREIGN KEY (concept_id) REFERENCES learning_concepts(concept_id) ON DELETE SET NULL,
    CONSTRAINT chk_tasks_estimated_minutes CHECK (estimated_minutes BETWEEN 15 AND 240),
    CONSTRAINT chk_tasks_learning_resources_json CHECK (jsonb_typeof(learning_resources_json) = 'array'),
    CONSTRAINT chk_tasks_status CHECK (status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    CONSTRAINT chk_tasks_reschedule_count CHECK (reschedule_count >= 0),
    CONSTRAINT chk_tasks_no_self_parent CHECK (parent_task_id IS NULL OR parent_task_id <> id),
    CONSTRAINT chk_tasks_scheduled_time_order CHECK (
        (scheduled_start IS NULL AND scheduled_end IS NULL)
        OR (scheduled_start IS NOT NULL AND scheduled_end IS NOT NULL AND scheduled_end > scheduled_start)
    ),
    CONSTRAINT chk_tasks_completed_at CHECK (
        (status = 'COMPLETED' AND completed_at IS NOT NULL) OR
        (status != 'COMPLETED' AND completed_at IS NULL)
    )
);

-- Bổ sung khóa ngoại từ schedule_blocks (planning BC) sang tasks (execution BC)
ALTER TABLE schedule_blocks
    ADD CONSTRAINT fk_schedule_blocks_task
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;

-- -----------------------------------------------------------------------------
-- 24. BẢNG TASK_DEPENDENCIES (Quan hệ Tiên quyết Giữa các Nhiệm vụ - DAG)
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
-- 25. BẢNG STUDY_SESSIONS (Phiên Thực thi Học tập Pomodoro / Stopwatch / MVS & Daily Check-in)
-- Hỗ trợ Minimum Viable Session (10-15p), tín hiệu Heartbeat 60s, nợ Takeaway và 3 câu hỏi
-- khảo sát nhanh cuối phiên (Daily Learning Check-in: thời lượng, độ khó, mức tập trung)
-- -----------------------------------------------------------------------------
CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    roadmap_id UUID NOT NULL,
    session_mode VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    timer_mode VARCHAR(20) NOT NULL DEFAULT 'POMODORO' CHECK (timer_mode IN ('POMODORO', 'STOPWATCH')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    planned_minutes INTEGER NOT NULL,
    actual_minutes INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
    pending_takeaway BOOLEAN NOT NULL DEFAULT FALSE,
    checkin_time_sufficiency VARCHAR(20) NULL,
    checkin_perceived_difficulty VARCHAR(20) NULL,
    checkin_focus_level SMALLINT NULL,
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_study_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_study_sessions_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_study_sessions_mode CHECK (session_mode IN ('STANDARD', 'MVS')),
    CONSTRAINT chk_study_sessions_planned_min CHECK (planned_minutes > 0),
    CONSTRAINT chk_study_sessions_actual_min CHECK (actual_minutes >= 0),
    CONSTRAINT chk_study_sessions_status CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED')),
    CONSTRAINT chk_study_sessions_times CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT chk_study_sessions_status_ended CHECK (
        (status = 'IN_PROGRESS' AND ended_at IS NULL) OR
        (status != 'IN_PROGRESS' AND ended_at IS NOT NULL)
    ),
    CONSTRAINT chk_study_sessions_checkin_time CHECK (
        checkin_time_sufficiency IS NULL OR checkin_time_sufficiency IN ('ENOUGH', 'TIGHT', 'INSUFFICIENT')
    ),
    CONSTRAINT chk_study_sessions_checkin_diff CHECK (
        checkin_perceived_difficulty IS NULL OR checkin_perceived_difficulty IN ('EASY', 'AS_EXPECTED', 'HARDER')
    ),
    CONSTRAINT chk_study_sessions_checkin_focus CHECK (
        checkin_focus_level IS NULL OR (checkin_focus_level BETWEEN 1 AND 5)
    )
);

-- -----------------------------------------------------------------------------
-- 26. BẢNG SESSION_TASKS (Bảng Trung gian Nhiều - Nhiều giữa Phiên học và Nhiệm vụ)
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
-- 27. BẢNG STUDY_NOTES (Ghi chép Học tập: Scratchpad, Takeaway, Tổng quát)
-- Tích hợp Confidence Calibration, AI Evidence Score & Anti-Fake Takeaway Verification
-- -----------------------------------------------------------------------------
CREATE TABLE study_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_id UUID,
    task_id UUID,
    note_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    self_confidence SMALLINT,
    ai_evidence_score NUMERIC(3, 2),
    alignment_flag VARCHAR(25) NOT NULL DEFAULT 'UNCHECKED',
    verification_status VARCHAR(25) NOT NULL DEFAULT 'PENDING_PROVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_study_notes_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_study_notes_session FOREIGN KEY (session_id) REFERENCES study_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_study_notes_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT chk_study_notes_context_anchor CHECK (session_id IS NOT NULL OR task_id IS NOT NULL),
    CONSTRAINT chk_study_notes_type CHECK (note_type IN ('SCRATCHPAD', 'TAKEAWAY', 'GENERAL')),
    CONSTRAINT chk_study_notes_confidence CHECK (
        self_confidence IS NULL OR (self_confidence BETWEEN 1 AND 5)
    ),
    CONSTRAINT chk_study_notes_evidence_score CHECK (
        ai_evidence_score IS NULL OR (ai_evidence_score BETWEEN 1.00 AND 5.00)
    ),
    CONSTRAINT chk_study_notes_alignment CHECK (
        alignment_flag IN ('UNCHECKED', 'ALIGNED', 'SUPERFICIAL', 'OFF_TOPIC', 'CONTRADICTORY')
    ),
    CONSTRAINT chk_study_notes_verification CHECK (
        verification_status IN ('PENDING_PROVE', 'VERIFIED', 'FLAGGED_SHALLOW', 'NEEDS_REVIEW')
    ),
    CONSTRAINT chk_study_notes_takeaway_min_length CHECK (
        note_type <> 'TAKEAWAY' OR char_length(btrim(content)) >= 30
    )
);

-- =============================================================================
-- BOUNDED CONTEXT 4: EVALUATION (`evaluation` — 4 BẢNG)
-- Trách nhiệm: Quản lý lịch sử tạm dừng & tịnh tiến Domino Shift (pause_records),
--              tính toán chỉ số định lượng (QuantitativeMetrics), sinh báo cáo
--              AI Review kèm phản tư tuần (Weekly Reflection), nhật ký biến động lịch
--              và kiểm chứng Prove Mode tích hợp Mistake Intelligence.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 28. BẢNG PAUSE_RECORDS (Lịch sử Tạm dừng Lộ trình & Tịnh tiến Domino Shift)
-- shifted_days khớp chính xác số ngày tạm dừng (pause_end_date - pause_start_date; NULL khi ACTIVE)
-- -----------------------------------------------------------------------------
CREATE TABLE pause_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id UUID NOT NULL,
    pause_start_date DATE NOT NULL,
    pause_end_date DATE NULL,
    shifted_days INTEGER NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_pause_records_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_pause_records_status CHECK (status IN ('ACTIVE', 'COMPLETED')),
    CONSTRAINT chk_pause_records_lifecycle CHECK (
        (status = 'ACTIVE' AND pause_end_date IS NULL AND shifted_days IS NULL) OR
        (status = 'COMPLETED' AND pause_end_date IS NOT NULL AND shifted_days IS NOT NULL AND shifted_days = (pause_end_date - pause_start_date) AND shifted_days >= 0)
    )
);

-- -----------------------------------------------------------------------------
-- 29. BẢNG AI_REVIEWS (Báo cáo Đánh giá Tiến độ, Phản tư Tuần & Khuyến nghị Thích ứng)
-- quantitative_summary JSONB lưu QuantitativeMetrics; user_reflection_payload lưu 2-3 câu
-- hỏi & trả lời phản tư chủ quan của người học (Weekly Reflection); model_used mặc định gemini-2.5-flash
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
    user_reflection_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    strengths_feedback TEXT NOT NULL,
    bottlenecks_feedback TEXT NOT NULL,
    action_recommendations TEXT NOT NULL,
    model_used VARCHAR(100) NOT NULL DEFAULT 'gemini-2.5-flash',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ai_reviews_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_ai_reviews_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_ai_reviews_milestone FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
    CONSTRAINT chk_ai_reviews_cycle CHECK (review_cycle IN ('WEEKLY', 'MILESTONE')),
    CONSTRAINT chk_ai_reviews_quantitative_summary CHECK (jsonb_typeof(quantitative_summary) = 'object'),
    CONSTRAINT chk_ai_reviews_user_reflection CHECK (jsonb_typeof(user_reflection_payload) = 'object'),
    CONSTRAINT chk_ai_reviews_period_order CHECK (
        (review_cycle = 'MILESTONE' AND milestone_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR
        (review_cycle = 'WEEKLY' AND milestone_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)
    )
);

-- -----------------------------------------------------------------------------
-- 30. BẢNG SCHEDULE_CHANGE_LOGS (Nhật ký Kiểm toán Biến động Lịch học - NEW v3.0)
-- Lưu vết bất biến mọi đợt dời lịch, phân loại gián đoạn chính đáng vs trì hoãn
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
    disruption_category VARCHAR(30) NOT NULL DEFAULT 'UNSPECIFIED',
    counts_toward_budget BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_sched_change_logs_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_sched_change_logs_schedule FOREIGN KEY (schedule_id) REFERENCES official_schedules(id) ON DELETE SET NULL,
    CONSTRAINT fk_sched_change_logs_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT chk_sched_change_logs_trigger CHECK (trigger_type IN (
        'DOMINO_SHIFT',
        'MANUAL_PROACTIVE_EDIT',
        'OVERDUE_RESCHEDULE',
        'AI_REPLAN',
        'STALLED_COMMITMENT_CONTRACT',
        'BACKLOG_QUEUE_MOVE',
        'POST_FAILURE_RESET',
        'CALENDAR_SYNC'
    )),
    CONSTRAINT chk_sched_change_logs_disruption CHECK (disruption_category IN (
        'UNSPECIFIED',
        'LEGITIMATE_HEALTH',
        'LEGITIMATE_WORK_SCHOOL',
        'LEGITIMATE_EXTERNAL_CALENDAR',
        'OVERLOAD_TASK_TOO_LARGE',
        'OVERLOAD_PREREQUISITE_GAP',
        'PROCRASTINATION_LOW_ENERGY',
        'PROCRASTINATION_AVOIDANCE'
    )),
    CONSTRAINT chk_sched_change_logs_affected CHECK (affected_tasks_count >= 0),
    CONSTRAINT chk_sched_change_logs_minutes CHECK (total_shifted_minutes >= 0),
    CONSTRAINT chk_sched_change_logs_payload CHECK (jsonb_typeof(diff_payload) = 'object')
);

-- -----------------------------------------------------------------------------
-- 31. BẢNG MILESTONE_PROOFS (Kiểm chứng Bằng chứng Học tập Prove Mode & Mistake Intelligence)
-- Lưu vết AI Recall Check, câu trả lời, Calibration Gap, phân loại lỗi sai
-- (MISSING_FOUNDATION, CONCEPT_MISCONCEPTION, PROCESS_ERROR, LACK_OF_PRACTICE) và kết luận Prove
-- -----------------------------------------------------------------------------
CREATE TABLE milestone_proofs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    milestone_id UUID NOT NULL,
    roadmap_id UUID NOT NULL,
    user_id UUID NOT NULL,
    attempt_no SMALLINT NOT NULL DEFAULT 1,
    recall_exchanges_payload JSONB NOT NULL DEFAULT '[]'::jsonb,
    mistake_taxonomy_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    avg_self_confidence NUMERIC(3, 2) NOT NULL,
    ai_evidence_score NUMERIC(3, 2) NOT NULL,
    calibration_gap NUMERIC(4, 2) GENERATED ALWAYS AS (avg_self_confidence - ai_evidence_score) STORED,
    proof_verdict VARCHAR(25) NOT NULL DEFAULT 'PENDING',
    feedback_summary TEXT NOT NULL DEFAULT '',
    corrective_task_id UUID,
    model_used VARCHAR(100) NOT NULL DEFAULT 'gemini-2.5-flash',
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_milestone_proofs_attempt UNIQUE (milestone_id, attempt_no),
    CONSTRAINT fk_milestone_proofs_milestone FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
    CONSTRAINT fk_milestone_proofs_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT fk_milestone_proofs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_milestone_proofs_corrective_task FOREIGN KEY (corrective_task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT chk_milestone_proofs_attempt CHECK (attempt_no >= 1),
    CONSTRAINT chk_milestone_proofs_confidence CHECK (avg_self_confidence BETWEEN 1.00 AND 5.00),
    CONSTRAINT chk_milestone_proofs_score CHECK (ai_evidence_score BETWEEN 1.00 AND 5.00),
    CONSTRAINT chk_milestone_proofs_verdict CHECK (
        proof_verdict IN ('PENDING', 'PROVEN', 'NEEDS_REVIEW', 'FLAGGED_SHALLOW')
    ),
    CONSTRAINT chk_milestone_proofs_exchanges_json CHECK (jsonb_typeof(recall_exchanges_payload) = 'array'),
    CONSTRAINT chk_milestone_proofs_mistake_taxonomy CHECK (jsonb_typeof(mistake_taxonomy_json) = 'array')
);

-- =============================================================================
-- BOUNDED CONTEXT 5 / SHARED KERNEL (`shared_kernel` — 4 BẢNG)
-- Trách nhiệm: Đảm bảo phát sự kiện liên Bounded Context tin cậy (Transactional Outbox),
--              tiêu thụ sự kiện bất biến (Idempotent Consumer) trên Taskiq Worker,
--              và quản lý trạng thái thực thi bền vững của 5 Workflow cốt lõi
--              (workflow_runs & workflow_step_executions).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 32. BẢNG OUTBOX_EVENTS (Hàng đợi Sự kiện Giao dịch Liên Context - NEW v3.0)
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
-- 33. BẢNG PROCESSED_EVENTS (Sổ cái Chống Xử lý Trùng Sự kiện - NEW v3.0)
-- Khóa chính kép (event_id, handler_name) bảo đảm Idempotent Consumer cho Taskiq
-- -----------------------------------------------------------------------------
CREATE TABLE processed_events (
    event_id UUID NOT NULL,
    handler_name VARCHAR(120) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_processed_events PRIMARY KEY (event_id, handler_name),
    CONSTRAINT fk_processed_events_outbox FOREIGN KEY (event_id) REFERENCES outbox_events(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- 34. BẢNG WORKFLOW_RUNS (Trạng thái Điều phối Workflow Bền vững - NEW v3.2)
-- Lưu vết tiến trình thực thi của 5 Workflow cốt lõi (hỗ trợ Pause/Resume Human-in-the-Loop)
-- -----------------------------------------------------------------------------
CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    goal_id UUID NULL,
    roadmap_id UUID NULL,
    workflow_type VARCHAR(40) NOT NULL,
    current_step VARCHAR(60) NOT NULL,
    status VARCHAR(25) NOT NULL DEFAULT 'RUNNING',
    context_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_detail TEXT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paused_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_workflow_runs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_workflow_runs_goal FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
    CONSTRAINT fk_workflow_runs_roadmap FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE,
    CONSTRAINT chk_workflow_runs_type CHECK (
        workflow_type IN (
            'PLAN_CREATION',
            'SCHEDULE_GENERATION',
            'OVERDUE_RECOVERY',
            'WEEKLY_REVIEW',
            'CONTINUOUS_LEARNING'
        )
    ),
    CONSTRAINT chk_workflow_runs_status CHECK (
        status IN ('RUNNING', 'PAUSED_WAITING_USER', 'COMPLETED', 'FAILED', 'CANCELLED')
    ),
    CONSTRAINT chk_workflow_runs_snapshot CHECK (jsonb_typeof(context_snapshot) = 'object')
);

-- -----------------------------------------------------------------------------
-- 35. BẢNG WORKFLOW_STEP_EXECUTIONS (Nhật ký Điểm dừng & Truy vết Từng Bước Workflow - NEW v3.2)
-- Ghi nhận chi tiết đầu vào/đầu ra và liên kết ai_usage_logs của từng bước trong Workflow
-- -----------------------------------------------------------------------------
CREATE TABLE workflow_step_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_run_id UUID NOT NULL,
    step_name VARCHAR(60) NOT NULL,
    step_order SMALLINT NOT NULL,
    status VARCHAR(25) NOT NULL DEFAULT 'RUNNING',
    input_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    ai_usage_log_id UUID NULL,
    retry_count SMALLINT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    CONSTRAINT fk_workflow_steps_run FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE,
    CONSTRAINT fk_workflow_steps_ai_log FOREIGN KEY (ai_usage_log_id) REFERENCES ai_usage_logs(id) ON DELETE SET NULL,
    CONSTRAINT chk_workflow_steps_order CHECK (step_order >= 1),
    CONSTRAINT chk_workflow_steps_status CHECK (
        status IN ('PENDING', 'RUNNING', 'WAITING_USER', 'COMPLETED', 'FAILED', 'SKIPPED')
    ),
    CONSTRAINT chk_workflow_steps_input_json CHECK (jsonb_typeof(input_summary) = 'object'),
    CONSTRAINT chk_workflow_steps_output_json CHECK (jsonb_typeof(output_payload) = 'object'),
    CONSTRAINT chk_workflow_steps_retry CHECK (retry_count >= 0)
);

-- =============================================================================
-- 6. TRIGGERS: TỰ ĐỘNG CẬP NHẬT UPDATED_AT CHO TẤT CẢ 26 BẢNG CÓ CỘT UPDATED_AT
-- =============================================================================
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_learner_profiles_updated_at BEFORE UPDATE ON learner_profiles FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_webcal_tokens_updated_at BEFORE UPDATE ON webcal_tokens FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_calendar_connections_updated_at BEFORE UPDATE ON calendar_connections FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_availabilities_updated_at BEFORE UPDATE ON availabilities FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_availability_slots_updated_at
    BEFORE UPDATE ON availability_slots
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_ai_quotas_updated_at BEFORE UPDATE ON ai_quotas FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_payment_transactions_updated_at BEFORE UPDATE ON payment_transactions FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_learner_memory_items_updated_at BEFORE UPDATE ON learner_memory_items FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_learner_concept_masteries_updated_at BEFORE UPDATE ON learner_concept_masteries FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_goals_updated_at BEFORE UPDATE ON goals FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_roadmaps_updated_at BEFORE UPDATE ON roadmaps FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_milestones_updated_at BEFORE UPDATE ON milestones FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_official_schedules_updated_at BEFORE UPDATE ON official_schedules FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_schedule_proposals_updated_at BEFORE UPDATE ON schedule_proposals FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_learning_concepts_updated_at BEFORE UPDATE ON learning_concepts FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_knowledge_sources_updated_at BEFORE UPDATE ON knowledge_sources FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_schedule_blocks_updated_at BEFORE UPDATE ON schedule_blocks FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_study_sessions_updated_at BEFORE UPDATE ON study_sessions FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_session_tasks_updated_at BEFORE UPDATE ON session_tasks FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_study_notes_updated_at BEFORE UPDATE ON study_notes FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_pause_records_updated_at BEFORE UPDATE ON pause_records FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_ai_reviews_updated_at BEFORE UPDATE ON ai_reviews FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_milestone_proofs_updated_at BEFORE UPDATE ON milestone_proofs FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_workflow_runs_updated_at BEFORE UPDATE ON workflow_runs FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =============================================================================
-- CHỈ MỤC HIỆU NĂNG & BẢO VỆ ĐỒNG THỜI (INDEXES & PARTIAL CONSTRAINTS — 67 CHỈ MỤC)
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

-- 1.6 Chống xung đột khung giờ rảnh đồng thời (DEC-03)
CREATE UNIQUE INDEX uq_availability_slots_active_time ON availability_slots (availability_id, day_of_week, start_time) WHERE is_active = TRUE;

-- 1.7 Duy nhất 1 ghi chép đúc kết TAKEAWAY cho mỗi cặp phiên học và nhiệm vụ (DEC-02)
CREATE UNIQUE INDEX uq_study_notes_takeaway ON study_notes (session_id, task_id) WHERE note_type = 'TAKEAWAY';

-- 2. TỐI ƯU HÓA TRUY VẤN NÓNG (HOT QUERIES), QUOTA SWEEPER, OUTBOX RELAY, HYBRID RAG & DASHBOARD
-- 2.1 Quét nhanh các bản ghi giữ chỗ Quota quá hạn (Taskiq QuotaSweeper mỗi 60s)
CREATE INDEX idx_quota_reservations_cleanup ON ai_quota_reservations(expires_at) WHERE status = 'RESERVED';
CREATE INDEX idx_quota_reservations_user_status ON ai_quota_reservations(user_id, status, created_at DESC);

-- 2.2 Truy vấn lịch sử giao dịch thanh toán của người dùng và đối soát trạng thái
CREATE INDEX idx_payment_transactions_user_created ON payment_transactions(user_id, created_at DESC);
CREATE INDEX idx_payment_transactions_status ON payment_transactions(status, created_at DESC);
CREATE INDEX idx_payment_transactions_pending_expires ON payment_transactions (expires_at) WHERE status = 'PENDING';

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

-- 2.24 Chỉ mục Kết nối Lịch Ngoại vi OAuth
CREATE INDEX idx_calendar_connections_user_status ON calendar_connections(user_id, sync_status);

-- 2.25 Truy vấn các task con của một task cha (Micro-Stepping) & Ground Truth Concept
CREATE INDEX idx_tasks_parent_task_id ON tasks(parent_task_id) WHERE parent_task_id IS NOT NULL;
CREATE INDEX idx_tasks_concept_id ON tasks(concept_id) WHERE concept_id IS NOT NULL;

-- 2.26 Truy vấn Backlog Recovery Queue theo Roadmap
CREATE INDEX idx_tasks_backlog_queue ON tasks(roadmap_id, milestone_id, reschedule_count DESC)
    WHERE scheduled_date IS NULL AND status IN ('TODO', 'IN_PROGRESS');

-- 2.27 Quét nhanh các lộ trình Dormant (không có hoạt động học >= 7 ngày)
CREATE INDEX idx_roadmaps_dormant_scan ON roadmaps(status, last_study_activity_at)
    WHERE status = 'ACTIVE';

-- 2.28 Truy vấn phiên học còn nợ Takeaway do Auto-close (UC-15)
CREATE INDEX idx_study_sessions_pending_takeaway ON study_sessions(user_id, ended_at DESC)
    WHERE pending_takeaway = TRUE;

-- 2.29 Truy vấn lịch sử kiểm chứng Prove Mode theo Milestone và Người học
CREATE INDEX idx_milestone_proofs_milestone ON milestone_proofs(milestone_id, attempt_no DESC);
CREATE INDEX idx_milestone_proofs_user_verdict ON milestone_proofs(user_id, proof_verdict, evaluated_at DESC);

-- 2.30 Truy vấn Trí nhớ Người học Cấu trúc hóa (Structured Learner Memory)
CREATE INDEX idx_learner_memory_items_user_cat ON learner_memory_items(user_id, memory_category, confirmation_status);

-- 2.31 Truy vấn Mức độ Thành thạo Khái niệm & Lịch Ôn tập Thông minh (Skill Mastery)
CREATE INDEX idx_learner_concept_masteries_user_review ON learner_concept_masteries(user_id, next_review_at)
    WHERE next_review_at IS NOT NULL;
CREATE INDEX idx_learner_concept_masteries_concept ON learner_concept_masteries(concept_id);

-- 2.32 Truy vấn Nguồn Tài liệu Học tập (Knowledge Sources)
CREATE INDEX idx_knowledge_sources_goal_status ON knowledge_sources(goal_id, ingestion_status);
CREATE INDEX idx_knowledge_sources_user_created ON knowledge_sources(user_id, created_at DESC);

-- 2.33 Truy vấn Hybrid RAG trên Phân đoạn Tri thức (B-Tree + GIN TSVECTOR + HNSW PGVECTOR)
CREATE INDEX idx_knowledge_chunks_goal_id ON knowledge_chunks(goal_id);
CREATE INDEX idx_knowledge_chunks_search_vector ON knowledge_chunks USING GIN (search_vector);
CREATE INDEX idx_knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

-- 2.34 Truy vấn Khối Lịch Học Thực thi & Đồng bộ Sự kiện Lịch Ngoại vi (Schedule Blocks)
CREATE INDEX idx_schedule_blocks_roadmap_date ON schedule_blocks(roadmap_id, block_date, start_time);
CREATE INDEX idx_schedule_blocks_schedule_id ON schedule_blocks(official_schedule_id);
CREATE INDEX idx_schedule_blocks_task_id ON schedule_blocks(task_id) WHERE task_id IS NOT NULL;
CREATE INDEX idx_schedule_blocks_external_event ON schedule_blocks(external_calendar_event_id)
    WHERE external_calendar_event_id IS NOT NULL;

-- 2.35 Truy vấn Điều phối Workflow Bền vững & Nhật ký Từng Bước (Durable Workflows)
CREATE INDEX idx_workflow_runs_user_status ON workflow_runs(user_id, status, updated_at DESC);
CREATE INDEX idx_workflow_runs_roadmap_type ON workflow_runs(roadmap_id, workflow_type)
    WHERE roadmap_id IS NOT NULL;
CREATE INDEX idx_workflow_step_executions_run_order ON workflow_step_executions(workflow_run_id, step_order);

-- 2.36 Các chỉ mục Khóa ngoại tối ưu hóa hiệu năng (Foreign Key Optimization Indexes)
CREATE INDEX idx_ai_quota_reservations_quota_id ON ai_quota_reservations(quota_id);
CREATE INDEX idx_sched_change_logs_schedule_id ON schedule_change_logs(schedule_id) WHERE schedule_id IS NOT NULL;
CREATE INDEX idx_sched_change_logs_task_id ON schedule_change_logs(task_id) WHERE task_id IS NOT NULL;
CREATE INDEX idx_milestone_proofs_roadmap_id ON milestone_proofs(roadmap_id);
CREATE INDEX idx_milestone_proofs_corrective_task_id ON milestone_proofs(corrective_task_id) WHERE corrective_task_id IS NOT NULL;
CREATE INDEX idx_workflow_runs_goal_id ON workflow_runs(goal_id) WHERE goal_id IS NOT NULL;
CREATE INDEX idx_workflow_step_executions_ai_log_id ON workflow_step_executions(ai_usage_log_id) WHERE ai_usage_log_id IS NOT NULL;

