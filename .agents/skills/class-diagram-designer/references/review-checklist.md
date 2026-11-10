# Review Checklist

Dùng checklist theo profile. Không cần đánh dấu mọi mục “đạt” nếu mục đó không áp dụng; ghi N/A kèm lý do khi có nguy cơ gây hiểu nhầm.

## 1. Critical

- [ ] Diagram có đúng profile/mục đích không? Có trộn Domain Overview, DDD detail, ERD và implementation không?
- [ ] Class có identity/lifecycle bị phân loại sai rõ ràng không?
- [ ] Có Aggregate Root bị mô tả đồng thời là member của Aggregate khác trong cùng ownership model không?
- [ ] Có composition/shared aggregation được dùng mà không có căn cứ ownership/lifecycle không?
- [ ] Multiplicity có mâu thuẫn với rule hoặc Use Case không?
- [ ] Có quan hệ/method/attribute được trình bày như CONFIRMED dù nguồn không hỗ trợ không?
- [ ] Có cross-context class coupling làm rò rỉ model hoặc nhầm lẫn Context ownership không?
- [ ] Có trộn domain ID với database FK/PK hoặc persistence details theo cách làm sai domain semantics không?
- [ ] Có derived attribute vừa được mô tả computed vừa bị mutate trực tiếp mà không có cache/source-of-truth rule không?
- [ ] Có business invariant quan trọng nhưng không có nơi chịu trách nhiệm bảo vệ không?

## 2. Major

- [ ] Có class bị tạo chỉ từ danh từ hoặc database table mà không có ý nghĩa nghiệp vụ?
- [ ] Có Entity/VO/Association Class bị phân loại thiếu căn cứ?
- [ ] Có cùng một thuật ngữ được dùng cho hai nghĩa khác nhau mà không phân biệt Context?
- [ ] Có package bị nhầm thành Bounded Context?
- [ ] Có Context count được áp đặt trước khi phân tích subdomain/model boundary?
- [ ] Có Aggregate quá lớn hoặc không dựa vào transaction/invariant?
- [ ] Có Association Class phù hợp nhưng bị thay bằng attribute ở sai phía?
- [ ] Có operation chỉ là getter/setter/CRUD hoặc `markX()` không có rule?
- [ ] Có service/application orchestration/domain logic bị trộn trách nhiệm?
- [ ] Có enum trộn các khái niệm khác nghĩa hoặc chứa giá trị technical/test-only?
- [ ] Có state lifecycle quan trọng nhưng thiếu guard/transition/terminal state?
- [ ] Có requirement/Use Case quan trọng chưa được phản ánh hoặc giải thích?
- [ ] Có class quan trọng nhưng không có purpose/owner/source rõ ràng?

## 3. Minor

- [ ] Tên class/attribute/operation chưa nhất quán.
- [ ] Role names hoặc association labels thiếu rõ ràng.
- [ ] Diagram quá dày, nhiều đường cắt/giao nhau.
- [ ] Stereotype tùy chỉnh không có legend.
- [ ] Enum catalog hoặc note trùng lặp.
- [ ] Có thuộc tính kỹ thuật không cần thiết ở profile hiện tại.
- [ ] Multiplicity đúng nhưng trình bày khó đọc.
- [ ] PlantUML/Mermaid source chưa nhất quán.

## 4. Checklist riêng Domain Overview

- [ ] Diagram trả lời được “hệ thống có những khái niệm nghiệp vụ lớn nào?”
- [ ] Phạm vi domain/system boundary rõ.
- [ ] Chỉ hiển thị các concept cần thiết cho overview.
- [ ] Không nhồi tất cả enum literals, methods, technical fields và database mapping.
- [ ] Context grouping được hỗ trợ bởi domain analysis hoặc được đánh dấu proposed.
- [ ] Relationship và multiplicity được grounded hoặc đánh dấu OPEN.
- [ ] Có danh sách detail được chuyển sang diagram/tài liệu khác.
- [ ] Không hiểu nhầm “không xuất hiện trong overview” thành “không tồn tại trong domain”.

## 5. Checklist riêng Detailed DDD Model

- [ ] Entity/VO phân biệt theo identity/equality semantics.
- [ ] Aggregate Map nêu root, members, invariants và update operations.
- [ ] Root là cổng cập nhật của Aggregate.
- [ ] Aggregate boundary dựa trên consistency/invariants, không dựa vào schema/package.
- [ ] Cross-Aggregate reference được mô tả rõ; domain ID không bị nhầm với database FK.
- [ ] Domain Service không thay thế behavior tự nhiên của Entity/VO.
- [ ] Application Service và Infrastructure Service không bị nhầm thành Domain Service.
- [ ] Domain Events là business facts, không chỉ là technical log/messages.
- [ ] State transitions có guard và source khi cần.
- [ ] Invariants có owner/enforcer rõ.

## 6. Checklist riêng Software/Implementation Design

- [ ] Class/interface/abstract class và implementation được phân loại đúng.
- [ ] Visibility, navigability và dependency phản ánh design/code target.
- [ ] Type và operation signature phù hợp ngôn ngữ/framework nếu mục tiêu yêu cầu.
- [ ] Không đưa giả định nghiệp vụ vào diagram implementation nếu chưa xác nhận.
- [ ] Reverse-engineered diagram được phân biệt với target design.

## 7. Cách ghi finding

Mỗi finding cần có:

| Field | Nội dung |
|---|---|
| ID | CR-01 / MJ-01 / MN-01 |
| Severity | Critical / Major / Minor |
| Location | Class, relationship, section hoặc dòng trong file |
| Evidence | Source hoặc mô tả mâu thuẫn |
| Problem | Điều gì sai/chưa rõ |
| Impact | Hệ quả đối với domain/design/code/review |
| Recommendation | Cách sửa, tránh giải pháp áp đặt |
| Confidence | CONFIRMED / INFERRED / PROPOSED / OPEN |

## 8. Tiêu chí kết luận

- **Ready for review:** không còn Critical; Major đã được xử lý hoặc có owner chấp nhận/open issue.
- **Ready for approval:** scope, source baseline, relationships, key invariants và open issues đã được người có thẩm quyền xác nhận; không còn mâu thuẫn trọng yếu chưa xử lý.
- **Not ready:** còn Critical hoặc các quyết định cốt lõi (identity, lifecycle, Aggregate boundary, multiplicity, Context boundary) đang bị suy diễn.

Không tuyên bố “chuẩn 100%” hoặc “đã đúng UML/DDD” chỉ dựa vào việc diagram render thành công.
