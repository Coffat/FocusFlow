# FocusFlow Shared AI Harness Runtime

## Phạm vi Phase 1–4

Runtime dùng chung nằm trong `shared_kernel/application/harness`. PostgreSQL là nguồn chân lý cho
`workflow_runs` và `workflow_step_executions`; Redis chỉ giữ circuit state và kênh realtime. Mọi
provider thật phải đi qua quota `RESERVE → COMMIT/RELEASE/EXPIRE`, structured-output validation và
circuit breaker. CI dùng mock provider và deterministic embedding 768 chiều.

Các feature flag rollout theo thứ tự:

1. `AI_HARNESS_V2_ENABLED`
2. `KNOWLEDGE_RAG_ENABLED`
3. recovery workflow
4. `LEARNER_MEMORY_ENABLED`

Job đã tạo trên đường cũ được phép hoàn tất trên đường cũ. Không bật đồng loạt các flag trước khi
gate của increment tương ứng xanh.

## Invariant bắt buộc

- AI chỉ đề xuất; lịch sinh ra luôn là `ScheduleProposal(DRAFT)` và chỉ learner Apply mới tạo lịch
  chính thức.
- Context có đúng năm tầng và không nhận lịch sử `study_sessions`, `study_notes` hoặc
  `schedule_change_logs` dạng thô.
- URL ingestion kiểm DNS trước request và sau mỗi redirect; địa chỉ non-global bị quarantine.
- Nội dung retrieval luôn được escape và bọc trong `<untrusted_knowledge_context>`.
- `EXPLICIT` luôn confirmed; `INFERRED` cần ít nhất 3 mẫu, confidence từ 0.7 và 7 evidence record.
- Task completion đơn thuần không phải bằng chứng concept mastery.
- Reset Profile cần xác nhận rõ, xóa memory/mastery nhưng không xóa lịch sử phiên học.

## Verification

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src
uv run lint-imports
uv run pytest -q

cd ../frontend
pnpm exec ng lint
pnpm exec ng test --watch=false
pnpm exec ng build --configuration production
```

Golden AI dataset v2 có 120 scenario trên `PLAN_CREATION`, `OVERDUE_RECOVERY` và `WEEKLY_REVIEW`.
CI chấm 10 metric bằng deterministic/code grader. EVAL-07 latency, EVAL-08 cost và memory precision
từ phản hồi learner không được suy diễn từ CI; chúng chỉ lấy từ staging telemetry.

## Schema

Chuỗi migration Phase 1–4 đưa schema từ 28 lên đúng 35 bảng: 2 workflow, 2 knowledge và 3 learner
intelligence. Kiểm cả upgrade database trống và downgrade/upgrade trước release. Không sửa trực tiếp
`docs/database/schema.sql`; artifact này chỉ được sinh lại bằng script dump schema.
