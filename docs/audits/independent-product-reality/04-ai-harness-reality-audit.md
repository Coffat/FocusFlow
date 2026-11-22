# 04 — AI Harness Reality Audit (Phase 4)

- **Scope**: Toàn bộ Shared AI Harness Runtime (`shared_kernel`, `planning`, `evaluation`), phân tách rõ ràng giữa: (1) Deterministic unit tests, (2) Mock/Stub provider integration tests, (3) Real external model API tests, và (4) End-to-end user workflows.

---

## 1. Architecture & Component Reality Matrix

| Component | Implementation Reality | Key Files | Gaps / Findings |
|---|---|---|---|
| **`LLMProviderPort` & `LiteLLMAdapter`** | **REAL** cho Gemini (`google-genai` SDK + thinking levels + fallback + tool loop + semaphore) | `shared_kernel/application/llm_port.py:341`, `shared_kernel/infrastructure/external_ai/litellm_adapter.py:413-1335` | (1) Gemini **bắt buộc `LLM_BASE_URL` (Cobhub proxy)** (`:435-440`); (2) Non-Gemini (`openai`/`anthropic`/`ollama`, `:1218-1296`) **bỏ qua** tools, fallbacks, semaphore; (3) **Không có `MockLLMAdapter`** runtime (`:428-434` từ chối `mock` dù `AGENTS.md` quảng bá); (4) `stream_structured()` (`:1312`) có 0 caller. |
| **Circuit Breaker (`CircuitBreakingLLMProvider`)** | **REAL** (Redis-backed) nhưng **KHÔNG CHẠY MẶC ĐỊNH** | `circuit_breaker.py:122-234`, `planning/presentation/deps.py:305-322`, `evaluation/presentation/deps.py:114-115` | `ai_harness_v2_enabled=False` mặc định (`config.py:113`) tắt circuit breaker ở Planning; Evaluation không bọc circuit breaker; mất Redis gây crash unhandled `ConnectionError` (`AUD-HIGH-08`). |
| **Prompt Registry** | **REAL** (SemVer + SHA-256 prompt/schema checksum) | `shared_kernel/application/harness/prompt_registry.py:25-118` | Không phát hiện lỗ hổng. |
| **Context Builder** | **REAL** (5 layers, token budget, PII key rejection, marker escaping) | `shared_kernel/application/harness/context_engine.py:45-311`, `roadmap_context_builder.py` | Hoạt động tốt. |
| **Tool / Skill Layer** | **REAL** (stage-scoped, JSON Schema args, timeout, truncation, audit log) | `shared_kernel/application/harness/tool_registry.py:190-338` | Chỉ hoạt động trên nhánh Gemini; bị bỏ qua trên non-Gemini (`AUD-MED-11`). |
| **3-Tier Validation Gate** | **REAL** (Tier 1 Schema → Tier 2 Deterministic `SpatioTemporalRuleEngine` + `DagCycleValidator` → Tier 3 LLM-as-a-Judge) | `planning/application/services/validation_gate/{orchestrator,tier1_schema,tier2_deterministic,tier3_judge}.py` | Kiểm chứng vượt ra ngoài JSON schema (kiểm DAG, hard conflicts, task coverage, feasibility). |
| **Knowledge Retrieval (RAG)** | **REAL CODE, UNCONFIGURED IN STAGING** (pgvector cosine + `websearch_to_tsquery` + RRF + `<untrusted_knowledge_context>`) | `embedding_adapter.py:37-206`, `knowledge_source_repository.py:84-122`, `roadmap_context_builder.py:737-754` | `rag_embedding_configured: false` trên staging (thiếu `EMBEDDING_API_KEY`); SSRF DNS rebinding trên `SafeUrlFetcher` (`AUD-CRIT-03`); upload không kiểm magic bytes (`AUD-HIGH-06`). |
| **Quota Lifecycle (`RESERVE → COMMIT/RELEASE/EXPIRE`)** | **REAL IN PLANNING; COMPLETELY BYPASSED IN EVALUATION** | `quota_facade_adapter.py:138-460`, `evaluation/presentation/deps.py:168-229`, `execution_manager.py:291,298` | **CRITICAL (`AUD-CRIT-04`)**: Prove Mode & Weekly Review không truyền `quota_port` → `_NoOpQuotaAdapter` → 0 credit bị trừ, 0 `ai_usage_logs`. **Đã tái hiện trực tiếp trên staging live.** |
| **Memory Extraction & Observability** | **REAL** (`WorkflowRun`, `WorkflowStepExecution`, `LearnerMemoryItem` chỉ ghi sau Prove Mode verified / Weekly Review) | `execution_manager.py:274-963`, `learner_profile_query_adapter.py:135-230` | `ai_usage_logs` thiếu toàn bộ call từ `evaluation`. |
| **2-Stage SSE & Taskiq Recovery** | **REAL BACKEND; MISSING FE REFRESH RECOVERY** | `sse/job_store.py`, `ai-sse.service.ts:82-245`, `roadmap.service.ts:1397-1640` | Refresh trình duyệt khi job AI 20–55s đang chạy sẽ mất UI tiến độ SSE (`AUD-MED-07`); `InMemorySseJobStore` rò rỉ bộ nhớ (`AUD-MED-08`). |

---

## 2. Verification Level Classification (No Conflation of Mock vs Live)

| AI Workflow | 1. Deterministic Unit | 2. Mock/Stub Integration | 3. Real External Model API | 4. Live E2E User Workflow | Observed Quality vs SRS |
|---|---|---|---|---|---|
| **Goal Clarification** | PASS (`test_ai_roadmap_clarification.py`) | PASS (`StubLLMAdapter`) | **VERIFIED LIVE** (Gemini via Cobhub, 8.8s) | **VERIFIED LIVE** (User A + Playwright) | 3 câu hỏi tiếng Việt sát domain PG16, có nhận diện lỗ hổng kiến thức; hỗ trợ Vòng 2. |
| **Milestone Generation** | PASS (Tier 1/2/3 tests) | PASS (`eval_runner.py` 18/6/12 goals) | **VERIFIED LIVE** (21.3s, 4 SSE events) | **VERIFIED LIVE** (DB `milestones=4`, `ai_quota_reservations=COMMITTED`) | 4 milestone tiếng Việt mạch lạc (`EXPLAIN ANALYZE` → `B-Tree` → `GIN/GiST` → `Join/Tuning`), đúng SRS. |
| **Schedule Proposal Generation** | PASS (`SpatioTemporalRuleEngine`, `golden_ai_workflows_v2.py` 120 synthetic) | PASS (`StubLLMAdapter`) | **VERIFIED LIVE** (31.8s, 9 SSE events) | **VERIFIED LIVE** (lưu `DRAFT` → `Apply` → 13 tasks, 21 blocks) | Đúng bất biến AI `DRAFT` vs `OfficialSchedule`; tôn trọng khung giờ 19:00–21:00. |
| **Prove Mode Challenge Gen** | PASS | PASS | **VERIFIED LIVE** (5.4s, 3 câu PG16) | **PARTIAL** — Chạy blocking đồng bộ trong endpoint `202` và **bypass quota** (`AUD-CRIT-04`) | Câu hỏi đúng chủ đề milestone, nhưng kiến trúc không trừ quota & không đẩy job bất đồng bộ thực sự. |
| **Prove Mode Grading** | PASS (fail-closed `NEEDS_REVIEW`) | PASS | **DEGRADED LIVE** (7.5s → `NEEDS_REVIEW`, `score=0`) | **DEFECTIVE LIVE** — Bypass quota (`AUD-CRIT-04`) + grader rơi vào fallback (`AUD-MED-12`) | Fail-closed an toàn (không cấp verified sai) nhưng UX thất bại trên câu trả lời hợp lệ ở live run. |
| **Weekly Review** | PASS (`QuantitativeFaithfulnessValidator`) | PASS | **NOT VERIFIED LIVE** (chỉ có unit/mock) | **NOT VERIFIED LIVE** (biết chắc bypass quota qua mã nguồn `evaluation/presentation/deps.py:209-229`) | Kiểm trung thực số liệu định lượng bằng code tất định, nhưng bypass quota. |
| **SRL Adaptation / Overdue Revise** | PASS | PASS | **NOT VERIFIED LIVE** | **NOT VERIFIED LIVE** (code & mock integration verified) | Chưa có bài kiểm chứng live với LLM thật cho nhánh overdue revise. |
| **RAG Knowledge Ingestion** | PASS | PASS | **NOT VERIFIED LIVE** (`rag_embedding_configured=false`, test `live_embedding` deselected) | **NOT VERIFIED LIVE** | Thiếu `EMBEDDING_API_KEY` trong staging; cần vá SSRF & magic-byte upload trước khi bật. |

---

## 3. Critical AI Findings Summary

1. **`AUD-CRIT-04` (Evaluation Quota Bypass — LIVE REPRODUCED)**: `evaluation/presentation/deps.py:168-229` không truyền `quota_port` → Prove Mode & Weekly Review gọi Gemini thật miễn phí, không giới hạn, không ghi `ai_usage_logs`.
2. **`AUD-HIGH-08` (Circuit Breaker Disabled / Unwired / Redis-Fragile)**: Tắt mặc định (`ai_harness_v2_enabled=False`), thiếu hoàn toàn ở `evaluation`, và ném lỗi `ConnectionError` chưa bắt khi mất Redis.
3. **`AUD-MED-11` (Offline Mock Contradiction & Cobhub Lock-in)**: `LLM_PROVIDER=mock` bị từ chối ở runtime; Gemini bắt buộc `LLM_BASE_URL`; non-Gemini bỏ qua tool-calling/fallback/semaphore.
4. **`AUD-MED-12` (Prove Mode Live Grader Fallback & Sync 202 Blocking)**: `generate-jobs` chặn ~5.4s trả thẳng `READY`; `submit` rơi vào `NEEDS_REVIEW`/`score=0` trên môi trường staging live (cần điều tra nguyên nhân prompt/schema trả về từ Cobhub gateway cho grader).
