# Kế hoạch hardening AI Prompt, Schema, LLM Execution và Security

> Artifact đích: `docs/plans/ai-prompt-hardening-plan.md`. Phiên hiện tại đang ở Plan Mode nên chưa ghi file; nội dung dưới đây là bản kế hoạch hoàn chỉnh để lưu vào đường dẫn trên khi chuyển sang chế độ thực thi.

## 1. Tóm tắt điều hành

1. Review xác định phần lớn nhận định A–F là đúng trên worktree hiện tại; D2 chưa đủ bằng chứng để kết luận LLM thực sự nhân `estimation_bias_beta` hai lần.
2. Rủi ro cao nhất là retry sau khi LLM đã thành công, mặc định retry mọi exception, thiếu `shield` khi cancel và nhiều call bỏ qua `AIExecutionManager`.
3. `LLMProviderPort` sẽ được chuẩn hóa keyword-only, bỏ `prompt` và toàn bộ sampling parameters, trả metadata gồm actual model và thinking tokens.
4. Giữ hard deadline 55 giây theo SRS; hạ decomposer từ HIGH xuống MEDIUM và chia ngân sách theo stage/attempt.
5. Tier 3 Judge tiếp tục chạy inline trong vòng này, một attempt tối đa 8 giây và fail-safe `REVIEW_PENDING`; chỉ cân nhắc background nếu số liệu thật vẫn xấu.
6. Mỗi output LLM có Pydantic model riêng; API DTO và field server-owned không được gửi trong response schema.
7. Structured output và custom tools tiếp tục dùng hai lượt; tài liệu Google chỉ xác nhận phối hợp structured output trực tiếp với built-in tools.
8. Prompt injection được cô lập tại một boundary chung, không dựa vào kiểm tra chuỗi marker.
9. Prove Mode lỗi chấm sẽ dùng trạng thái hiện có `NEEDS_REVIEW`, không cập nhật mastery, tránh migration và false pass.
10. Không có migration DB bắt buộc trong kế hoạch mặc định; audit dữ liệu cũ chỉ đọc trước khi loại alias.
11. Prompt vẫn ở Python trong vòng này; Giai đoạn 7 chỉ thu thập dữ kiện để quyết định `.md`.
12. Baseline đã kiểm tra: 45 test AI liên quan xanh trong 4,49 giây; 11 test golden/eval xanh trong 0,99 giây. Đây chưa phải baseline model thật.

## 2. Bảng xác minh A1–F

Nguồn Google chính thức: [Gemini 3.8 migration checklist](https://ai.google.dev/gemini-api/docs/latest-model), [thinking levels](https://ai.google.dev/gemini-api/docs/thinking), [structured output](https://ai.google.dev/gemini-api/docs/structured-output), [tools](https://ai.google.dev/gemini-api/docs/tools), [token usage](https://ai.google.dev/gemini-api/docs/generate-content/tokens).

| ID | Trạng thái | Bằng chứng hiện tại và kết luận |
|---|---|---|
| A1 | XÁC NHẬN | `execution_manager.py:174-209`: provider, validate, quota commit và workflow writes cùng nằm trong `try` của attempt; lỗi DB tại dòng 180–209 rơi vào retry ở 217–226. |
| A2 | XÁC NHẬN | `execution_manager.py:78-86`: mặc định `lambda _exc: True`. Clarification đã có predicate riêng tại `clarification_use_cases.py:226-241`, nhưng đường chung vẫn sai. |
| A3 | XÁC NHẬN | `execution_manager.py:227-257`: release/workflow write không dùng `asyncio.shield`; lỗi cleanup có thể thay exception gốc. |
| A4 | XÁC NHẬN | Gate gọi trực tiếp tại `validation_gate.py:993-1003,1020-1027`; judge tại 708–718; critics tại `learning_quality.py:306-368`; evaluation tại `intelligence.py:149-159,259-276,405-419`. |
| A5 | XÁC NHẬN | `inspect.signature` tại `execution_manager.py:137-146`, `validation_gate.py:691-697,969-975`, `learning_quality.py:281-285`, `milestone_use_cases.py:291-294`; nhiều call truyền cả `prompt` và `user_prompt`. |
| A6 | XÁC NHẬN | `litellm_adapter.py:1061-1064,1146-1149` chỉ cộng `candidates_token_count`; Google công bố thinking nằm riêng trong `thoughts_token_count`. |
| A7 | XÁC NHẬN | Temperature còn trong port/manager và các call: `llm_port.py:50`, `execution_manager.py:111`, gate 712/999, critics 312/365, evaluation 157/274/417. Adapter còn dùng `thinking_budget`, không phải `thinking_level`, tại 1021–1028,1047–1050,1106–1109. |
| A8 | XÁC NHẬN | Adapter cho MEDIUM/HIGH tối đa 45 giây tại `litellm_adapter.py:1139-1144`; gate và milestone pipeline chỉ có 55 giây tại `validation_gate.py:967`, `milestone_use_cases.py:287`; decomposer đang HIGH tại `roadmap_skills.py:90`. |
| A9 | XÁC NHẬN | Judge 5 giây tại `validation_gate.py:50`; attempt 2 dùng `min(timeout,8)` tại 701–706; thiếu score/status mặc định pass tại 755–761; disabled trả `judge_skipped=False,status=SKIPPED` tại 682–683; judge retry không nhận pipeline deadline. |
| A10 | XÁC NHẬN | Production assert tại `validation_gate.py:356`; file dài trên 1.200 dòng. Việc tách file được để cuối nhằm giảm xung đột. |
| B1 | XÁC NHẬN | Prompt yêu cầu hai thang điểm tại `roadmap_skills.py:123-124`; schema khai cả hai 0–100 tại `validation_gate.py:61-98`, không required; normalization mơ hồ tại 755–780. |
| B2 | XÁC NHẬN | `MILESTONE_RESPONSE_SCHEMA` tại `milestone_use_cases.py:83-125` thiếu `scope_summary/deferred_scope`, nhưng code đọc tại 415–420. |
| B3 | XÁC NHẬN | `task_id` có property nhưng không required tại `proposal_generation_use_cases.py:99,139-145`; normalization vẫn cần giữ làm defense-in-depth. |
| B4 | XÁC NHẬN | Resource schema bắt buộc `title,url` tại `proposal_generation_use_cases.py:109-123`; domain resource chưa có ID tại `knowledge_concept.py:21-39`. |
| B5 | XÁC NHẬN | Docstring/default và tập hợp chuẩn lệch nhau tại `planning_dtos.py:15-25,62-65`; aliases tại `clarification_use_cases.py:210-217`; fallback `"GENERAL"` tại 546/936. Dữ liệu production cũ chưa được kiểm tra. |
| B6 | XÁC NHẬN | `ClarificationQuestionsResponse` chứa `session_id`, `round`, `status`, quota… tại `planning_dtos.py:95-116` và được gửi thẳng làm response schema tại `clarification_use_cases.py:530,875`; question/text và id bị nhân bản tại 33–87. |
| B7 | XÁC NHẬN | Options bị cắt `[:5]` tại `clarification_use_cases.py:547,958`; không có bước tất định bảo đảm “Khác” ở cuối. |
| B8 | XÁC NHẬN | Registry dùng schema rút gọn và judge sai contract tại `roadmap_skills.py:301-349`; checksum được tự tính rồi đăng ký; `PromptTemplate.output_schema` là dict mutable tại `models.py:28-35`; không có production caller của `build_planning_prompt_registry`. |
| B9 | XÁC NHẬN | `SkillDefinition.allowed_tools` tại `roadmap_skills.py:13-24` trùng `STAGE_ALLOWED_TOOLS` tại `knowledge_tool_dispatcher.py:33-46`; generic `RegisteredTool.allowed_stages` dùng `str` tại `tool_registry.py:12-16`. |
| C1 | XÁC NHẬN | Vòng tool dừng vô điều kiện sau lượt đầu tại `litellm_adapter.py:1055-1082`. |
| C2 | XÁC NHẬN | Generic `ToolRegistry.dispatch` chỉ kiểm dict/quyền/status tại `tool_registry.py:38-53`; không validate JSON Schema, timeout, catch handler hay giới hạn output. Dispatcher planning có validation/timeout riêng nhưng không xử lý lỗi thành envelope. |
| C3 | XÁC NHẬN | Non-Gemini branch chỉ dùng `json_object`, tự nhét schema vào system prompt tại `litellm_adapter.py:1202-1228`. Theo ADR-006, mặc định giữ nhánh tương thích nhưng đánh dấu capability và validate nghiêm ở application. |
| D1 | XÁC NHẬN | Milestone context chỉ có id/order/title/description tại `roadmap_context_builder.py:283-291`; đọc field availability không tồn tại tại 293–300; đọc `planned_*` thay vì `scheduled_*` tại 308–327. |
| D2 | CHƯA RÕ | Code nhân beta tại `spatio_temporal_engine.py:1013-1030`, prompt yêu cầu LLM “tôn trọng beta” tại `roadmap_skills.py:97`, nhưng không chứng minh model tự nhân. Hard cap 60 được xác nhận tại `spatio_temporal_engine.py:1009`; ý định sản phẩm chưa có trong SRS. |
| D3 | XÁC NHẬN | `assemble_harness_context` đưa toàn bộ system instruction vào layer SYSTEM tại `roadmap_context_builder.py:436-474`; caller đồng thời gửi cùng instruction làm system prompt. |
| D4 | XÁC NHẬN | Weekly summary chỉ có source/period_days tại `intelligence_repository.py:77-100`; validator tại `intelligence.py:436-459`; faithfulness hardcode 1.0 tại 501–504. |
| D5 | XÁC NHẬN | DTO/DB dùng 0..1 tại `evaluation/application/dtos/intelligence.py:14-16` và ORM constraint; log lại ghi `/5` tại `intelligence.py:317-325`. |
| D6 | XÁC NHẬN | Token estimate `len/4`, cắt JSON theo ký tự, allocation cố định và chỉ kiểm top-level tại `context_engine.py:19-74`. |
| E1 | XÁC NHẬN MỘT PHẦN | ContextBuilder đã sanitize goal ở `roadmap_context_builder.py:162-166,214-217,274-277`; nhưng prompt builder tự nhận raw text và không sanitize tại `roadmap_skills.py:143-207`. Nhánh milestone không có Goal có thể chèn raw lần hai. |
| E2 | XÁC NHẬN | Các system prompt tại `roadmap_skills.py:35-125` và `intelligence.py:150-154,260-265,406-410` chưa có luật chung “external content is data, not instruction”. |
| E3 | XÁC NHẬN | `untrusted_context.py:5-14` chỉ replace đúng case và không escape marker khác; ContextEngine render marker trực tiếp tại `context_engine.py:74`. |
| E4 | XÁC NHẬN | Builders quyết định có thêm raw fields bằng kiểm tra chuỗi `"[USER_PROVIDED_FACTS]"` tại `roadmap_skills.py:154-160,190-197`. |
| E5 | XÁC NHẬN | Fallback score dựa trên số câu có text tại `intelligence.py:228-237`; nếu grader lỗi thì vẫn lưu score/status và upsert mastery tại 300–337. |
| E6 | XÁC NHẬN | LLM output còn status tại `intelligence.py:45-48`; confidence tự khai được gửi cho grader tại 266–270; code chỉ áp threshold, chưa tính rubric/calibration riêng. |
| E7 | XÁC NHẬN | `except Exception: pass` tại `intelligence.py:300-301,433-434`; DB session tồn tại xuyên call; `hasattr(save_weekly_review)` tại 461; fallback model tự đặt tại 178/298/431; weekly memory dùng `EVIDENCED_TAKEAWAY` tại 476. |
| F1 | XÁC NHẬN | Các system/user prompts còn lặp rule JSON, `[SKILL]`, uppercase, nhiệm vụ dài và thiếu field bounds/examples tại `roadmap_skills.py:35-297`, `learning_quality.py:297-367`, `intelligence.py:149-419`. |
| F2 | XÁC NHẬN | Runtime dùng `build_self_correction_prompt` tại `validation_gate.py:903,1050,1203,1241`; `build_task_repair_prompt` chỉ được import/test, không có caller production. Prompt repair nói giữ phần hợp lệ nhưng chỉ truyền số lượng task cũ tại `roadmap_skills.py:284-297`. |

### Mâu thuẫn tài liệu được xử lý

- SRS yêu cầu hard timeout LLM 55 giây; skill cũ ghi judge advisory ≤5 giây. Chọn SRS 55 giây cho toàn pipeline, cho judge tối đa 8 giây trong ngân sách còn lại và vẫn fail-safe.
- Google khuyến cáo không lặp JSON Schema hoặc full JSON example trong prompt. Vì vậy “ví dụ đúng schema” sẽ là ví dụ ngữ nghĩa ngắn trong `Field.description`/golden fixture, không chép lại toàn bộ JSON wire shape trong system prompt.
- SRS mô tả `proof_verdict=PENDING`, nhưng bảng `milestone_proofs` hiện chỉ cho `DRAFT|READY|SUBMITTED|PASSED|NEEDS_REVIEW`. Mặc định dùng `NEEDS_REVIEW` khi grader không xác minh được và tuyệt đối không cập nhật mastery; không tự mở rộng DB enum trong vòng hardening này.

## 3. Kiểm kê toàn bộ prompt production

| Prompt | Vị trí/hàm | Mục đích và caller | Registry | Execution path | Sanitizer/boundary |
|---|---|---|---|---|---|
| Goal Clarifier system | `roadmap_skills.py:27-54`, `GOAL_CLARIFIER_SKILL` | Câu hỏi chẩn đoán; `GenerateClarificationQuestionsUseCase`, follow-up | Khai báo nhưng chưa dùng | Manager | Main path qua ContextBuilder; follow-up chưa cấu trúc/sanitize đầy đủ |
| Goal Clarifier user | `roadmap_skills.py:143-177`, `build_goal_clarifier_prompt` | Main clarification tại `clarification_use_cases.py:846-875` | Không | Manager | Dựa vào string marker, còn raw fallback |
| Clarification follow-up inline | `clarification_use_cases.py:495-535` | Một câu follow-up vòng hai | Không | Manager | `gap/prior_answers` nội suy trực tiếp |
| Milestone Planner system | `roadmap_skills.py:57-77` | Milestone generation tại `milestone_use_cases.py:206-362` | Khai báo nhưng chưa dùng | Manager nếu có workflow repo; direct fallback | Partial |
| Milestone Planner user | `roadmap_skills.py:180-207` | Build milestone request | Không | Như trên | Raw fallback có thể trùng dữ liệu |
| Task Decomposer system | `roadmap_skills.py:80-105` | Task generation tại `proposal_generation_use_cases.py:438-588` | Khai báo nhưng chưa dùng | Gate gọi provider trực tiếp | ContextBuilder sanitize một phần |
| Task Decomposer user | `roadmap_skills.py:210-234` | Dữ liệu milestone/availability | Không | Gate direct | Structured context nhưng còn marker text |
| Active self-correction | `validation_gate.py:903-927` | Retry milestone/task/judge violations | Không | Gate direct | Kế thừa base prompt |
| Unused task repair | `roadmap_skills.py:259-298` | Không có production caller | Không | Không chạy | N/A; xóa sau khi xác nhận |
| Pedagogical Judge system | `roadmap_skills.py:108-125` | Tier 3 judge tại `validation_gate.py:671-787` | Khai báo sai schema, chưa dùng | Direct | Proposal JSON không có explicit untrusted rule |
| Pedagogical Judge user | `roadmap_skills.py:237-256` | Proposal payload + goal | Không | Direct | Chưa structured boundary |
| Coverage/Prerequisite Critic | `learning_quality.py:286-316` | Critic 1 cho milestone/task | Không | Direct | Context/payload nội suy |
| Learner-fit Critic | Cùng hàm trên | Critic 2 | Không | Direct | Như trên |
| Quality Arbiter | `learning_quality.py:343-369` | Phân xử critic bất đồng | Không | Direct | Nội suy critic reports/payload |
| Prove Mode question | `intelligence.py:149-159` | Sinh ba câu recall | Không | Direct | Chỉ sanitize title |
| Prove Mode grader | `intelligence.py:259-276` | Chấm learner answers | Không | Direct | Answer được sanitize; thiếu data/instruction rule |
| Weekly Review | `intelligence.py:405-419` | Feedback tuần | Không | Direct | Reflection được sanitize; quantitative data nghèo |
| Adapter final-stage instruction | `litellm_adapter.py:1090-1109` | Ép lượt cuối không gọi tool | Không | Adapter nội bộ | Sẽ thay bằng config/protocol, không để business prompt lặp |
| Non-Gemini schema instruction | `litellm_adapter.py:1204-1221` | Bù thiếu native schema enforcement | Không | Adapter nội bộ | Giữ riêng cho compatibility branch |

## 4. Đồ thị phụ thuộc và nhóm có thể song song

```text
PR-00 Baseline
   ↓
PR-01 Port + execution lifecycle
   ↓
PR-02 Migrate mọi call + deadline/judge
   ├──────────────┬──────────────┐
   ↓              ↓              ↓
PR-03 Schemas   PR-05 Registry  PR-06 Adapter/tools
   ↓              ↓              ↓
PR-04 Clarifier ──┴──────────────┘
   ↓
PR-07 Context/data ownership
   ↓
PR-08 Security boundaries
   ↓
PR-09 Evaluation fail-safe
   ↓
PR-10 → PR-11 → PR-12 → PR-13 → PR-14 → PR-15 → PR-16
   ↓
PR-17 Registry wiring + prompts.lock
   ↓
PR-18 Gate split/cleanup
```

- PR-03, PR-05 và phần validation thuần của PR-06 có thể làm song song sau PR-02.
- Các PR prompt phải tuần tự theo thứ tự yêu cầu để đo tác động riêng.
- PR-18 cố ý để cuối; không trộn refactor file với thay đổi hành vi.
- PR cần dữ liệu/model thật: PR-00, PR-02, PR-04 audit alias, PR-06 SDK contract và toàn bộ PR-10..16.
- Mặc định không PR nào cần migration DB. PR-04 chỉ audit read-only; PR-09 giữ status DB hiện có.

## 5. Chi tiết task theo giai đoạn/PR

### Giai đoạn 0 — Baseline và lưới an toàn

| ID | Mục | Mục tiêu / file-hàm / thay đổi | Test và tiêu chí chấp nhận | Rủi ro, rollback | Size | Phụ thuộc / PR |
|---|---|---|---|---|---|---|
| T0.1 | A–F | Mở rộng `tests/ai_evals/` thành tập 18 mục tiêu: 6 domain, 3 trình độ, deadline rộng/hẹp, Mode A/B, 4 injection cases; tái sử dụng dataset hiện có, không gọi provider thật trong CI. | Dataset có expected invariants và golden deterministic; CI offline 100% xanh. | Golden quá cứng; rollback dataset mới. | M | PR-00 |
| T0.2 | A8,A9,D4 | Thêm runner đo pass@1, retry trung bình, prompt/output/thinking tokens, p50/p95, judge timeout, weekly fallback; xuất JSON artifact, không ghi PII/prompt thô. | Chạy Python 3.12/mock; live run opt-in bằng env riêng; cùng input tạo report schema ổn định. | Nondeterminism; chạy 3 lần/scenario và dùng median/p95. | M | PR-00 |
| T0.3 | A1–A3,E5 | Characterization tests cho post-LLM DB failure, cancel cleanup, non-retryable errors, grader failure và current status. | Test tái hiện đúng lỗi hiện tại trước khi sửa; không lock-in false-pass như hành vi mong muốn. | Test phụ thuộc implementation; chỉ assert observable lifecycle. | S | PR-00 |

### Giai đoạn 1 — Đường thực thi và độ tin cậy

| ID | Mục | Mục tiêu / file-hàm / thay đổi | Test và tiêu chí chấp nhận | Rủi ro, rollback | Size | Phụ thuộc / PR |
|---|---|---|---|---|---|---|
| T1.1 | A5–A7 | Chuẩn hóa `LLMProviderPort.generate_structured` keyword-only: `system_prompt,user_prompt,response_schema,tools,tool_executor,max_tool_calls,thinking_level`; bỏ `prompt/temperature`; trả result object chứa payload, prompt/output/thinking tokens và actual model ID. | Mypy bắt mọi caller cũ; token billable completion = candidate + thoughts; không còn `inspect.signature` hay temperature trong production. | Diff rộng; rollback toàn PR trước khi migrate prompt behavior. | L | PR-01 |
| T1.2 | A1–A3 | Tách provider attempt khỏi post-success effects trong `AIExecutionManager`; retry classifier chỉ nhận timeout, 429, 5xx, JSON/Pydantic invalid; commit/release idempotent; cancel cleanup dùng `shield`; cleanup lỗi được log nhưng exception gốc giữ nguyên. | LLM success + workflow DB failure không gọi LLM lần hai; 400/401/403, `PermissionError`, `TypeError` đúng một attempt; cancel luôn đóng reservation. | Sai trạng thái quota; fake quota concurrency tests và idempotency tests. | L | PR-01 |
| T1.3 | A7,A8 | Cấu hình stage-level thinking/deadline: goal LOW, milestone MEDIUM, decomposer MEDIUM, judge MEDIUM, critics LOW, Prove grader MEDIUM, weekly MEDIUM; model ID chuẩn `gemini-3.8-flash`, thinking tách riêng. Pipeline 55s; decomposer call ≤35s, critics song song ≤8s, judge một attempt ≤8s và luôn bị clamp bởi remaining deadline. | Không stage nào dùng `minimal`; total timeout ≤55s; retry chỉ chạy nếu còn ≥12s; p95 không vượt 55s. | Chất lượng decomposer giảm; rollback riêng level MEDIUM→HIGH nếu live eval chứng minh tốt hơn và deadline vẫn đạt. | M | PR-02 |
| T1.4 | A4,A9 | Chuyển gate generate, critics, judge, Prove/Weekly Review qua manager; dùng một reservation cho user workflow và aggregate usage, không tính nhiều quota credit cho internal steps; mỗi physical call vẫn có workflow step. | Không direct provider call ngoài manager/adapter/circuit breaker; token mọi step cộng đủ; judge thiếu field thành REVIEW_PENDING. | Sai semantics quota; giữ contract “một user operation = một quota credit”. | L | PR-02 |

### Giai đoạn 2 — Hợp đồng dữ liệu một nguồn sự thật

| ID | Mục | Mục tiêu / file-hàm / thay đổi | Test và tiêu chí chấp nhận | Rủi ro, rollback | Size | Phụ thuộc / PR |
|---|---|---|---|---|---|---|
| T2.1 | B1–B3 | Tạo Pydantic LLM output models riêng cho milestone, task proposal và judge; schema luôn từ `model_json_schema()`. Judge chỉ có integer `score 0..100` và `issues[{severity,category,message,task_ref?}]`; task ID bắt buộc `T1,T2…`; milestone có `scope_summary/deferred_scope`. | Model validate fail khi thiếu required; consumed-field constants là subset schema; không còn handwritten schema cùng contract. | Model/schema Gemini quá phức tạp; giữ schema subset Google hỗ trợ. | L | PR-03 |
| T2.2 | B4 | Tool trả `resource_id` tất định từ curated resource; LLM output chỉ chọn tối đa ba ID/task; mapper server điền title/url/type/description; ID không thuộc tool results bị loại; không results → `[]`. | Không URL nào xuất hiện nếu không đến từ tool; invalid ID không được persist. | ID thay đổi khi URL đổi; version/hash canonical input. | M | PR-03 |
| T2.3 | B6,B7 | Tách `ClarificationQuestionLLMOutput` và `ClarificationQuestionsLLMOutput`; LLM chỉ sinh text/type/options/purpose/format/dimension. Mapper cấp ID, nhân bản legacy `question/text`, thêm “Khác / tự định nghĩa” sau tối đa bốn option chuyên môn. | Response schema không chứa session/status/quota/id; choice luôn 3–5 option và “Khác” cuối; API DTO giữ nguyên. | FE phụ thuộc ordering; behavior change được ghi release note. | M | PR-04 |
| T2.4 | B5 | Tạo một `DiagnosticDimension` enum dùng cho gap analyzer, LLM schema và validator; aliases chỉ ở compatibility mapper. Audit read-only JSON trong `goals.clarification_context` và `workflow_runs.context_snapshot`; chưa xóa aliases nếu còn dữ liệu cũ. | Canonical output chỉ thuộc 7 giá trị; audit report liệt kê counts/invalid rows; không migration trong PR này. | JSON legacy không parse được; script audit ghi count, không sửa DB. | M | PR-04 |
| T2.5 | B8,B9 | Registry nhận model/schema thật, deep-immutable canonical schema; prompt ID dùng canonical skill ID; tool authority lấy từ `SkillDefinition`, startup assert registry khớp `RoadmapPipelineStage`. | Mutate schema sau register không đổi checksum; mismatch tool/stage fail startup; judge registry schema đúng model. | Startup fail vì config cũ; feature flag chỉ cho audit một release, không bypass lâu dài. | M | PR-05 |

### Giai đoạn 3 — Adapter và tool

| ID | Mục | Mục tiêu / file-hàm / thay đổi | Test và tiêu chí chấp nhận | Rủi ro, rollback | Size | Phụ thuộc / PR |
|---|---|---|---|---|---|---|
| T3.1 | C1 | Sửa Google tool loop thành multi-turn đúng protocol, bảo toàn function call ID/name/thought signatures; tiếp tục hai-stage: tool discovery rồi structured final output. | Test hai lượt tool tuần tự và parallel calls; đúng call limit; không unconditional break. | SDK behavior thay đổi; adapter contract test khóa phiên bản. | L | PR-06 |
| T3.2 | C2 | Generic `ToolRegistry` validate args theo declaration schema, timeout từng tool, catch lỗi thành `ToolResultEnvelope(error)`, truncate payload theo byte/item limit và ghi audit không chứa dữ liệu nhạy cảm. | Invalid args không gọi handler; timeout/error trả envelope; payload không vượt giới hạn. | Model lặp tool khi nhận error; tổng call limit vẫn chặn. | M | PR-06 |
| T3.3 | C3 | Giữ non-Gemini compatibility theo ADR-006; thêm capability `native_structured_output`; native path dùng schema, fallback path dùng JSON instruction + Pydantic validation. Không cho fallback trong production Gemini 3.8. | Contract test cả hai capability; invalid fallback JSON fail-safe. | Hai behavior paths; cùng output model và mapper giảm drift. | M | PR-06 |
| T3.4 | SDK | Live opt-in contract test xác minh `google-genai` hiện tại: Gemini 3.8 Flash với custom function calling + response schema. Mặc định giữ hai-stage vì docs chỉ xác nhận structured output phối hợp trực tiếp với built-in tools. | Ghi SDK/model/version và kết quả; test không chạy CI, không log key. | Chi phí/capability preview; không biến live test thành gate bắt buộc. | S | PR-06, REAL |

### Giai đoạn 4 — Dữ liệu đầu vào và ngữ cảnh

| ID | Mục | Mục tiêu / file-hàm / thay đổi | Test và tiêu chí chấp nhận | Rủi ro, rollback | Size | Phụ thuộc / PR |
|---|---|---|---|---|---|---|
| T4.1 | D1–D3 | Context decomposition thêm outcomes, criteria, effort; dùng `default_daily_quota_minutes/daily_quota_minutes`, `scheduled_start/end`; bỏ beta khỏi prompt và system layer trùng; code là owner của beta. | Snapshot test đúng field thực; prompt không chứa system instruction lần hai; beta chỉ áp đúng một lần trong scheduler. | Prompt token/content thay đổi; so baseline từng stage. | M | PR-07 |
| T4.2 | D2 | Bỏ hard cap 60; session limit = `min(max(10,opt_session_minutes),120,capacity)`. Không yêu cầu LLM tự nhân beta. | opt 90 tạo block ≤90 khi slot đủ; beta chỉ đổi effort server-side; hard constraints 30–120 giữ nguyên. | Phiên dài hơn UX hiện tại; rollback cap bằng config nếu product xác nhận 60. | M | PR-07 |
| T4.3 | D6 | ContextEngine dùng tokenizer/model count adapter khi có, fallback conservative cho tiếng Việt; truncate theo item/layer priority, luôn tạo JSON hợp lệ; redistribute unused budget; recursive forbidden-key check và escape marker. | Mọi layer parse được JSON; nested raw history bị reject; budget không vượt trần; Vietnamese estimate sai số được đo. | Tokenizer có thể tốn CPU; cache theo content hash. | L | PR-07 |
| T4.4 | D5 | Chuẩn hóa confidence nội bộ/API/DB là 0..1; mọi text/log hiển thị `%` hoặc `0..1`, không `/5`; calibration tính tất định. | confidence 0.8 log “80%”; không string `/5`; DB constraint giữ nguyên. | Chỉ behavior/log change, rollback đơn giản. | S | PR-07 |

### Giai đoạn 5 — Bảo mật và toàn vẹn

| ID | Mục | Mục tiêu / file-hàm / thay đổi | Test và tiêu chí chấp nhận | Rủi ro, rollback | Size | Phụ thuộc / PR |
|---|---|---|---|---|---|---|
| T5.1 | E1–E4 | Tạo một structured prompt boundary nhận typed blocks; sanitize mọi user/free text tại boundary; `html.escape` toàn content untrusted; marker case-insensitive; system rule chung nói KB/learner/tool/user blocks là dữ liệu. Bỏ string sniffing marker. | Injection cases gồm mixed-case closing tag, fake section header, nested marker; không payload nào thoát block. | Escape làm giảm readability; chỉ escape boundaries, giữ Unicode. | L | PR-08 |
| T5.2 | E5,E6 | Prove grader output chỉ có rubric component scores + corrective evidence; code cộng điểm và status. Không gửi confidence vào grader; grader lỗi → `NEEDS_REVIEW`, score không được coi là verified và không upsert mastery/memory evidence. | Answer `"a"` không pass; grader timeout không ghi mastery; threshold 70 tính tất định; calibration tính sau. | User thấy nhiều NEEDS_REVIEW; đây là fail-safe có chủ đích. | L | PR-09 |
| T5.3 | D4,E7 | Weekly Review lấy deterministic metrics qua query port trước LLM; đóng transaction trước external call, mở UoW mới để persist; bỏ `hasattr`; lưu actual model; source_workflow=`WEEKLY_REVIEW`; faithfulness lưu tỷ lệ thật. | Summary có completed/planned minutes, adherence, overdue, confidence/mastery khi có; thiếu data tạo feedback hỗ trợ, không bịa số; rollback transaction sạch. | Query cross-context; chỉ qua `public_api` Query Ports. | L | PR-09 |
| T5.4 | E7 | Thay `except Exception: pass` bằng typed handling/log an toàn; workflow step ghi failure/fallback reason, không PII. | Exception gốc quan sát được; fallback có reason code; API vẫn trả safe message. | Log noise; rate-limit/sampling operational logs. | S | PR-09 |

### Giai đoạn 6 — Viết lại prompt, mỗi prompt một PR

Mỗi PR dưới đây chỉ merge khi toàn bộ hard constraints không regression, pass@1 không giảm và latency/token nằm trong ngưỡng §6.

| ID | Prompt / thay đổi | Test và tiêu chí chấp nhận | Size | PR |
|---|---|---|---|---|
| T6.1 | Decomposer: tách “Tra cứu” và “Xuất kết quả”; ID `T1…`; THEORY→PRACTICE→REVIEW→PROJECT; tối đa 3 resource IDs; nhận effort cuối đã tính, không beta; sửa retry thành “sinh lại toàn bộ và khắc phục lỗi”. Xóa `build_task_repair_prompt` nếu vẫn không có caller. | Coverage/outcome/concept tests; no hallucinated URL; eval riêng decomposer. | M | PR-10 |
| T6.2 | Judge + critics/arbiter: rubric neo 0/40/60/80/100, FAIL hoặc score<60; input có learner level và milestone summary; issue phải trỏ evidence/task_ref. | Missing score/status invalid; unsupported issue bị loại; judge timeout → REVIEW_PENDING. | M | PR-11 |
| T6.3 | Prove grader: ba rubric components, evidence per answer, không status/confidence; external blocks là data. | Code tính score/status; adversarial learner answers không chi phối rubric. | M | PR-12 |
| T6.4 | Goal Clarifier: câu hỏi ≤ gaps, 0 nếu không gap; option chuyên môn không chồng lấn; dimension enum; định nghĩa purpose/format; user task ở cuối. | 0–3 questions đúng gap; “Khác” do server thêm; không hỏi lại known dimension. | M | PR-13 |
| T6.5 | Milestone Planner: chống bịa concept ID, coverage criteria, effort bounds/milestone, định nghĩa FULL_SCOPE/FIT_CAPACITY/deferred_scope. | Unknown concept vào unverified; scope fields required; coverage và capacity eval. | M | PR-14 |
| T6.6 | Weekly Review: giọng hỗ trợ, không phán xét; 1–3 actions; thiếu dữ liệu nói rõ thiếu; chỉ dùng deterministic metrics. | Faithfulness validator pass; action count 1–3; fallback rate không tăng. | S | PR-15 |
| T6.7 | Prove question generation: đúng ba mục tiêu hiểu bản chất/ví dụ/vận dụng; grounded từ milestone/tasks/concepts; untrusted rule chung. | Ba câu khác nhau, có grounding reference, injection cases pass. | S | PR-16 |

### Giai đoạn 7 — Gom prompt và nối registry, không chuyển `.md`

| ID | Mục | Mục tiêu / file-hàm / thay đổi | Test và tiêu chí chấp nhận | Rủi ro, rollback | Size | Phụ thuộc / PR |
|---|---|---|---|---|---|---|
| T7.1 | B8,F | Registry quản lý mọi production prompt, gồm evaluation/critics; callsite lấy `prompt_id@version`, schema checksum và ghi vào `WorkflowRun.context_snapshot`. | Inventory và registry one-to-one; không direct inline system prompt ngoài adapter internals. | Registry wiring lỗi startup; rollback registry resolution, không rollback prompt content. | L | PR-17 |
| T7.2 | B8 | Thêm `prompts.lock` chứa canonical prompt ID/version/checksum/schema checksum; golden test chỉ cập nhật bằng lệnh review rõ ràng. | Prompt/schema đổi mà không bump version hoặc lock → CI fail. | Lock churn; canonical serialization ổn định. | M | PR-17 |
| T7.3 | A10 | Sau khi behavior ổn định, tách gate thành orchestrator, tier1, tier2, tier3; thay production assert bằng validation branch. | Không đổi public behavior; toàn bộ gate/eval tests trước và sau giống nhau. | Merge conflict; PR độc lập, revert riêng. | M | PR-18 |
| T7.4 | Quyết định `.md` | Script read-only từ git log thống kê số prompt, LOC/token, tần suất sửa, authors, co-change và duplicate similarity; chỉ ghi report, không chuyển file. | Báo cáo có dữ liệu đủ để quyết định; không có code path đọc `.md`. | Git history shallow; ghi rõ phạm vi lịch sử. | S | PR-17 |

## 6. Kế hoạch đo lường và ngưỡng chấp nhận

| Metric | Cách đo | Ngưỡng merge |
|---|---|---|
| Raw pass@1 | 18 scenario × 3 lần, fixed model/stage thinking | Không thấp hơn baseline theo từng prompt; hard constraints 100% |
| Post-retry recovery | Tỷ lệ hợp lệ sau retry | Không thấp hơn baseline; 0 proposal vi phạm Tier 2 được persist |
| Retry trung bình | Physical model attempts/workflow | Không tăng quá 0,1 attempt so baseline |
| Latency p50/p95 | Monotonic clock theo step và toàn pipeline | Main planning p95 ≤55s; mỗi PR không tăng >10% baseline |
| Judge timeout | Timeout/total judge runs | ≤5%; nếu >5% sau MEDIUM+8s thì mở follow-up background design |
| Tokens | Prompt, candidate, thinking, total theo step | Thinking được tính đủ; p95 không tăng >10% nếu quality không tăng |
| Weekly fallback | Fallback/weekly reviews có đủ quantitative data | <5%; với thiếu data phải là explicit insufficient-data response |
| Injection isolation | Adversarial dataset | 100% không thoát boundary, không thay đổi task/schema/rules |
| Schema conformance | Pydantic validation + consumed-field contract | 100%; không missing field được default thành PASS |
| Tool integrity | Invalid args, timeout, oversized output, unknown ID | 100% fail-safe; 0 URL ngoài tool evidence |
| Quota integrity | Concurrent/failure/cancel tests | Một operation commit đúng một credit; không leak/double commit |
| Faithfulness | Numbers trong weekly output so deterministic summary | 100% số trực tiếp có nguồn; derived number chỉ cho phép qua declared deterministic derivation |

Live baseline và prompt comparisons dùng `gemini-3.8-flash`, stage thinking cố định, ba lần/scenario, chạy ngoài CI với tài khoản test. CI tiếp tục dùng mock provider và golden deterministic.

## 7. Rủi ro tổng thể và rollback

- Thay đổi port ảnh hưởng nhiều caller: gom trong PR-01, không trộn prompt/schema behavior.
- Quota aggregation sai có thể tính thừa/thiếu: fake concurrency và idempotency test là gate bắt buộc.
- Tightening schema làm giảm pass@1 ban đầu: mapper compatibility chỉ được dùng cho API/legacy DB, không được “coerce” output LLM sai.
- Prompt hardening có thể tăng token: đo riêng từng PR và revert prompt version nếu vượt ngưỡng.
- Alias diagnostic có thể tồn tại trong JSON production: giữ compatibility mapper tối thiểu hai release sau audit.
- Hai-stage tool flow tăng latency: chỉ gọi tools ở attempt đầu, cache evidence trong workflow và reuse ở retry.
- Non-Gemini fallback có schema enforcement yếu: không dùng trong cấu hình production Gemini; Pydantic vẫn fail-closed.
- Worktree hiện tại có nhiều thay đổi chưa commit: khi triển khai phải tạo từng PR từ trạng thái đã thống nhất, không vô tình ghi đè thay đổi người dùng.
- Baseline vừa chạy bằng `.venv` Python 3.14 dù dự án yêu cầu 3.12; số chính thức phải chạy lại trong Python 3.12/Docker.
- Rollback theo từng PR bằng revert độc lập; `prompts.lock` giữ checksum phiên bản trước để khôi phục chính xác.

## 8. Câu hỏi mở và giả định mặc định

1. Quota tính theo physical LLM call hay user workflow? Mặc định: một credit/user workflow, aggregate toàn bộ internal calls và tokens.
2. Tier 3 Judge có chuyển background ngay không? Mặc định: chưa; chạy inline một attempt MEDIUM tối đa 8 giây, bounded bởi 55 giây, chỉ chuyển background nếu live timeout >5%.
3. Có được xóa alias dimension ngay không? Mặc định: không; audit production, giữ mapper hai release và chỉ xóa khi count bằng 0.
4. Có tiếp tục hỗ trợ non-Gemini không? Mặc định: có theo ADR-006, nhưng là compatibility path, không phải production path.
5. Hard cap session 60 phút có chủ đích không? Mặc định: không thấy quy định SRS; thay bằng `min(opt_session_minutes,120,capacity)` và rollback bằng config nếu product xác nhận cap 60.

## 9. Mẫu báo cáo sau khi thực thi

- Danh sách PR, commit và các mục A–F đã đóng.
- Mục bị bỏ/lùi, lý do và issue theo dõi.
- Bảng metric trước/sau: pass@1, recovery, retry, token candidate/thinking, p50/p95, judge timeout, weekly fallback.
- Bảng kiểm kê prompt đã cập nhật với prompt ID/version/checksum/caller.
- Kết quả quality gates: ruff, format, mypy, import-linter, pytest, AI eval và API contract nếu có.
- Thay đổi API/DB và tương thích ngược; mặc định kỳ này không migration.
- Phát hiện mới ngoài phạm vi, không trộn vào các PR chính.
- Dữ liệu quyết định `.md`: số prompt, LOC/token, tần suất sửa, authors, co-change và mức trùng lặp.
