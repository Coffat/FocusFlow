# Phân Nhóm 150 Files trong Checkpoint `cd5989b` để Chia PR

- **Commit nguồn:** `cd5989b` (`chore: checkpoint pre-cobhub-hardening baseline`)
- **Tổng số file:** **150 files** (xác minh bằng `git diff-tree --no-commit-id --name-status -r cd5989b`)
- **Kiểm tra secret/PII trong lịch sử `cd5989b~1..HEAD`:** 0 file `.env` thật (chỉ có `.env.example`); không có key/secret/PII thật bị lộ (`AIza...` chỉ xuất hiện 1 lần làm chuỗi giả lập trong `test_embedding_adapter.py`; `antigravity-proxy-key` chỉ là placeholder cho local proxy/test).

## Tóm tắt Phân nhóm PR

| Nhóm PR | Số file | Phạm vi chính |
|---|---:|---|
| **PR1 — Docs, Plans, SRS & Reports** | 4 | Cập nhật SRS v1.3, kế hoạch AI prompt hardening, báo cáo baseline/metrics. |
| **PR2 — DB Migrations & ORM Models** | 4 | Alembic migrations 0011–0012 và cập nhật ORM models (`user_orm.py`, `planning_orm.py`). |
| **PR3 — Shared Kernel AI Harness, Prompt Lock & Infra Config** | 23 | AI Harness runtime (`context_engine`, `execution_manager`, `prompt_registry`, `untrusted_context`, `workflow_port`), `litellm_adapter`, `embedding_adapter`, `prompts.lock`, cấu hình Docker/env. |
| **PR4 — Planning Domain, Services & Use Cases** | 37 | Domain models, Spatio-Temporal Engine, `validation_gate/` package, Dual Critics, Clarification Gap Analysis, Planning Use Cases & Presentation. |
| **PR5 — Account, Execution & Evaluation Contexts** | 22 | Calendar sync/quota adapters, `WeeklyExecutionMetricsAdapter`, Evaluation prompts (`Prove`/`WeeklyReview`) & intelligence use cases. |
| **PR6 — Frontend Angular UI, SSE & API Types** | 32 | Cập nhật `schema.d.ts`, `ai-sse.service`, các dialog wizard roadmap, availability config và spec tests. |
| **PR7 — Backend Unit, Integration & AI Eval Tests** | 28 | Test helpers, 18-goal dataset & `eval_runner.py`, cùng các unit/integration tests cho `shared_kernel`, `planning`, `account`, `execution`, `evaluation`. |
| **Tổng cộng** | **150** | **100% file trong `cd5989b`** |

## PR1 — Docs, Plans, SRS & Reports (4 files)

_Cập nhật SRS v1.3, kế hoạch AI prompt hardening, báo cáo baseline/metrics._

| Trạng thái | Đường dẫn file |
|:---:|---|
| `A` | `docs/plans/ai-prompt-hardening-plan.md` |
| `A` | `docs/reports/live-real-test-report.md` |
| `A` | `docs/reports/prompt-md-decision-metrics.md` |
| `M` | `docs/srs/srs-v1.3.md` |

## PR2 — DB Migrations & ORM Models (4 files)

_Alembic migrations 0011–0012 và cập nhật ORM models (`user_orm.py`, `planning_orm.py`)._

| Trạng thái | Đường dẫn file |
|:---:|---|
| `A` | `backend/alembic/versions/0011_goal_clarification_action.py` |
| `A` | `backend/alembic/versions/0012_adaptive_roadmap_quality.py` |
| `M` | `backend/src/account/infrastructure/orm/user_orm.py` |
| `M` | `backend/src/planning/infrastructure/orm/planning_orm.py` |

## PR3 — Shared Kernel AI Harness, Prompt Lock & Infra Config (23 files)

_AI Harness runtime (`context_engine`, `execution_manager`, `prompt_registry`, `untrusted_context`, `workflow_port`), `litellm_adapter`, `embedding_adapter`, `prompts.lock`, cấu hình Docker/env._

| Trạng thái | Đường dẫn file |
|:---:|---|
| `M` | `.env.example` |
| `A` | `backend/prompts.lock` |
| `A` | `backend/scripts/analyze_prompt_maintenance.py` |
| `A` | `backend/scripts/update_prompts_lock.py` |
| `M` | `backend/src/shared_kernel/application/harness/__init__.py` |
| `M` | `backend/src/shared_kernel/application/harness/context_engine.py` |
| `M` | `backend/src/shared_kernel/application/harness/execution_manager.py` |
| `M` | `backend/src/shared_kernel/application/harness/models.py` |
| `M` | `backend/src/shared_kernel/application/harness/prompt_registry.py` |
| `M` | `backend/src/shared_kernel/application/harness/tool_registry.py` |
| `A` | `backend/src/shared_kernel/application/harness/untrusted_context.py` |
| `M` | `backend/src/shared_kernel/application/harness/workflow_port.py` |
| `M` | `backend/src/shared_kernel/application/llm_port.py` |
| `M` | `backend/src/shared_kernel/config.py` |
| `M` | `backend/src/shared_kernel/infrastructure/database/sqlalchemy_uow.py` |
| `M` | `backend/src/shared_kernel/infrastructure/external_ai/__init__.py` |
| `M` | `backend/src/shared_kernel/infrastructure/external_ai/circuit_breaker.py` |
| `M` | `backend/src/shared_kernel/infrastructure/external_ai/embedding_adapter.py` |
| `M` | `backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py` |
| `M` | `backend/src/shared_kernel/infrastructure/external_ai/prompt_sanitizer.py` |
| `M` | `backend/src/shared_kernel/infrastructure/sse/job_store.py` |
| `M` | `backend/src/shared_kernel/infrastructure/workflow/repository.py` |
| `M` | `docker-compose.yml` |

## PR4 — Planning Domain, Services & Use Cases (37 files)

_Domain models, Spatio-Temporal Engine, `validation_gate/` package, Dual Critics, Clarification Gap Analysis, Planning Use Cases & Presentation._

| Trạng thái | Đường dẫn file |
|:---:|---|
| `A` | `backend/scripts/audit_clarification_dimensions.py` |
| `A` | `backend/scripts/experiment_interview_and_milestones.py` |
| `M` | `backend/src/planning/application/dtos/planning_dtos.py` |
| `M` | `backend/src/planning/application/knowledge/untrusted_context.py` |
| `M` | `backend/src/planning/application/ports/sse_job_port.py` |
| `M` | `backend/src/planning/application/services/__init__.py` |
| `A` | `backend/src/planning/application/services/clarification_gap_analysis.py` |
| `A` | `backend/src/planning/application/services/effective_availability_service.py` |
| `M` | `backend/src/planning/application/services/harness_support.py` |
| `M` | `backend/src/planning/application/services/knowledge_tool_dispatcher.py` |
| `A` | `backend/src/planning/application/services/learning_quality.py` |
| `M` | `backend/src/planning/application/services/roadmap_context_builder.py` |
| `M` | `backend/src/planning/application/services/roadmap_skills.py` |
| `D` | `backend/src/planning/application/services/validation_gate.py` |
| `A` | `backend/src/planning/application/services/validation_gate/__init__.py` |
| `A` | `backend/src/planning/application/services/validation_gate/orchestrator.py` |
| `A` | `backend/src/planning/application/services/validation_gate/tier1_schema.py` |
| `A` | `backend/src/planning/application/services/validation_gate/tier2_deterministic.py` |
| `A` | `backend/src/planning/application/services/validation_gate/tier3_judge.py` |
| `M` | `backend/src/planning/application/use_cases/clarification_use_cases.py` |
| `M` | `backend/src/planning/application/use_cases/create_goal_and_roadmap.py` |
| `M` | `backend/src/planning/application/use_cases/milestone_use_cases.py` |
| `M` | `backend/src/planning/application/use_cases/proposal_generation_use_cases.py` |
| `M` | `backend/src/planning/application/use_cases/proposal_management_use_cases.py` |
| `M` | `backend/src/planning/domain/exceptions/planning_exceptions.py` |
| `M` | `backend/src/planning/domain/models/__init__.py` |
| `M` | `backend/src/planning/domain/models/knowledge_concept.py` |
| `M` | `backend/src/planning/domain/models/milestone.py` |
| `M` | `backend/src/planning/domain/models/roadmap.py` |
| `M` | `backend/src/planning/domain/services/spatio_temporal_engine.py` |
| `M` | `backend/src/planning/infrastructure/adapters/milestone_ownership_adapter.py` |
| `M` | `backend/src/planning/infrastructure/repositories/planning_repositories.py` |
| `M` | `backend/src/planning/presentation/deps.py` |
| `M` | `backend/src/planning/presentation/routers.py` |
| `M` | `backend/src/planning/presentation/schemas/planning_schemas.py` |
| `M` | `backend/src/planning/presentation/tasks.py` |
| `M` | `backend/src/planning/public_api.py` |

## PR5 — Account, Execution & Evaluation Contexts (22 files)

_Calendar sync/quota adapters, `WeeklyExecutionMetricsAdapter`, Evaluation prompts (`Prove`/`WeeklyReview`) & intelligence use cases._

| Trạng thái | Đường dẫn file |
|:---:|---|
| `M` | `backend/src/account/application/use_cases/calendar/handle_google_calendar_oauth_callback_use_case.py` |
| `M` | `backend/src/account/application/use_cases/calendar/initiate_google_calendar_auth_use_case.py` |
| `M` | `backend/src/account/application/use_cases/calendar/sync_schedule_blocks_use_case.py` |
| `M` | `backend/src/account/domain/ports/calendar_provider_port.py` |
| `M` | `backend/src/account/infrastructure/adapters/__init__.py` |
| `M` | `backend/src/account/infrastructure/adapters/availability_query_adapter.py` |
| `M` | `backend/src/account/infrastructure/adapters/calendar_connection_query_adapter.py` |
| `M` | `backend/src/account/infrastructure/adapters/calendar_sync_facade_adapter.py` |
| `M` | `backend/src/account/infrastructure/adapters/google_calendar_adapter.py` |
| `D` | `backend/src/account/infrastructure/adapters/mock_calendar_adapter.py` |
| `M` | `backend/src/account/infrastructure/adapters/quota_facade_adapter.py` |
| `M` | `backend/src/account/presentation/deps.py` |
| `M` | `backend/src/account/public_api.py` |
| `M` | `backend/src/evaluation/application/dtos/intelligence.py` |
| `M` | `backend/src/evaluation/application/ports/intelligence_repository_port.py` |
| `A` | `backend/src/evaluation/application/prompts.py` |
| `M` | `backend/src/evaluation/application/use_cases/intelligence.py` |
| `M` | `backend/src/evaluation/domain/services/__init__.py` |
| `M` | `backend/src/evaluation/infrastructure/repositories/intelligence_repository.py` |
| `M` | `backend/src/evaluation/presentation/deps.py` |
| `A` | `backend/src/execution/infrastructure/adapters/weekly_execution_metrics_adapter.py` |
| `M` | `backend/src/execution/public_api.py` |

## PR6 — Frontend Angular UI, SSE & API Types (32 files)

_Cập nhật `schema.d.ts`, `ai-sse.service`, các dialog wizard roadmap, availability config và spec tests._

| Trạng thái | Đường dẫn file |
|:---:|---|
| `M` | `frontend/src/app/core/api/schema.d.ts` |
| `M` | `frontend/src/app/core/constants/api-endpoints.ts` |
| `A` | `frontend/src/app/core/services/ai-sse.service.spec.ts` |
| `M` | `frontend/src/app/core/services/ai-sse.service.ts` |
| `M` | `frontend/src/app/features/dashboard/dashboard.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/ai-grill-me-dialog/ai-grill-me-dialog.component.html` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/ai-grill-me-dialog/ai-grill-me-dialog.component.spec.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/ai-grill-me-dialog/ai-grill-me-dialog.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/goal-setup-dialog/goal-setup-dialog.component.spec.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/goal-setup-dialog/goal-setup-dialog.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/milestone-approval-dialog/milestone-approval-dialog.component.html` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/milestone-approval-dialog/milestone-approval-dialog.component.spec.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/milestone-approval-dialog/milestone-approval-dialog.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/roadmap-wizard-host/roadmap-wizard-host.component.html` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/roadmap-wizard-host/roadmap-wizard-host.component.spec.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/roadmap-wizard-host/roadmap-wizard-host.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/schedule-proposal-dialog/schedule-proposal-dialog.component.html` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/schedule-proposal-dialog/schedule-proposal-dialog.component.spec.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/dialogs/schedule-proposal-dialog/schedule-proposal-dialog.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/roadmap-page/roadmap-page.component.html` |
| `M` | `frontend/src/app/features/roadmaps/components/roadmap-page/roadmap-page.component.spec.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/roadmap-page/roadmap-page.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/components/roadmaps-hub/roadmaps-hub.component.ts` |
| `M` | `frontend/src/app/features/roadmaps/models/roadmap.model.ts` |
| `M` | `frontend/src/app/features/roadmaps/roadmap.service.spec.ts` |
| `M` | `frontend/src/app/features/roadmaps/services/roadmap.service.ts` |
| `M` | `frontend/src/app/features/settings/components/availability-config/availability-config.component.html` |
| `M` | `frontend/src/app/features/settings/components/availability-config/availability-config.component.spec.ts` |
| `M` | `frontend/src/app/features/settings/components/availability-config/availability-config.component.ts` |
| `M` | `frontend/src/app/shared/components/wizard-dialog-shell/wizard-dialog-shell.component.html` |
| `M` | `frontend/src/app/shared/components/wizard-dialog-shell/wizard-dialog-shell.component.spec.ts` |
| `M` | `frontend/src/app/shared/components/wizard-dialog-shell/wizard-dialog-shell.component.ts` |

## PR7 — Backend Unit, Integration & AI Eval Tests (28 files)

_Test helpers, 18-goal dataset & `eval_runner.py`, cùng các unit/integration tests cho `shared_kernel`, `planning`, `account`, `execution`, `evaluation`._

| Trạng thái | Đường dẫn file |
|:---:|---|
| `A` | `backend/tests/ai_evals/datasets/golden_planning_18_goals.jsonl` |
| `A` | `backend/tests/ai_evals/eval_runner.py` |
| `M` | `backend/tests/ai_evals/test_ai_planning_eval_harness.py` |
| `A` | `backend/tests/ai_evals/test_eval_runner_and_dataset.py` |
| `A` | `backend/tests/helpers/__init__.py` |
| `A` | `backend/tests/helpers/calendar_stubs.py` |
| `A` | `backend/tests/helpers/llm_stubs.py` |
| `M` | `backend/tests/integration/account/test_quota_profile_and_migration_0002.py` |
| `M` | `backend/tests/integration/planning/test_roadmaps_and_ai_planning_api.py` |
| `M` | `backend/tests/unit/account/test_calendar_sync.py` |
| `A` | `backend/tests/unit/evaluation/test_intelligence_hardening.py` |
| `M` | `backend/tests/unit/execution/test_calendar_two_way_sync.py` |
| `A` | `backend/tests/unit/planning/test_adaptive_decomposition_quality.py` |
| `M` | `backend/tests/unit/planning/test_ai_roadmap_clarification.py` |
| `A` | `backend/tests/unit/planning/test_clarification_gap_analysis.py` |
| `M` | `backend/tests/unit/planning/test_clarification_use_cases.py` |
| `A` | `backend/tests/unit/planning/test_hardening_phase1_3.py` |
| `A` | `backend/tests/unit/planning/test_hardening_phase4_5.py` |
| `A` | `backend/tests/unit/planning/test_hardening_phase6_7.py` |
| `A` | `backend/tests/unit/planning/test_phase_b_c_d_improvements.py` |
| `M` | `backend/tests/unit/planning/test_roadmap_evaluation_dataset.py` |
| `M` | `backend/tests/unit/planning/test_roadmap_schedule_separation.py` |
| `M` | `backend/tests/unit/planning/test_skills_and_task_decomposer.py` |
| `M` | `backend/tests/unit/planning/test_sse_job_store_and_use_cases.py` |
| `M` | `backend/tests/unit/planning/test_validation_gate_and_domain.py` |
| `M` | `backend/tests/unit/shared_kernel/test_ai_harness_runtime.py` |
| `M` | `backend/tests/unit/shared_kernel/test_prompt_sanitizer_and_llm_port.py` |
| `A` | `backend/tests/unit/shared_kernel/test_prompts_lock.py` |
