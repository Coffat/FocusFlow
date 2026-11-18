# Báo cáo Phân tích Bảo trì Prompt & Quyết định Lưu trữ `.md` (T7.4)

> Sinh tự động bằng script read-only `backend/scripts/analyze_prompt_maintenance.py`.
> Không tạo bất kỳ code path runtime nào đọc file `.md`.

## 1. Phạm vi lịch sử Git trong repository

- **Shallow repository**: `False`
- **Tổng số commit trên nhánh hiện tại (`HEAD`)**: `144`
- **Khoảng thời gian lịch sử (`HEAD`)**: `2026-09-29 13:25:05 +0700` → `2026-11-14 17:04:51 +0700`
- **Số commit đã commit chạm các file định nghĩa prompt**: `3` (lưu ý: các file mới tạo/sửa chưa commit như `evaluation/application/prompts.py` và `untrusted_context.py` hiển thị `0` commit trong lịch sử đã commit)
- **Danh sách / số lượng authors**: `1` (CoffatDev: 3 commits)

## 2. Thống kê kích thước 12 Production Prompts

| Prompt ID | Version | Workflow Type | LOC | Chars | Est. Tokens (`len/4`) | Est. Tokens (VI conservative) |
|---|---|---|---|---|---|---|
| `coverage-prerequisite-critic` | `2.0.0` | `SCHEDULE_GENERATION` | 5 | 1002 | 250 | 368 |
| `goal-clarifier` | `2.0.0` | `PLAN_CREATION` | 10 | 1725 | 431 | 633 |
| `goal-clarifier-followup` | `2.0.0` | `PLAN_CREATION` | 9 | 1199 | 299 | 440 |
| `learner-fit-actionability-critic` | `2.0.0` | `SCHEDULE_GENERATION` | 5 | 989 | 247 | 363 |
| `learning-milestone-planner` | `2.0.0` | `PLAN_CREATION` | 12 | 2031 | 507 | 745 |
| `learning-task-decomposer` | `2.0.0` | `SCHEDULE_GENERATION` | 12 | 1853 | 463 | 680 |
| `pedagogical-quality-judge` | `2.0.0` | `SCHEDULE_GENERATION` | 13 | 1662 | 415 | 610 |
| `proposal-self-correction` | `2.0.0` | `SCHEDULE_GENERATION` | 4 | 915 | 228 | 336 |
| `prove-mode-grader` | `2.0.0` | `CONTINUOUS_LEARNING` | 12 | 1655 | 413 | 607 |
| `prove-question-generator` | `2.0.0` | `CONTINUOUS_LEARNING` | 11 | 1529 | 382 | 561 |
| `quality-arbiter` | `2.0.0` | `SCHEDULE_GENERATION` | 5 | 873 | 218 | 321 |
| `weekly-review-advisor` | `2.0.0` | `WEEKLY_REVIEW` | 9 | 1263 | 315 | 464 |
| **Tổng cộng (12 prompts)** | — | — | **107** | **16696** | **4168** | **6128** |

### Tổng LOC của các file nguồn chứa prompt

- `backend/src/planning/application/services/roadmap_skills.py`: **600** LOC, **3** commits
- `backend/src/evaluation/application/prompts.py`: **226** LOC, **0** commits
- `backend/src/shared_kernel/application/harness/untrusted_context.py`: **244** LOC, **0** commits

## 3. Phân tích Co-change (Prompt ↔ Code / Schema / Test)

- Tổng số commit chạm prompt: `3`
- Commit đồng thời sửa `DTO / Schema / prompts.lock`: `3`
- Commit đồng thời sửa `Use Cases / Services`: `3`
- Commit đồng thời sửa `Tests`: `2`

### Top file thay đổi cùng lúc với Prompt files

| File | Số lần co-change |
|---|---|
| `backend/src/planning/application/services/validation_gate.py` | 3 |
| `backend/src/planning/application/use_cases/proposal_generation_use_cases.py` | 3 |
| `backend/src/planning/domain/services/spatio_temporal_engine.py` | 3 |
| `backend/src/planning/infrastructure/repositories/planning_repositories.py` | 3 |
| `backend/src/planning/presentation/deps.py` | 3 |
| `backend/src/planning/presentation/routers.py` | 3 |
| `backend/src/planning/presentation/schemas/planning_schemas.py` | 3 |
| `backend/src/planning/presentation/tasks.py` | 3 |
| `backend/src/account/public_api.py` | 2 |
| `backend/src/execution/infrastructure/adapters/schedule_sync_adapter.py` | 2 |
| `backend/src/execution/public_api.py` | 2 |
| `backend/src/planning/application/dtos/planning_dtos.py` | 2 |

## 4. Mức độ trùng lặp nội dung giữa các Prompt

- **Trung bình SequenceMatcher similarity** (toàn bộ 66 cặp): `0.4854`
- **Trung bình Token Jaccard similarity** (toàn bộ 66 cặp): `0.3948`
- Lưu ý: Toàn bộ 12 prompts đều tái sử dụng hằng số `UNTRUSTED_DATA_SYSTEM_RULE` ở cấp Python, nên phần lớn độ tương đồng đến từ quy tắc bảo mật dùng chung.

### Top 8 cặp prompt có độ tương đồng cao nhất

| Prompt A | Prompt B | SequenceMatcher | Token Jaccard |
|---|---|---|---|
| `coverage-prerequisite-critic` | `learner-fit-actionability-critic` | 0.7845 | 0.6536 |
| `goal-clarifier` | `goal-clarifier-followup` | 0.5896 | 0.5837 |
| `coverage-prerequisite-critic` | `quality-arbiter` | 0.6837 | 0.5724 |
| `learner-fit-actionability-critic` | `quality-arbiter` | 0.7132 | 0.5526 |
| `proposal-self-correction` | `quality-arbiter` | 0.6678 | 0.475 |
| `learner-fit-actionability-critic` | `pedagogical-quality-judge` | 0.4987 | 0.4643 |
| `prove-mode-grader` | `prove-question-generator` | 0.4234 | 0.4542 |
| `quality-arbiter` | `weekly-review-advisor` | 0.5974 | 0.4432 |

## 5. Khuyến nghị kỹ thuật (Có chuyển sang `.md` hay giữ trong Python?)

- **Kết luận hiện tại**: **Giữ prompt trong Python** (`roadmap_skills.py`, `evaluation/application/prompts.py`, `untrusted_context.py`) kết hợp `PromptRegistry` + `prompts.lock` CI drift check.
- **Cơ sở dữ liệu định lượng**:
  1. Quy mô gọn: 12 prompts chỉ chiếm tổng cộng **107 dòng / ~6128 tokens**.
  2. Tỷ lệ đồng biến đổi (co-change) với schema/use-case/test cao (`use_cases_or_services=3`, `tests=2`), cho thấy prompt gắn chặt với Pydantic structured output và domain invariants.
  3. Tác giả chỉnh sửa tập trung (`1` author(s)), chưa có nhu cầu non-engineer tự sửa prompt độc lập ngoài chu kỳ code review.
  4. Nội dung bảo mật dùng chung (`UNTRUSTED_DATA_SYSTEM_RULE`) được chia sẻ an toàn bằng Python import mà không cần templating parser bên ngoài.
