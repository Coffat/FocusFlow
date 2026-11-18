-- ============================================================================
-- FocusFlow — PostgreSQL 16 Physical Database DDL
-- GENERATED from Alembic head via backend/scripts/dump_schema.sh
-- DO NOT EDIT BY HAND. All schema changes must go through Alembic migrations.
-- ============================================================================

--
-- PostgreSQL database dump
--

\restrict ksecOrFoe4YIR9lYCw8RygNUJnINrwfLr6TAjvZMbPBevhAGy1DVOduAagc3Db9

-- Dumped from database version 16.15 (Debian 16.15-1.pgdg12+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg12+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: fn_set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_quota_reservations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_quota_reservations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    quota_id uuid NOT NULL,
    user_id uuid NOT NULL,
    operation_type character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'RESERVED'::character varying NOT NULL,
    tokens_reserved integer DEFAULT 0 NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    CONSTRAINT chk_ai_quota_res_resolved CHECK (((((status)::text = 'RESERVED'::text) AND (resolved_at IS NULL)) OR (((status)::text <> 'RESERVED'::text) AND (resolved_at IS NOT NULL)))),
    CONSTRAINT chk_ai_quota_res_status CHECK (((status)::text = ANY ((ARRAY['RESERVED'::character varying, 'COMMITTED'::character varying, 'RELEASED'::character varying, 'EXPIRED'::character varying])::text[]))),
    CONSTRAINT chk_ai_quota_res_tokens CHECK ((tokens_reserved >= 0))
);


--
-- Name: ai_quotas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_quotas (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    monthly_limit integer DEFAULT 30 NOT NULL,
    used_calls integer DEFAULT 0 NOT NULL,
    reserved_calls integer DEFAULT 0 NOT NULL,
    tokens_consumed bigint DEFAULT '0'::bigint NOT NULL,
    cycle_start timestamp with time zone NOT NULL,
    cycle_end timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_ai_quotas_cycle CHECK ((cycle_end > cycle_start)),
    CONSTRAINT chk_ai_quotas_limit CHECK (((used_calls + reserved_calls) <= monthly_limit)),
    CONSTRAINT chk_ai_quotas_monthly_limit CHECK ((monthly_limit > 0)),
    CONSTRAINT chk_ai_quotas_reserved_calls CHECK ((reserved_calls >= 0)),
    CONSTRAINT chk_ai_quotas_tokens CHECK ((tokens_consumed >= 0)),
    CONSTRAINT chk_ai_quotas_used_calls CHECK ((used_calls >= 0))
);


--
-- Name: ai_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_reviews (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    user_id uuid NOT NULL,
    milestone_id uuid,
    review_cycle character varying(20) NOT NULL,
    period_start date,
    period_end date,
    quantitative_summary jsonb DEFAULT '{}'::jsonb NOT NULL,
    strengths_feedback text NOT NULL,
    bottlenecks_feedback text NOT NULL,
    action_recommendations text NOT NULL,
    model_used character varying(100) NOT NULL,
    generated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    user_reflection_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT chk_ai_reviews_cycle CHECK (((review_cycle)::text = ANY ((ARRAY['WEEKLY'::character varying, 'MILESTONE'::character varying])::text[]))),
    CONSTRAINT chk_ai_reviews_period_order CHECK (((((review_cycle)::text = 'MILESTONE'::text) AND (milestone_id IS NOT NULL) AND (period_start IS NULL) AND (period_end IS NULL)) OR (((review_cycle)::text = 'WEEKLY'::text) AND (milestone_id IS NULL) AND (period_start IS NOT NULL) AND (period_end IS NOT NULL) AND (period_end >= period_start)))),
    CONSTRAINT chk_ai_reviews_quantitative_summary CHECK ((jsonb_typeof(quantitative_summary) = 'object'::text)),
    CONSTRAINT chk_ai_reviews_reflection CHECK ((jsonb_typeof(user_reflection_payload) = 'object'::text))
);


--
-- Name: ai_usage_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_usage_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    action_type character varying(50) NOT NULL,
    model_name character varying(100) DEFAULT 'gpt-4o-mini'::character varying NOT NULL,
    prompt_tokens integer DEFAULT 0 NOT NULL,
    completion_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    latency_ms integer DEFAULT 0 NOT NULL,
    status character varying(20) DEFAULT 'SUCCESS'::character varying NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    estimated_cost_usd numeric(12,6) DEFAULT '0'::numeric NOT NULL,
    error_code character varying(80),
    idempotency_key character varying(255),
    audit_metadata jsonb,
    CONSTRAINT chk_ai_usage_logs_action CHECK (((action_type)::text = ANY ((ARRAY['ROADMAP_GENERATION'::character varying, 'SCHEDULE_PROPOSAL'::character varying, 'AI_REVIEW_WEEKLY'::character varying, 'AI_REVIEW_MILESTONE'::character varying, 'MILESTONE_BREAKDOWN'::character varying, 'CHAT_ASSISTANT'::character varying, 'KNOWLEDGE_INGESTION'::character varying, 'WHAT_IF_SIMULATION'::character varying, 'OVERDUE_RECOVERY'::character varying, 'CONTINUOUS_LEARNING'::character varying, 'GOAL_CLARIFICATION'::character varying])::text[]))),
    CONSTRAINT chk_ai_usage_logs_latency CHECK ((latency_ms >= 0)),
    CONSTRAINT chk_ai_usage_logs_status CHECK (((status)::text = ANY ((ARRAY['SUCCESS'::character varying, 'FAILED'::character varying, 'RATE_LIMITED'::character varying, 'TIMEOUT'::character varying])::text[]))),
    CONSTRAINT chk_ai_usage_logs_tokens CHECK (((prompt_tokens >= 0) AND (completion_tokens >= 0) AND (total_tokens >= 0)))
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: availabilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.availabilities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    mode character varying(20) DEFAULT 'MODE_A'::character varying NOT NULL,
    calendar_integration_mode character varying(20) DEFAULT 'NONE'::character varying NOT NULL,
    daily_quotas jsonb DEFAULT '{}'::jsonb NOT NULL,
    min_session_minutes integer DEFAULT 30 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_availabilities_cal_mode CHECK (((calendar_integration_mode)::text = ANY ((ARRAY['NONE'::character varying, 'EXPORT_ICS'::character varying, 'CONNECTED'::character varying])::text[]))),
    CONSTRAINT chk_availabilities_min_session CHECK (((min_session_minutes >= 15) AND (min_session_minutes <= 120))),
    CONSTRAINT chk_availabilities_mode CHECK (((mode)::text = ANY ((ARRAY['MODE_A'::character varying, 'MODE_B'::character varying])::text[])))
);


--
-- Name: availability_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.availability_slots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    availability_id uuid NOT NULL,
    day_of_week smallint NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    end_day_offset smallint DEFAULT '0'::smallint NOT NULL,
    slot_type character varying(20) DEFAULT 'ALLOWED'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    energy_level character varying(10) DEFAULT 'MEDIUM'::character varying NOT NULL,
    CONSTRAINT chk_avail_slots_day CHECK (((day_of_week >= 0) AND (day_of_week <= 6))),
    CONSTRAINT chk_avail_slots_energy CHECK (((energy_level)::text = ANY ((ARRAY['LOW'::character varying, 'MEDIUM'::character varying, 'HIGH'::character varying])::text[]))),
    CONSTRAINT chk_avail_slots_offset CHECK ((end_day_offset = ANY (ARRAY[0, 1]))),
    CONSTRAINT chk_avail_slots_time CHECK (((end_day_offset = 1) OR (end_time > start_time))),
    CONSTRAINT chk_avail_slots_type CHECK (((slot_type)::text = ANY ((ARRAY['ALLOWED'::character varying, 'FIXED'::character varying])::text[])))
);


--
-- Name: calendar_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.calendar_connections (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    provider character varying(30) DEFAULT 'GOOGLE'::character varying NOT NULL,
    external_calendar_id character varying(255) DEFAULT 'primary'::character varying NOT NULL,
    oauth_refresh_token_encrypted text NOT NULL,
    sync_status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    sync_token text,
    channel_id character varying(255),
    resource_id character varying(255),
    channel_token_hash character varying(64),
    channel_expiration timestamp with time zone,
    source_calendars_json jsonb DEFAULT '["primary"]'::jsonb NOT NULL,
    sync_metadata_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    last_synced_at timestamp with time zone,
    error_detail text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_calendar_connections_provider CHECK (((provider)::text = ANY ((ARRAY['GOOGLE'::character varying, 'OUTLOOK'::character varying, 'LOCAL_MOCK'::character varying])::text[]))),
    CONSTRAINT chk_calendar_connections_status CHECK (((sync_status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'REVOKED'::character varying, 'ERROR'::character varying])::text[])))
);


--
-- Name: concept_prerequisites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.concept_prerequisites (
    source_concept_id character varying(120) NOT NULL,
    prerequisite_concept_id character varying(120) NOT NULL,
    relation_type character varying(30) DEFAULT 'REQUIRES'::character varying NOT NULL,
    rationale text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_concept_prerequisites_no_self_loop CHECK (((source_concept_id)::text <> (prerequisite_concept_id)::text)),
    CONSTRAINT chk_concept_prerequisites_relation_type CHECK (((relation_type)::text = ANY ((ARRAY['REQUIRES'::character varying, 'RECOMMENDED_BEFORE'::character varying])::text[])))
);


--
-- Name: goals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.goals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    title text NOT NULL,
    raw_description text NOT NULL,
    target_date date,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    prior_knowledge_level character varying(50) DEFAULT 'BEGINNER'::character varying NOT NULL,
    clarification_context text,
    CONSTRAINT chk_goals_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'COMPLETED'::character varying, 'ARCHIVED'::character varying])::text[])))
);


--
-- Name: knowledge_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_chunks (
    id uuid NOT NULL,
    source_id uuid NOT NULL,
    goal_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    section_title character varying(255),
    page_number integer,
    content text NOT NULL,
    token_count integer NOT NULL,
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple'::regconfig, content)) STORED NOT NULL,
    embedding public.vector(768),
    provenance_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_knowledge_chunks_index CHECK ((chunk_index >= 0)),
    CONSTRAINT chk_knowledge_chunks_page CHECK (((page_number IS NULL) OR (page_number >= 1))),
    CONSTRAINT chk_knowledge_chunks_provenance CHECK ((jsonb_typeof(provenance_json) = 'object'::text)),
    CONSTRAINT chk_knowledge_chunks_tokens CHECK ((token_count > 0))
);


--
-- Name: knowledge_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_sources (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    goal_id uuid NOT NULL,
    source_type character varying(20) NOT NULL,
    title character varying(255) NOT NULL,
    source_uri text,
    content_hash character varying(64) NOT NULL,
    ingestion_status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    chunk_count integer DEFAULT 0 NOT NULL,
    provenance_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    error_detail text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_knowledge_sources_chunks CHECK ((chunk_count >= 0)),
    CONSTRAINT chk_knowledge_sources_hash CHECK (((content_hash)::text ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT chk_knowledge_sources_provenance CHECK ((jsonb_typeof(provenance_metadata) = 'object'::text)),
    CONSTRAINT chk_knowledge_sources_status CHECK (((ingestion_status)::text = ANY ((ARRAY['PENDING'::character varying, 'PROCESSING'::character varying, 'INDEXED'::character varying, 'FAILED'::character varying, 'QUARANTINED'::character varying])::text[]))),
    CONSTRAINT chk_knowledge_sources_type CHECK (((source_type)::text = ANY ((ARRAY['PDF'::character varying, 'DOCX'::character varying, 'TXT'::character varying, 'URL'::character varying])::text[])))
);


--
-- Name: learner_concept_masteries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.learner_concept_masteries (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    concept_key character varying(160) NOT NULL,
    mastery_score numeric(5,4) NOT NULL,
    evidence_count integer NOT NULL,
    last_evidence_type character varying(40) NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_learner_mastery_evidence CHECK ((evidence_count > 0)),
    CONSTRAINT chk_learner_mastery_score CHECK (((mastery_score >= (0)::numeric) AND (mastery_score <= (1)::numeric)))
);


--
-- Name: learner_memory_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.learner_memory_items (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    memory_key character varying(160) NOT NULL,
    value jsonb NOT NULL,
    category character varying(30) NOT NULL,
    epistemic_level character varying(20) NOT NULL,
    confidence double precision NOT NULL,
    sample_size integer DEFAULT 0 NOT NULL,
    evidence jsonb DEFAULT '[]'::jsonb NOT NULL,
    observation_started_at timestamp with time zone,
    observation_ended_at timestamp with time zone,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_learner_memory_confidence CHECK (((confidence >= (0)::double precision) AND (confidence <= (1)::double precision))),
    CONSTRAINT chk_learner_memory_epistemic CHECK (((epistemic_level)::text = ANY ((ARRAY['EXPLICIT'::character varying, 'OBSERVED'::character varying, 'INFERRED'::character varying])::text[]))),
    CONSTRAINT chk_learner_memory_sample_size CHECK ((sample_size >= 0)),
    CONSTRAINT chk_learner_memory_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'CONFIRMED'::character varying, 'REJECTED'::character varying])::text[])))
);


--
-- Name: learner_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.learner_profiles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    optimal_focus_duration_mins integer DEFAULT 25 NOT NULL,
    peak_productivity_slots jsonb DEFAULT '["MORNING", "EVENING"]'::jsonb NOT NULL,
    estimation_bias_factor numeric(4,2) DEFAULT 1.00 NOT NULL,
    weekly_completion_rate numeric(5,2) DEFAULT 0.00 NOT NULL,
    total_completed_sessions integer DEFAULT 0 NOT NULL,
    is_cold_start boolean DEFAULT true NOT NULL,
    last_aggregated_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_learner_profiles_bias CHECK (((estimation_bias_factor >= 0.50) AND (estimation_bias_factor <= 2.00))),
    CONSTRAINT chk_learner_profiles_duration CHECK (((optimal_focus_duration_mins >= 15) AND (optimal_focus_duration_mins <= 120))),
    CONSTRAINT chk_learner_profiles_rate CHECK (((weekly_completion_rate >= 0.00) AND (weekly_completion_rate <= 100.00))),
    CONSTRAINT chk_learner_profiles_sessions CHECK ((total_completed_sessions >= 0))
);


--
-- Name: learning_concepts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.learning_concepts (
    concept_id character varying(120) NOT NULL,
    title character varying(255) NOT NULL,
    summary text NOT NULL,
    domain character varying(100) NOT NULL,
    difficulty_level character varying(50) DEFAULT 'BEGINNER'::character varying NOT NULL,
    estimated_effort_minutes integer DEFAULT 60 NOT NULL,
    keywords jsonb DEFAULT '[]'::jsonb NOT NULL,
    learning_outcomes jsonb DEFAULT '[]'::jsonb NOT NULL,
    verification_status character varying(30) DEFAULT 'VERIFIED'::character varying NOT NULL,
    version character varying(20) DEFAULT '1.0.0'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_learning_concepts_effort_positive CHECK ((estimated_effort_minutes > 0)),
    CONSTRAINT chk_learning_concepts_verification_status CHECK (((verification_status)::text = ANY ((ARRAY['VERIFIED'::character varying, 'UNVERIFIED'::character varying, 'DEPRECATED'::character varying])::text[])))
);


--
-- Name: milestone_proofs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.milestone_proofs (
    id uuid NOT NULL,
    milestone_id uuid NOT NULL,
    user_id uuid NOT NULL,
    status character varying(24) DEFAULT 'DRAFT'::character varying NOT NULL,
    questions jsonb DEFAULT '[]'::jsonb NOT NULL,
    answers jsonb DEFAULT '[]'::jsonb NOT NULL,
    score integer,
    confidence numeric(5,4),
    corrective_action text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    submitted_at timestamp with time zone,
    CONSTRAINT chk_milestone_proofs_confidence CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT chk_milestone_proofs_status CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'READY'::character varying, 'SUBMITTED'::character varying, 'PASSED'::character varying, 'NEEDS_REVIEW'::character varying])::text[])))
);


--
-- Name: milestones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.milestones (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    sequence_order integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    proof_status character varying(20) DEFAULT 'UNVERIFIED'::character varying NOT NULL,
    learning_outcomes jsonb DEFAULT '[]'::jsonb NOT NULL,
    completion_criteria text,
    estimated_effort_minutes integer DEFAULT 60 NOT NULL,
    required_concepts jsonb DEFAULT '[]'::jsonb NOT NULL,
    unverified_concepts jsonb DEFAULT '[]'::jsonb NOT NULL,
    prerequisite_milestone_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT chk_milestones_proof_status CHECK (((proof_status)::text = ANY ((ARRAY['UNVERIFIED'::character varying, 'PENDING_REVIEW'::character varying, 'PROVEN'::character varying, 'NEEDS_REVIEW'::character varying])::text[]))),
    CONSTRAINT chk_milestones_seq CHECK ((sequence_order >= 1)),
    CONSTRAINT chk_milestones_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'APPROVED'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying])::text[])))
);


--
-- Name: official_schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.official_schedules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    total_sessions integer DEFAULT 0 NOT NULL,
    total_planned_minutes integer DEFAULT 0 NOT NULL,
    activated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    buffer_minutes_per_week integer DEFAULT 60 NOT NULL,
    recovery_window_days smallint DEFAULT '7'::smallint NOT NULL,
    daily_workload_cap_minutes integer DEFAULT 180 NOT NULL,
    stability_weight numeric(4,3) DEFAULT 0.800 NOT NULL,
    CONSTRAINT chk_official_schedules_minutes CHECK ((total_planned_minutes >= 0)),
    CONSTRAINT chk_official_schedules_resilience CHECK (((buffer_minutes_per_week >= 0) AND ((recovery_window_days >= 7) AND (recovery_window_days <= 14)) AND ((daily_workload_cap_minutes >= 30) AND (daily_workload_cap_minutes <= 840)) AND ((stability_weight >= (0)::numeric) AND (stability_weight <= (1)::numeric)))),
    CONSTRAINT chk_official_schedules_sessions CHECK ((total_sessions >= 0))
);


--
-- Name: outbox_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outbox_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    aggregate_type character varying(100) NOT NULL,
    aggregate_id uuid NOT NULL,
    event_type character varying(120) NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    retry_count integer DEFAULT 0 NOT NULL,
    correlation_id character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    published_at timestamp with time zone,
    CONSTRAINT chk_outbox_events_payload CHECK ((jsonb_typeof(payload) = 'object'::text)),
    CONSTRAINT chk_outbox_events_published CHECK (((((status)::text = 'PUBLISHED'::text) AND (published_at IS NOT NULL)) OR (((status)::text <> 'PUBLISHED'::text) AND (published_at IS NULL)))),
    CONSTRAINT chk_outbox_events_retry CHECK ((retry_count >= 0)),
    CONSTRAINT chk_outbox_events_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'PUBLISHED'::character varying, 'FAILED'::character varying])::text[])))
);


--
-- Name: pause_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pause_records (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    pause_start_date date NOT NULL,
    pause_end_date date NOT NULL,
    shifted_days integer NOT NULL,
    reason text,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_pause_records_dates CHECK ((pause_end_date >= pause_start_date)),
    CONSTRAINT chk_pause_records_duration CHECK ((shifted_days = ((pause_end_date - pause_start_date) + 1))),
    CONSTRAINT chk_pause_records_shifted CHECK ((shifted_days > 0)),
    CONSTRAINT chk_pause_records_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'COMPLETED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: payment_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_transactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    transaction_ref character varying(100) NOT NULL,
    gateway_provider character varying(20) DEFAULT 'PAYOS'::character varying NOT NULL,
    amount_vnd integer NOT NULL,
    currency character varying(10) DEFAULT 'VND'::character varying NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    qr_code_url text,
    webhook_signature_verified boolean DEFAULT false NOT NULL,
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_payment_transactions_amount CHECK ((amount_vnd > 0)),
    CONSTRAINT chk_payment_transactions_paid_at CHECK (((((status)::text = ANY ((ARRAY['PAID'::character varying, 'REFUNDED'::character varying])::text[])) AND (paid_at IS NOT NULL)) OR (((status)::text <> ALL ((ARRAY['PAID'::character varying, 'REFUNDED'::character varying])::text[])) AND (paid_at IS NULL)))),
    CONSTRAINT chk_payment_transactions_provider CHECK (((gateway_provider)::text = ANY ((ARRAY['PAYOS'::character varying, 'VNPAY'::character varying, 'MOCK'::character varying])::text[]))),
    CONSTRAINT chk_payment_transactions_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'PAID'::character varying, 'FAILED'::character varying, 'CANCELLED'::character varying, 'REFUNDED'::character varying])::text[])))
);


--
-- Name: processed_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processed_events (
    event_id uuid NOT NULL,
    handler_name character varying(120) NOT NULL,
    processed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: roadmaps; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roadmaps (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    goal_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    status character varying(20) DEFAULT 'INITIALIZED'::character varying NOT NULL,
    start_date date,
    target_date date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    weekly_reschedule_budget smallint DEFAULT '3'::smallint NOT NULL,
    weekly_reschedule_used smallint DEFAULT '0'::smallint NOT NULL,
    budget_week_start date,
    last_study_activity_at timestamp with time zone,
    reset_ritual_count integer DEFAULT 0 NOT NULL,
    planning_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT chk_roadmaps_dates CHECK (((target_date IS NULL) OR (start_date IS NULL) OR (target_date >= start_date))),
    CONSTRAINT chk_roadmaps_reset_count CHECK ((reset_ritual_count >= 0)),
    CONSTRAINT chk_roadmaps_status CHECK (((status)::text = ANY ((ARRAY['INITIALIZED'::character varying, 'ACTIVE'::character varying, 'PAUSED'::character varying, 'COMPLETED'::character varying, 'ARCHIVED'::character varying])::text[]))),
    CONSTRAINT chk_roadmaps_weekly_budget CHECK (((weekly_reschedule_budget >= 0) AND (weekly_reschedule_used >= 0)))
);


--
-- Name: schedule_blocks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_blocks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    official_schedule_id uuid NOT NULL,
    task_id uuid,
    sequence_in_task smallint DEFAULT '1'::smallint NOT NULL,
    block_type character varying(20) DEFAULT 'STUDY'::character varying NOT NULL,
    block_date date NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    scheduled_duration_minutes integer NOT NULL,
    is_protected boolean DEFAULT false NOT NULL,
    status character varying(20) DEFAULT 'PLANNED'::character varying NOT NULL,
    external_calendar_event_id character varying(255),
    etag character varying(255),
    sync_status character varying(30) DEFAULT 'SYNCED'::character varying NOT NULL,
    last_synced_at timestamp with time zone,
    placement_rationale text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_schedule_blocks_duration CHECK (((scheduled_duration_minutes >= 10) AND (scheduled_duration_minutes <= 240))),
    CONSTRAINT chk_schedule_blocks_seq CHECK ((sequence_in_task >= 1)),
    CONSTRAINT chk_schedule_blocks_status CHECK (((status)::text = ANY ((ARRAY['PLANNED'::character varying, 'COMPLETED'::character varying, 'MISSED'::character varying, 'RESCHEDULED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT chk_schedule_blocks_time_order CHECK ((end_time > start_time)),
    CONSTRAINT chk_schedule_blocks_type CHECK (((block_type)::text = ANY ((ARRAY['STUDY'::character varying, 'BUFFER'::character varying, 'REVISION'::character varying, 'RECOVERY'::character varying])::text[])))
);


--
-- Name: schedule_change_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_change_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    schedule_id uuid,
    task_id uuid,
    trigger_type character varying(30) NOT NULL,
    reason text,
    affected_tasks_count integer DEFAULT 1 NOT NULL,
    total_shifted_minutes integer DEFAULT 0 NOT NULL,
    diff_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    disruption_category character varying(40),
    counts_toward_budget boolean DEFAULT true NOT NULL,
    CONSTRAINT chk_sched_change_logs_affected CHECK ((affected_tasks_count >= 0)),
    CONSTRAINT chk_sched_change_logs_minutes CHECK ((total_shifted_minutes >= 0)),
    CONSTRAINT chk_sched_change_logs_payload CHECK ((jsonb_typeof(diff_payload) = 'object'::text)),
    CONSTRAINT chk_sched_change_logs_trigger CHECK (((trigger_type)::text = ANY ((ARRAY['DOMINO_SHIFT'::character varying, 'MANUAL_EDIT'::character varying, 'AI_REPLAN'::character varying, 'CALENDAR_SYNC'::character varying])::text[])))
);


--
-- Name: schedule_proposals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_proposals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    user_id uuid NOT NULL,
    proposal_data jsonb NOT NULL,
    status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    applied_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    proposal_type character varying(35) DEFAULT 'INITIAL_SCHEDULE'::character varying NOT NULL,
    original_proposal_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    user_edit_count integer DEFAULT 0 NOT NULL,
    pedagogical_warnings jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT chk_schedule_proposals_data CHECK ((jsonb_typeof(proposal_data) = 'object'::text)),
    CONSTRAINT chk_schedule_proposals_edit_count CHECK ((user_edit_count >= 0)),
    CONSTRAINT chk_schedule_proposals_original CHECK ((jsonb_typeof(original_proposal_data) = 'object'::text)),
    CONSTRAINT chk_schedule_proposals_status CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'APPLIED'::character varying, 'DISCARDED'::character varying])::text[]))),
    CONSTRAINT chk_schedule_proposals_type CHECK (((proposal_type)::text = ANY ((ARRAY['INITIAL_SCHEDULE'::character varying, 'AI_RECOVERY'::character varying, 'POST_FAILURE_RESET'::character varying, 'SCHEDULE_ONLY_REOPTIMIZE'::character varying, 'WHAT_IF_SIMULATION'::character varying])::text[]))),
    CONSTRAINT chk_schedule_proposals_warnings CHECK ((jsonb_typeof(pedagogical_warnings) = 'array'::text))
);


--
-- Name: session_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    task_id uuid NOT NULL,
    allocated_minutes integer DEFAULT 0 NOT NULL,
    actual_minutes integer DEFAULT 0 NOT NULL,
    status_after_session character varying(20) DEFAULT 'IN_PROGRESS'::character varying NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_session_tasks_actual CHECK ((actual_minutes >= 0)),
    CONSTRAINT chk_session_tasks_allocated CHECK ((allocated_minutes >= 0)),
    CONSTRAINT chk_session_tasks_status_after CHECK (((status_after_session)::text = ANY ((ARRAY['TODO'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying])::text[])))
);


--
-- Name: study_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.study_notes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    session_id uuid,
    task_id uuid,
    note_type character varying(20) NOT NULL,
    content text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    self_confidence smallint,
    ai_evidence_score numeric(4,2),
    alignment_flag character varying(20) DEFAULT 'UNCHECKED'::character varying NOT NULL,
    verification_status character varying(25) DEFAULT 'PENDING_PROVE'::character varying NOT NULL,
    CONSTRAINT chk_study_notes_alignment CHECK (((alignment_flag)::text = ANY ((ARRAY['UNCHECKED'::character varying, 'ALIGNED'::character varying, 'SUPERFICIAL'::character varying, 'OFF_TOPIC'::character varying, 'CONTRADICTORY'::character varying])::text[]))),
    CONSTRAINT chk_study_notes_confidence CHECK (((self_confidence IS NULL) OR ((self_confidence >= 1) AND (self_confidence <= 5)))),
    CONSTRAINT chk_study_notes_evidence CHECK (((ai_evidence_score IS NULL) OR ((ai_evidence_score >= (1)::numeric) AND (ai_evidence_score <= (5)::numeric)))),
    CONSTRAINT chk_study_notes_type CHECK (((note_type)::text = ANY ((ARRAY['SCRATCHPAD'::character varying, 'TAKEAWAY'::character varying, 'GENERAL'::character varying])::text[]))),
    CONSTRAINT chk_study_notes_verification CHECK (((verification_status)::text = ANY ((ARRAY['PENDING_PROVE'::character varying, 'VERIFIED'::character varying, 'FLAGGED_SHALLOW'::character varying, 'NEEDS_REVIEW'::character varying])::text[])))
);


--
-- Name: study_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.study_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    roadmap_id uuid NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    planned_minutes integer NOT NULL,
    actual_minutes integer DEFAULT 0 NOT NULL,
    status character varying(20) DEFAULT 'IN_PROGRESS'::character varying NOT NULL,
    last_heartbeat_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    session_mode character varying(15) DEFAULT 'STANDARD'::character varying NOT NULL,
    pending_takeaway boolean DEFAULT false NOT NULL,
    checkin_time_sufficiency character varying(15),
    checkin_perceived_difficulty smallint,
    checkin_focus_level smallint,
    CONSTRAINT chk_study_sessions_actual_min CHECK ((actual_minutes >= 0)),
    CONSTRAINT chk_study_sessions_checkin_scores CHECK ((((checkin_perceived_difficulty IS NULL) OR ((checkin_perceived_difficulty >= 1) AND (checkin_perceived_difficulty <= 5))) AND ((checkin_focus_level IS NULL) OR ((checkin_focus_level >= 1) AND (checkin_focus_level <= 5))))),
    CONSTRAINT chk_study_sessions_checkin_time CHECK (((checkin_time_sufficiency IS NULL) OR ((checkin_time_sufficiency)::text = ANY ((ARRAY['TOO_SHORT'::character varying, 'JUST_RIGHT'::character varying, 'TOO_LONG'::character varying])::text[])))),
    CONSTRAINT chk_study_sessions_mode CHECK (((session_mode)::text = ANY ((ARRAY['STANDARD'::character varying, 'MVS'::character varying])::text[]))),
    CONSTRAINT chk_study_sessions_planned_min CHECK ((planned_minutes > 0)),
    CONSTRAINT chk_study_sessions_status CHECK (((status)::text = ANY ((ARRAY['IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'PARTIAL_COMPLETED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT chk_study_sessions_status_ended CHECK (((((status)::text = 'IN_PROGRESS'::text) AND (ended_at IS NULL)) OR (((status)::text <> 'IN_PROGRESS'::text) AND (ended_at IS NOT NULL)))),
    CONSTRAINT chk_study_sessions_times CHECK (((ended_at IS NULL) OR (ended_at >= started_at)))
);


--
-- Name: task_dependencies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_dependencies (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    predecessor_id uuid NOT NULL,
    successor_id uuid NOT NULL,
    roadmap_id uuid NOT NULL,
    is_mandatory boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_task_deps_not_self CHECK ((predecessor_id <> successor_id))
);


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    roadmap_id uuid NOT NULL,
    milestone_id uuid NOT NULL,
    official_schedule_id uuid,
    title character varying(255) NOT NULL,
    description text,
    estimated_minutes integer NOT NULL,
    scheduled_date date,
    scheduled_start timestamp with time zone,
    scheduled_end timestamp with time zone,
    status character varying(20) DEFAULT 'TODO'::character varying NOT NULL,
    completed_at timestamp with time zone,
    reschedule_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    parent_task_id uuid,
    concept_id character varying(120),
    learning_resources_json jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT chk_tasks_completed_at CHECK (((((status)::text = 'COMPLETED'::text) AND (completed_at IS NOT NULL)) OR (((status)::text <> 'COMPLETED'::text) AND (completed_at IS NULL)))),
    CONSTRAINT chk_tasks_estimated_minutes CHECK (((estimated_minutes >= 15) AND (estimated_minutes <= 240))),
    CONSTRAINT chk_tasks_reschedule_count CHECK ((reschedule_count >= 0)),
    CONSTRAINT chk_tasks_resources_json CHECK ((jsonb_typeof(learning_resources_json) = 'array'::text)),
    CONSTRAINT chk_tasks_scheduled_time_order CHECK ((((scheduled_start IS NULL) AND (scheduled_end IS NULL)) OR ((scheduled_start IS NOT NULL) AND (scheduled_end IS NOT NULL) AND (scheduled_end > scheduled_start)))),
    CONSTRAINT chk_tasks_status CHECK (((status)::text = ANY ((ARRAY['TODO'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(100) NOT NULL,
    timezone character varying(50) DEFAULT 'Asia/Ho_Chi_Minh'::character varying NOT NULL,
    role character varying(20) DEFAULT 'LEARNER'::character varying NOT NULL,
    tier character varying(20) DEFAULT 'FREE'::character varying NOT NULL,
    is_locked boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_users_role CHECK (((role)::text = ANY ((ARRAY['LEARNER'::character varying, 'ADMIN'::character varying])::text[]))),
    CONSTRAINT chk_users_tier CHECK (((tier)::text = ANY ((ARRAY['FREE'::character varying, 'PREMIUM'::character varying])::text[])))
);


--
-- Name: webcal_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webcal_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    oauth_refresh_token_encrypted text,
    external_calendar_id character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    last_used_at timestamp with time zone,
    rotated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_webcal_tokens_hash CHECK (((token_hash)::text ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: workflow_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_runs (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    goal_id uuid,
    roadmap_id uuid,
    workflow_type character varying(40) NOT NULL,
    current_step character varying(60) NOT NULL,
    status character varying(25) DEFAULT 'RUNNING'::character varying NOT NULL,
    context_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    error_detail text,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    paused_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_workflow_runs_snapshot CHECK ((jsonb_typeof(context_snapshot) = 'object'::text)),
    CONSTRAINT chk_workflow_runs_status CHECK (((status)::text = ANY ((ARRAY['RUNNING'::character varying, 'PAUSED_WAITING_USER'::character varying, 'COMPLETED'::character varying, 'FAILED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT chk_workflow_runs_type CHECK (((workflow_type)::text = ANY ((ARRAY['PLAN_CREATION'::character varying, 'SCHEDULE_GENERATION'::character varying, 'OVERDUE_RECOVERY'::character varying, 'WEEKLY_REVIEW'::character varying, 'CONTINUOUS_LEARNING'::character varying])::text[])))
);


--
-- Name: workflow_step_executions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_step_executions (
    id uuid NOT NULL,
    workflow_run_id uuid NOT NULL,
    step_name character varying(60) NOT NULL,
    step_order smallint NOT NULL,
    status character varying(25) DEFAULT 'RUNNING'::character varying NOT NULL,
    input_summary jsonb DEFAULT '{}'::jsonb NOT NULL,
    output_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    ai_usage_log_id uuid,
    retry_count smallint DEFAULT '0'::smallint NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT chk_workflow_steps_input_json CHECK ((jsonb_typeof(input_summary) = 'object'::text)),
    CONSTRAINT chk_workflow_steps_order CHECK ((step_order >= 1)),
    CONSTRAINT chk_workflow_steps_output_json CHECK ((jsonb_typeof(output_payload) = 'object'::text)),
    CONSTRAINT chk_workflow_steps_retry CHECK ((retry_count >= 0)),
    CONSTRAINT chk_workflow_steps_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'RUNNING'::character varying, 'WAITING_USER'::character varying, 'COMPLETED'::character varying, 'FAILED'::character varying, 'SKIPPED'::character varying])::text[])))
);


--
-- Name: ai_quota_reservations ai_quota_reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_quota_reservations
    ADD CONSTRAINT ai_quota_reservations_pkey PRIMARY KEY (id);


--
-- Name: ai_quotas ai_quotas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_quotas
    ADD CONSTRAINT ai_quotas_pkey PRIMARY KEY (id);


--
-- Name: ai_reviews ai_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_reviews
    ADD CONSTRAINT ai_reviews_pkey PRIMARY KEY (id);


--
-- Name: ai_usage_logs ai_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_usage_logs
    ADD CONSTRAINT ai_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: availabilities availabilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availabilities
    ADD CONSTRAINT availabilities_pkey PRIMARY KEY (id);


--
-- Name: availability_slots availability_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availability_slots
    ADD CONSTRAINT availability_slots_pkey PRIMARY KEY (id);


--
-- Name: calendar_connections calendar_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_connections
    ADD CONSTRAINT calendar_connections_pkey PRIMARY KEY (id);


--
-- Name: concept_prerequisites concept_prerequisites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concept_prerequisites
    ADD CONSTRAINT concept_prerequisites_pkey PRIMARY KEY (source_concept_id, prerequisite_concept_id);


--
-- Name: goals goals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goals
    ADD CONSTRAINT goals_pkey PRIMARY KEY (id);


--
-- Name: knowledge_chunks knowledge_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_chunks
    ADD CONSTRAINT knowledge_chunks_pkey PRIMARY KEY (id);


--
-- Name: knowledge_sources knowledge_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_sources
    ADD CONSTRAINT knowledge_sources_pkey PRIMARY KEY (id);


--
-- Name: learner_concept_masteries learner_concept_masteries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_concept_masteries
    ADD CONSTRAINT learner_concept_masteries_pkey PRIMARY KEY (id);


--
-- Name: learner_memory_items learner_memory_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_memory_items
    ADD CONSTRAINT learner_memory_items_pkey PRIMARY KEY (id);


--
-- Name: learner_profiles learner_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_profiles
    ADD CONSTRAINT learner_profiles_pkey PRIMARY KEY (id);


--
-- Name: learning_concepts learning_concepts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learning_concepts
    ADD CONSTRAINT learning_concepts_pkey PRIMARY KEY (concept_id);


--
-- Name: milestone_proofs milestone_proofs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestone_proofs
    ADD CONSTRAINT milestone_proofs_pkey PRIMARY KEY (id);


--
-- Name: milestones milestones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestones
    ADD CONSTRAINT milestones_pkey PRIMARY KEY (id);


--
-- Name: official_schedules official_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.official_schedules
    ADD CONSTRAINT official_schedules_pkey PRIMARY KEY (id);


--
-- Name: outbox_events outbox_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbox_events
    ADD CONSTRAINT outbox_events_pkey PRIMARY KEY (id);


--
-- Name: pause_records pause_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pause_records
    ADD CONSTRAINT pause_records_pkey PRIMARY KEY (id);


--
-- Name: payment_transactions payment_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT payment_transactions_pkey PRIMARY KEY (id);


--
-- Name: processed_events processed_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_events
    ADD CONSTRAINT processed_events_pkey PRIMARY KEY (event_id, handler_name);


--
-- Name: roadmaps roadmaps_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roadmaps
    ADD CONSTRAINT roadmaps_pkey PRIMARY KEY (id);


--
-- Name: schedule_blocks schedule_blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_blocks
    ADD CONSTRAINT schedule_blocks_pkey PRIMARY KEY (id);


--
-- Name: schedule_change_logs schedule_change_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_change_logs
    ADD CONSTRAINT schedule_change_logs_pkey PRIMARY KEY (id);


--
-- Name: schedule_proposals schedule_proposals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_proposals
    ADD CONSTRAINT schedule_proposals_pkey PRIMARY KEY (id);


--
-- Name: session_tasks session_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT session_tasks_pkey PRIMARY KEY (id);


--
-- Name: study_notes study_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_notes
    ADD CONSTRAINT study_notes_pkey PRIMARY KEY (id);


--
-- Name: study_sessions study_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions
    ADD CONSTRAINT study_sessions_pkey PRIMARY KEY (id);


--
-- Name: task_dependencies task_dependencies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT task_dependencies_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: ai_quotas uq_ai_quotas_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_quotas
    ADD CONSTRAINT uq_ai_quotas_user_id UNIQUE (user_id);


--
-- Name: availabilities uq_availabilities_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availabilities
    ADD CONSTRAINT uq_availabilities_user_id UNIQUE (user_id);


--
-- Name: calendar_connections uq_calendar_connections_user_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_connections
    ADD CONSTRAINT uq_calendar_connections_user_provider UNIQUE (user_id, provider);


--
-- Name: knowledge_chunks uq_knowledge_chunks_source_idx; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_chunks
    ADD CONSTRAINT uq_knowledge_chunks_source_idx UNIQUE (source_id, chunk_index);


--
-- Name: knowledge_sources uq_knowledge_sources_owner_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_sources
    ADD CONSTRAINT uq_knowledge_sources_owner_hash UNIQUE (user_id, goal_id, content_hash);


--
-- Name: learner_concept_masteries uq_learner_mastery_user_concept; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_concept_masteries
    ADD CONSTRAINT uq_learner_mastery_user_concept UNIQUE (user_id, concept_key);


--
-- Name: learner_memory_items uq_learner_memory_user_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_memory_items
    ADD CONSTRAINT uq_learner_memory_user_key UNIQUE (user_id, memory_key);


--
-- Name: learner_profiles uq_learner_profiles_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_profiles
    ADD CONSTRAINT uq_learner_profiles_user_id UNIQUE (user_id);


--
-- Name: milestones uq_milestones_roadmap_seq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestones
    ADD CONSTRAINT uq_milestones_roadmap_seq UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: official_schedules uq_official_schedules_roadmap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.official_schedules
    ADD CONSTRAINT uq_official_schedules_roadmap UNIQUE (roadmap_id);


--
-- Name: payment_transactions uq_payment_transactions_ref; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT uq_payment_transactions_ref UNIQUE (transaction_ref);


--
-- Name: session_tasks uq_session_tasks_session_task; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT uq_session_tasks_session_task UNIQUE (session_id, task_id);


--
-- Name: study_notes uq_study_notes_session_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_notes
    ADD CONSTRAINT uq_study_notes_session_type UNIQUE (session_id, note_type);


--
-- Name: task_dependencies uq_task_deps_pair; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT uq_task_deps_pair UNIQUE (predecessor_id, successor_id);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: webcal_tokens uq_webcal_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webcal_tokens
    ADD CONSTRAINT uq_webcal_tokens_token_hash UNIQUE (token_hash);


--
-- Name: webcal_tokens uq_webcal_tokens_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webcal_tokens
    ADD CONSTRAINT uq_webcal_tokens_user_id UNIQUE (user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: webcal_tokens webcal_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webcal_tokens
    ADD CONSTRAINT webcal_tokens_pkey PRIMARY KEY (id);


--
-- Name: workflow_runs workflow_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_pkey PRIMARY KEY (id);


--
-- Name: workflow_step_executions workflow_step_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_step_executions
    ADD CONSTRAINT workflow_step_executions_pkey PRIMARY KEY (id);


--
-- Name: idx_ai_quota_reservations_quota_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_quota_reservations_quota_id ON public.ai_quota_reservations USING btree (quota_id);


--
-- Name: idx_ai_reviews_roadmap_cycle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_reviews_roadmap_cycle ON public.ai_reviews USING btree (roadmap_id, review_cycle, generated_at DESC);


--
-- Name: idx_ai_reviews_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_reviews_user_id ON public.ai_reviews USING btree (user_id);


--
-- Name: idx_ai_usage_logs_user_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_usage_logs_user_action ON public.ai_usage_logs USING btree (user_id, action_type, created_at DESC);


--
-- Name: idx_avail_slots_availability_day; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_avail_slots_availability_day ON public.availability_slots USING btree (availability_id, day_of_week);


--
-- Name: idx_calendar_connections_channel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_calendar_connections_channel ON public.calendar_connections USING btree (channel_id) WHERE (channel_id IS NOT NULL);


--
-- Name: idx_calendar_connections_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_calendar_connections_user_status ON public.calendar_connections USING btree (user_id, sync_status);


--
-- Name: idx_concept_prerequisites_prereq; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_concept_prerequisites_prereq ON public.concept_prerequisites USING btree (prerequisite_concept_id);


--
-- Name: idx_concept_prerequisites_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_concept_prerequisites_source ON public.concept_prerequisites USING btree (source_concept_id);


--
-- Name: idx_goals_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_goals_user_id ON public.goals USING btree (user_id);


--
-- Name: idx_knowledge_chunks_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_chunks_embedding_hnsw ON public.knowledge_chunks USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: idx_knowledge_chunks_goal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_chunks_goal_id ON public.knowledge_chunks USING btree (goal_id);


--
-- Name: idx_knowledge_chunks_search_vector; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_chunks_search_vector ON public.knowledge_chunks USING gin (search_vector);


--
-- Name: idx_knowledge_sources_goal_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_sources_goal_status ON public.knowledge_sources USING btree (goal_id, ingestion_status);


--
-- Name: idx_learner_memory_context; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_learner_memory_context ON public.learner_memory_items USING btree (user_id, status, category);


--
-- Name: idx_learning_concepts_domain_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_learning_concepts_domain_level ON public.learning_concepts USING btree (domain, difficulty_level, verification_status);


--
-- Name: idx_milestone_proofs_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_milestone_proofs_owner ON public.milestone_proofs USING btree (user_id, milestone_id);


--
-- Name: idx_outbox_events_aggregate; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outbox_events_aggregate ON public.outbox_events USING btree (aggregate_type, aggregate_id);


--
-- Name: idx_outbox_events_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outbox_events_pending ON public.outbox_events USING btree (created_at) WHERE ((status)::text = 'PENDING'::text);


--
-- Name: idx_pause_records_roadmap_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pause_records_roadmap_id ON public.pause_records USING btree (roadmap_id);


--
-- Name: idx_payment_transactions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payment_transactions_status ON public.payment_transactions USING btree (status, created_at DESC);


--
-- Name: idx_payment_transactions_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payment_transactions_user_created ON public.payment_transactions USING btree (user_id, created_at DESC);


--
-- Name: idx_quota_reservations_cleanup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_reservations_cleanup ON public.ai_quota_reservations USING btree (expires_at) WHERE ((status)::text = 'RESERVED'::text);


--
-- Name: idx_quota_reservations_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_reservations_user_status ON public.ai_quota_reservations USING btree (user_id, status, created_at DESC);


--
-- Name: idx_roadmaps_goal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_roadmaps_goal_id ON public.roadmaps USING btree (goal_id);


--
-- Name: idx_roadmaps_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_roadmaps_user_status ON public.roadmaps USING btree (user_id, status);


--
-- Name: idx_sched_change_logs_roadmap_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sched_change_logs_roadmap_created ON public.schedule_change_logs USING btree (roadmap_id, created_at DESC);


--
-- Name: idx_sched_change_logs_schedule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sched_change_logs_schedule_id ON public.schedule_change_logs USING btree (schedule_id) WHERE (schedule_id IS NOT NULL);


--
-- Name: idx_sched_change_logs_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sched_change_logs_task_id ON public.schedule_change_logs USING btree (task_id) WHERE (task_id IS NOT NULL);


--
-- Name: idx_sched_change_logs_trigger; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sched_change_logs_trigger ON public.schedule_change_logs USING btree (trigger_type, created_at DESC);


--
-- Name: idx_schedule_blocks_external_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedule_blocks_external_event ON public.schedule_blocks USING btree (external_calendar_event_id) WHERE (external_calendar_event_id IS NOT NULL);


--
-- Name: idx_schedule_blocks_roadmap_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedule_blocks_roadmap_date ON public.schedule_blocks USING btree (roadmap_id, block_date, start_time);


--
-- Name: idx_schedule_blocks_schedule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedule_blocks_schedule_id ON public.schedule_blocks USING btree (official_schedule_id);


--
-- Name: idx_schedule_blocks_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedule_blocks_task_id ON public.schedule_blocks USING btree (task_id) WHERE (task_id IS NOT NULL);


--
-- Name: idx_schedule_proposals_roadmap_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedule_proposals_roadmap_status ON public.schedule_proposals USING btree (roadmap_id, status);


--
-- Name: idx_schedule_proposals_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedule_proposals_user_id ON public.schedule_proposals USING btree (user_id);


--
-- Name: idx_session_tasks_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_tasks_session_id ON public.session_tasks USING btree (session_id);


--
-- Name: idx_session_tasks_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_tasks_task_id ON public.session_tasks USING btree (task_id);


--
-- Name: idx_study_notes_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_study_notes_task_id ON public.study_notes USING btree (task_id);


--
-- Name: idx_study_notes_user_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_study_notes_user_session ON public.study_notes USING btree (user_id, session_id);


--
-- Name: idx_study_sessions_heartbeat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_study_sessions_heartbeat ON public.study_sessions USING btree (last_heartbeat_at) WHERE ((status)::text = 'IN_PROGRESS'::text);


--
-- Name: idx_study_sessions_roadmap_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_study_sessions_roadmap_started ON public.study_sessions USING btree (roadmap_id, started_at DESC);


--
-- Name: idx_study_sessions_user_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_study_sessions_user_started ON public.study_sessions USING btree (user_id, started_at DESC);


--
-- Name: idx_task_deps_predecessor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_task_deps_predecessor ON public.task_dependencies USING btree (predecessor_id);


--
-- Name: idx_task_deps_roadmap; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_task_deps_roadmap ON public.task_dependencies USING btree (roadmap_id);


--
-- Name: idx_task_deps_successor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_task_deps_successor ON public.task_dependencies USING btree (successor_id);


--
-- Name: idx_tasks_concept_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_concept_id ON public.tasks USING btree (concept_id);


--
-- Name: idx_tasks_milestone_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_milestone_id ON public.tasks USING btree (milestone_id);


--
-- Name: idx_tasks_official_schedule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_official_schedule_id ON public.tasks USING btree (official_schedule_id);


--
-- Name: idx_tasks_overdue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_overdue ON public.tasks USING btree (scheduled_date) WHERE (((status)::text = ANY ((ARRAY['TODO'::character varying, 'IN_PROGRESS'::character varying])::text[])) AND (scheduled_date IS NOT NULL));


--
-- Name: idx_tasks_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_parent_id ON public.tasks USING btree (parent_task_id);


--
-- Name: idx_tasks_roadmap_scheduled_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_roadmap_scheduled_date ON public.tasks USING btree (roadmap_id, scheduled_date);


--
-- Name: idx_tasks_scheduled_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tasks_scheduled_start ON public.tasks USING btree (scheduled_start) WHERE (scheduled_start IS NOT NULL);


--
-- Name: idx_workflow_runs_goal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_runs_goal_id ON public.workflow_runs USING btree (goal_id);


--
-- Name: idx_workflow_runs_roadmap_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_runs_roadmap_type ON public.workflow_runs USING btree (roadmap_id, workflow_type);


--
-- Name: idx_workflow_runs_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_runs_user_status ON public.workflow_runs USING btree (user_id, status, updated_at);


--
-- Name: idx_workflow_step_executions_ai_log_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_step_executions_ai_log_id ON public.workflow_step_executions USING btree (ai_usage_log_id);


--
-- Name: idx_workflow_step_executions_run_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflow_step_executions_run_order ON public.workflow_step_executions USING btree (workflow_run_id, step_order);


--
-- Name: uq_ai_reviews_milestone; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ai_reviews_milestone ON public.ai_reviews USING btree (roadmap_id, milestone_id) WHERE ((review_cycle)::text = 'MILESTONE'::text);


--
-- Name: uq_ai_reviews_weekly; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ai_reviews_weekly ON public.ai_reviews USING btree (roadmap_id, period_start, period_end) WHERE ((review_cycle)::text = 'WEEKLY'::text);


--
-- Name: uq_ai_usage_logs_idempotency_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ai_usage_logs_idempotency_key ON public.ai_usage_logs USING btree (idempotency_key) WHERE (idempotency_key IS NOT NULL);


--
-- Name: uq_schedule_proposals_roadmap_draft; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_schedule_proposals_roadmap_draft ON public.schedule_proposals USING btree (roadmap_id) WHERE ((status)::text = 'DRAFT'::text);


--
-- Name: uq_study_sessions_user_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_study_sessions_user_active ON public.study_sessions USING btree (user_id) WHERE ((status)::text = 'IN_PROGRESS'::text);


--
-- Name: uq_users_lower_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_users_lower_email ON public.users USING btree (lower((email)::text));


--
-- Name: ai_quotas trg_ai_quotas_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_ai_quotas_updated_at BEFORE UPDATE ON public.ai_quotas FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: ai_reviews trg_ai_reviews_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_ai_reviews_updated_at BEFORE UPDATE ON public.ai_reviews FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: availabilities trg_availabilities_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_availabilities_updated_at BEFORE UPDATE ON public.availabilities FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: availability_slots trg_availability_slots_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_availability_slots_updated_at BEFORE UPDATE ON public.availability_slots FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: calendar_connections trg_calendar_connections_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_calendar_connections_updated_at BEFORE UPDATE ON public.calendar_connections FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: goals trg_goals_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_goals_updated_at BEFORE UPDATE ON public.goals FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: learner_profiles trg_learner_profiles_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_learner_profiles_updated_at BEFORE UPDATE ON public.learner_profiles FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: milestones trg_milestones_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_milestones_updated_at BEFORE UPDATE ON public.milestones FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: official_schedules trg_official_schedules_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_official_schedules_updated_at BEFORE UPDATE ON public.official_schedules FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: pause_records trg_pause_records_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pause_records_updated_at BEFORE UPDATE ON public.pause_records FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: payment_transactions trg_payment_transactions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_transactions_updated_at BEFORE UPDATE ON public.payment_transactions FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: roadmaps trg_roadmaps_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_roadmaps_updated_at BEFORE UPDATE ON public.roadmaps FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: schedule_blocks trg_schedule_blocks_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_schedule_blocks_updated_at BEFORE UPDATE ON public.schedule_blocks FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: schedule_proposals trg_schedule_proposals_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_schedule_proposals_updated_at BEFORE UPDATE ON public.schedule_proposals FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: session_tasks trg_session_tasks_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_session_tasks_updated_at BEFORE UPDATE ON public.session_tasks FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: study_notes trg_study_notes_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_study_notes_updated_at BEFORE UPDATE ON public.study_notes FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: study_sessions trg_study_sessions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_study_sessions_updated_at BEFORE UPDATE ON public.study_sessions FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: tasks trg_tasks_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON public.tasks FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: users trg_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: webcal_tokens trg_webcal_tokens_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_webcal_tokens_updated_at BEFORE UPDATE ON public.webcal_tokens FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: ai_quotas ai_quotas_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_quotas
    ADD CONSTRAINT ai_quotas_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: availabilities availabilities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availabilities
    ADD CONSTRAINT availabilities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: availability_slots availability_slots_availability_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availability_slots
    ADD CONSTRAINT availability_slots_availability_id_fkey FOREIGN KEY (availability_id) REFERENCES public.availabilities(id) ON DELETE CASCADE;


--
-- Name: ai_quota_reservations fk_ai_quota_res_quota; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_quota_reservations
    ADD CONSTRAINT fk_ai_quota_res_quota FOREIGN KEY (quota_id) REFERENCES public.ai_quotas(id) ON DELETE CASCADE;


--
-- Name: ai_quota_reservations fk_ai_quota_res_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_quota_reservations
    ADD CONSTRAINT fk_ai_quota_res_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: ai_reviews fk_ai_reviews_milestone; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_reviews
    ADD CONSTRAINT fk_ai_reviews_milestone FOREIGN KEY (milestone_id) REFERENCES public.milestones(id) ON DELETE CASCADE;


--
-- Name: ai_reviews fk_ai_reviews_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_reviews
    ADD CONSTRAINT fk_ai_reviews_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: ai_reviews fk_ai_reviews_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_reviews
    ADD CONSTRAINT fk_ai_reviews_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: ai_usage_logs fk_ai_usage_logs_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_usage_logs
    ADD CONSTRAINT fk_ai_usage_logs_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: calendar_connections fk_calendar_connections_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.calendar_connections
    ADD CONSTRAINT fk_calendar_connections_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: concept_prerequisites fk_concept_prerequisites_prereq; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concept_prerequisites
    ADD CONSTRAINT fk_concept_prerequisites_prereq FOREIGN KEY (prerequisite_concept_id) REFERENCES public.learning_concepts(concept_id) ON DELETE CASCADE;


--
-- Name: concept_prerequisites fk_concept_prerequisites_source; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concept_prerequisites
    ADD CONSTRAINT fk_concept_prerequisites_source FOREIGN KEY (source_concept_id) REFERENCES public.learning_concepts(concept_id) ON DELETE CASCADE;


--
-- Name: goals fk_goals_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goals
    ADD CONSTRAINT fk_goals_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: learner_profiles fk_learner_profiles_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_profiles
    ADD CONSTRAINT fk_learner_profiles_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: milestones fk_milestones_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestones
    ADD CONSTRAINT fk_milestones_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: official_schedules fk_official_schedules_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.official_schedules
    ADD CONSTRAINT fk_official_schedules_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: pause_records fk_pause_records_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pause_records
    ADD CONSTRAINT fk_pause_records_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: payment_transactions fk_payment_transactions_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT fk_payment_transactions_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: roadmaps fk_roadmaps_goal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roadmaps
    ADD CONSTRAINT fk_roadmaps_goal FOREIGN KEY (goal_id) REFERENCES public.goals(id) ON DELETE CASCADE;


--
-- Name: roadmaps fk_roadmaps_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roadmaps
    ADD CONSTRAINT fk_roadmaps_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: schedule_change_logs fk_sched_change_logs_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_change_logs
    ADD CONSTRAINT fk_sched_change_logs_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: schedule_change_logs fk_sched_change_logs_schedule; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_change_logs
    ADD CONSTRAINT fk_sched_change_logs_schedule FOREIGN KEY (schedule_id) REFERENCES public.official_schedules(id) ON DELETE SET NULL;


--
-- Name: schedule_change_logs fk_sched_change_logs_task; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_change_logs
    ADD CONSTRAINT fk_sched_change_logs_task FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE SET NULL;


--
-- Name: schedule_blocks fk_schedule_blocks_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_blocks
    ADD CONSTRAINT fk_schedule_blocks_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: schedule_blocks fk_schedule_blocks_schedule; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_blocks
    ADD CONSTRAINT fk_schedule_blocks_schedule FOREIGN KEY (official_schedule_id) REFERENCES public.official_schedules(id) ON DELETE CASCADE;


--
-- Name: schedule_blocks fk_schedule_blocks_task; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_blocks
    ADD CONSTRAINT fk_schedule_blocks_task FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: schedule_proposals fk_schedule_proposals_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_proposals
    ADD CONSTRAINT fk_schedule_proposals_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: schedule_proposals fk_schedule_proposals_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_proposals
    ADD CONSTRAINT fk_schedule_proposals_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_tasks fk_session_tasks_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT fk_session_tasks_session FOREIGN KEY (session_id) REFERENCES public.study_sessions(id) ON DELETE CASCADE;


--
-- Name: session_tasks fk_session_tasks_task; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT fk_session_tasks_task FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE RESTRICT;


--
-- Name: study_notes fk_study_notes_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_notes
    ADD CONSTRAINT fk_study_notes_session FOREIGN KEY (session_id) REFERENCES public.study_sessions(id) ON DELETE CASCADE;


--
-- Name: study_notes fk_study_notes_task; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_notes
    ADD CONSTRAINT fk_study_notes_task FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE SET NULL;


--
-- Name: study_notes fk_study_notes_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_notes
    ADD CONSTRAINT fk_study_notes_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: study_sessions fk_study_sessions_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions
    ADD CONSTRAINT fk_study_sessions_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: study_sessions fk_study_sessions_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions
    ADD CONSTRAINT fk_study_sessions_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: task_dependencies fk_task_deps_pred; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT fk_task_deps_pred FOREIGN KEY (predecessor_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: task_dependencies fk_task_deps_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT fk_task_deps_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: task_dependencies fk_task_deps_succ; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_dependencies
    ADD CONSTRAINT fk_task_deps_succ FOREIGN KEY (successor_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- Name: tasks fk_tasks_concept; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT fk_tasks_concept FOREIGN KEY (concept_id) REFERENCES public.learning_concepts(concept_id) ON DELETE SET NULL;


--
-- Name: tasks fk_tasks_milestone; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT fk_tasks_milestone FOREIGN KEY (milestone_id) REFERENCES public.milestones(id) ON DELETE CASCADE;


--
-- Name: tasks fk_tasks_official_schedule; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT fk_tasks_official_schedule FOREIGN KEY (official_schedule_id) REFERENCES public.official_schedules(id) ON DELETE SET NULL;


--
-- Name: tasks fk_tasks_parent; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT fk_tasks_parent FOREIGN KEY (parent_task_id) REFERENCES public.tasks(id) ON DELETE SET NULL;


--
-- Name: tasks fk_tasks_roadmap; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT fk_tasks_roadmap FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: webcal_tokens fk_webcal_tokens_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webcal_tokens
    ADD CONSTRAINT fk_webcal_tokens_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: knowledge_chunks knowledge_chunks_goal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_chunks
    ADD CONSTRAINT knowledge_chunks_goal_id_fkey FOREIGN KEY (goal_id) REFERENCES public.goals(id) ON DELETE CASCADE;


--
-- Name: knowledge_chunks knowledge_chunks_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_chunks
    ADD CONSTRAINT knowledge_chunks_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.knowledge_sources(id) ON DELETE CASCADE;


--
-- Name: knowledge_sources knowledge_sources_goal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_sources
    ADD CONSTRAINT knowledge_sources_goal_id_fkey FOREIGN KEY (goal_id) REFERENCES public.goals(id) ON DELETE CASCADE;


--
-- Name: knowledge_sources knowledge_sources_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_sources
    ADD CONSTRAINT knowledge_sources_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: learner_concept_masteries learner_concept_masteries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_concept_masteries
    ADD CONSTRAINT learner_concept_masteries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: learner_memory_items learner_memory_items_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_memory_items
    ADD CONSTRAINT learner_memory_items_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: milestone_proofs milestone_proofs_milestone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestone_proofs
    ADD CONSTRAINT milestone_proofs_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES public.milestones(id) ON DELETE CASCADE;


--
-- Name: milestone_proofs milestone_proofs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestone_proofs
    ADD CONSTRAINT milestone_proofs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: processed_events processed_events_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_events
    ADD CONSTRAINT processed_events_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.outbox_events(id) ON DELETE CASCADE;


--
-- Name: workflow_runs workflow_runs_goal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_goal_id_fkey FOREIGN KEY (goal_id) REFERENCES public.goals(id) ON DELETE CASCADE;


--
-- Name: workflow_runs workflow_runs_roadmap_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_roadmap_id_fkey FOREIGN KEY (roadmap_id) REFERENCES public.roadmaps(id) ON DELETE CASCADE;


--
-- Name: workflow_runs workflow_runs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: workflow_step_executions workflow_step_executions_ai_usage_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_step_executions
    ADD CONSTRAINT workflow_step_executions_ai_usage_log_id_fkey FOREIGN KEY (ai_usage_log_id) REFERENCES public.ai_usage_logs(id) ON DELETE SET NULL;


--
-- Name: workflow_step_executions workflow_step_executions_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_step_executions
    ADD CONSTRAINT workflow_step_executions_workflow_run_id_fkey FOREIGN KEY (workflow_run_id) REFERENCES public.workflow_runs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ksecOrFoe4YIR9lYCw8RygNUJnINrwfLr6TAjvZMbPBevhAGy1DVOduAagc3Db9

