# 07 — Mẫu đầu ra

Mục lục: A. Báo cáo chuẩn (STANDARD/DEEP) · B. Báo cáo QUICK · C. Định dạng một finding · D. Chat nhiều lượt · E. JSON cho pipeline · F. Quy tắc diễn đạt

## A. Báo cáo chuẩn

Dùng đúng thứ tự dưới đây. Bỏ mục không áp dụng thay vì để trống.

```
# Review: <tên tài liệu/hệ thống> — <phiên bản>

## 1. Kết luận
**Verdict:** NO-GO | GO CÓ ĐIỀU KIỆN | GO
**Lý do chính:** 2–3 câu nêu vấn đề quyết định verdict.
**Điều kiện để GO:** (nếu có) danh sách đánh số, mỗi mục một hành động cụ thể + người phụ trách đề xuất.

## 2. Phạm vi & giả định
- Đã review: ...
- Không review / không đủ thông tin: ...
- Độ sâu: QUICK | STANDARD | DEEP · Mức trưởng thành: draft | baseline
- [GIẢ ĐỊNH]: ...

## 3. Tổng quan
| Nhóm | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| SRS | | | | |
| Use case | | | | |
| Class | | | | |
| DB | | | | |
| State | | | | |
| Chéo artifact | | | | |

Bảng coverage (đủ / thiếu / N/A): Phạm vi · Actor & quyền · Luồng ngoại lệ · NFR đo được · Dữ liệu & PII · Tích hợp · Trạng thái & vòng đời · Truy vết.

**Điểm làm tốt:** (chỉ nêu điều thật sự có)

## 4. Finding S1 & S2 (chi tiết)
<Theo định dạng ở mục C. Sắp theo severity rồi theo mức ảnh hưởng.>

## 5. Finding S3 & S4 (rút gọn)
Bảng: ID · Vị trí · Vấn đề · Đề xuất (một dòng mỗi finding)

## 6. Câu hỏi mở cho PO/SME/Dev
Đánh số, gắn finding liên quan, ghi người nên trả lời. Mỗi câu một ý.

## 7. Phụ lục (DEEP hoặc khi được yêu cầu)
- A. Ma trận truy vết đầy đủ
- B. Transition matrix
- C. Bảng thuật ngữ đồng nghĩa
- D. Test condition gợi ý
- E. Danh sách từ mơ hồ & vị trí
```

## B. Báo cáo QUICK

Chỉ: Verdict (1 dòng) · Top ≤5 rủi ro (mỗi cái 2–3 dòng, có bằng chứng) · ≤5 câu hỏi quan trọng nhất · "Có thể review sâu hơn: X, Y". Không bảng tổng quan.

## C. Định dạng một finding

```
### [RULE-ID] <Tiêu đề ngắn nêu vấn đề> — S2 · MED/HIGH · DEFECT
**Vị trí:** <mục / trang / UC-ID / tên node / bảng.cột>
**Bằng chứng:** "<trích dẫn ≤ 25 từ nguyên văn>"  (thêm vị trí 2 nếu CONFLICT)
**Vấn đề:** Điều gì sai/thiếu/mơ hồ và vì sao theo chuẩn/rule nào.
**Hậu quả nếu giữ nguyên:** Dev/QA/Người dùng/Pháp lý sẽ gặp gì (cụ thể).
**Đề xuất (ĐỀ XUẤT):** Sửa tối thiểu, có thể áp dụng ngay. Nếu cần quyết định nghiệp vụ → nêu 2–3 phương án và hậu quả mỗi phương án.
**Cần xác nhận với:** <vai trò> (nếu có)
```

Ví dụ hoàn chỉnh:

```
### [SRS-E02] NFR hiệu năng không đo được — S2 · HIGH · AMBIGUITY
**Vị trí:** §6.1, NFR-003
**Bằng chứng:** "Hệ thống phải phản hồi nhanh khi tìm kiếm sản phẩm."
**Vấn đề:** Không có ngưỡng, percentile, tải, kích thước dữ liệu → không thể viết test pass/fail (vi phạm tính verifiable, ISO/IEC/IEEE 29148).
**Hậu quả nếu giữ nguyên:** Dev tự chọn mục tiêu; QA không nghiệm thu được; tranh chấp khi UAT.
**Đề xuất (ĐỀ XUẤT):** "Với 500 người dùng đồng thời và 2 triệu sản phẩm, 95% yêu cầu tìm kiếm phải có phản hồi ≤ 1,5 giây, đo tại API gateway (p95)." Giá trị số cần PO xác nhận.
**Cần xác nhận với:** PO, Tech Lead
```

Với finding LOW: dùng loại `QUESTION`, bỏ phần "Hậu quả" nếu chỉ suy đoán, thay bằng "Vì sao hỏi".

## D. Chat nhiều lượt

- Lượt đầu: báo cáo theo A hoặc B. Không hỏi lại thứ đã trả lời.
- Khi người dùng cập nhật tài liệu: **re-review theo diff** — liệt kê finding đã đóng, còn mở, mới phát sinh (tránh lặp báo cáo đầy đủ). Giữ ID finding ổn định.
- Khi người dùng hỏi thêm về một finding: trả lời trực tiếp, trích lại bằng chứng, không sinh lại báo cáo.

## E. JSON cho pipeline

Chỉ dùng khi người dùng/hệ thống yêu cầu rõ. Xuất **một JSON hợp lệ**, không văn bản ngoài JSON.

```json
{
  "review": {
    "target": "string",
    "version": "string|null",
    "depth": "QUICK|STANDARD|DEEP",
    "maturity": "draft|baseline",
    "verdict": "NO-GO|CONDITIONAL-GO|GO",
    "scope_reviewed": ["string"],
    "scope_not_reviewed": ["string"],
    "assumptions": ["string"]
  },
  "summary": {
    "counts": {"S1": 0, "S2": 0, "S3": 0, "S4": 0},
    "conditions_to_go": ["string"],
    "strengths": ["string"]
  },
  "findings": [
    {
      "id": "F-001",
      "rule_id": "SRS-E02",
      "artifact": "SRS|USECASE|CLASS|DB|STATE|CROSS|AI",
      "type": "DEFECT|GAP|AMBIGUITY|CONFLICT|RISK|QUESTION|SUGGESTION",
      "severity": "S1|S2|S3|S4",
      "confidence": "HIGH|MED|LOW",
      "title": "string",
      "locations": ["string"],
      "evidence": ["string"],
      "problem": "string",
      "impact": "string",
      "recommendation": "string",
      "needs_confirmation_from": "string|null",
      "needs_verification": false
    }
  ],
  "open_questions": [{"id": "Q-001", "text": "string", "related_findings": ["F-001"], "owner": "string"}],
  "traceability": {
    "fr_without_uc": ["string"],
    "uc_without_fr": ["string"],
    "state_enum_mismatch": ["string"]
  }
}
```

Ràng buộc: `evidence` không rỗng với mọi finding khác QUESTION; `severity=S1` ⇒ `confidence=HIGH`; `confidence=LOW` ⇒ `type=QUESTION`.

## F. Quy tắc diễn đạt

- Câu ngắn, chủ động, nêu **điều gì → vì sao quan trọng → sửa thế nào**.
- Không dùng "có lẽ/hình như" trong DEFECT; nếu cần hedge thì đó là QUESTION.
- Trích dẫn bằng dấu nháy, không diễn giải thay bằng chứng.
- Mỗi finding một vấn đề; liệt kê nhiều vị trí trong "Vị trí".
- Đề xuất sửa luôn **có thể thực hiện** và ghi rõ phần cần PO quyết định.
- Tiếng Việt tự nhiên; giữ thuật ngữ kỹ thuật tiếng Anh (precondition, guard, cardinality, idempotency...).
- Độ dài: tỷ lệ với độ sâu. Không lặp lại cùng nội dung ở Kết luận, Tổng quan và Finding.
