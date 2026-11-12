# Harness Engineering và kiểm thử

Nguồn nghiệp vụ là SRS v1.3; nguồn kỹ thuật là ADR-001..010. Hai skill FocusFlow đã được cập nhật để phân biệt SRS v1.3 (35 bảng đích) với Alembic hiện có (28 bảng). Khi thay đổi nghiệp vụ, đối chiếu SRS; khi dùng bảng, kiểm migration và ORM thực tế.

## Chạy cục bộ

Trong `backend/`, chạy `uv sync --python 3.12 --extra dev`. Trong `frontend/`, chạy `pnpm install --frozen-lockfile`. Từ gốc repo, dùng `bash scripts/quality-gates.sh backend-static`, `backend-tests`, `frontend-static`, hoặc `frontend-e2e`. Kết quả JUnit và AI eval nằm trong `artifacts/quality/`.

Chạy `bash scripts/check-api-contract.sh` để so OpenAPI backend hiện tại với `schema.d.ts` đã commit. Nếu có drift, regenerate type và xử lý lỗi biên dịch frontend trước khi merge.

Eval offline dùng dataset `golden_constraints_v1.jsonl` với 223 kịch bản cố định, có ID và version. Các case này đo hard constraint cho Mode A, Mode B Soft Overflow, DAG và prompt isolation. Bộ 5 kịch bản planning gốc tiếp tục kiểm tra retry, quota release, draft/apply và Tier 3 fail-open. `RUN_LIVE_AI_EVALS` luôn bằng `0` trong CI.

## Quy tắc gate

- Mọi hard constraint phải đạt 100% trên golden dataset; lỗi nào cũng làm gate đỏ.
- Property tests dùng seed có thể tái lập và kiểm tra quota thời gian, Soft Overflow, DAG ở 100 ví dụ mỗi thuộc tính.
- Gate xuất branch coverage cho availability rules, DAG validator và scheduling engine. Mục tiêu ADR-009 là ≥95% từng thành phần; baseline đo ngày 11/11/2026 lần lượt là 84%, 95%, 70%, nên hai thành phần đầu và cuối chưa đủ ngưỡng để áp `fail-under` lên CI. Bổ sung các case còn thiếu trước khi bật chặn coverage.
- Các metric ADR-009 như User Acceptance, Recovery Success, Insight Acceptance, Profile Correction và Cost cần telemetry thật; không suy ra chúng từ mock. Các ngưỡng ADR vẫn giữ nguyên để đánh giá khi có dữ liệu.
- Khi sửa bug, thêm case tái hiện độc lập; khi đổi OpenAPI, chạy `pnpm run api:gen` với backend đang chạy rồi kiểm tra diff type sinh ra.
- Khi đổi schema, chạy Alembic upgrade/downgrade và đối chiếu schema dump theo AGENTS.md.
