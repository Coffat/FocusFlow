# Detailed DDD Domain Model Profile

## 1. Mục đích

Profile này dùng để phân tích và thiết kế mô hình miền chi tiết khi nghiệp vụ có đủ độ phức tạp để hưởng lợi từ DDD. Không áp dụng máy móc cho mọi CRUD application.

Một Detailed DDD Domain Model có thể mô tả Entity, Value Object, Aggregate, invariant, hành vi và các tactical patterns khác. Nó không đồng nghĩa với một Software Design Class Diagram có mọi method, visibility, interface và framework dependency.

## 2. Phạm vi vào/ra

| Đưa vào | Mặc định loại khỏi domain model |
|---|---|
| Identity nghiệp vụ | Database PK/FK thuần persistence |
| Domain value types | ORM navigation/proxy |
| Business invariant | Controller/route/HTTP status |
| Aggregate boundary | Database index/column type |
| Behavior và lifecycle | Framework annotations |
| Domain event/policy/specification khi có ý nghĩa | Queue/client/database adapter |
| Domain Service khi cần | DTO/API request-response, trừ khi đang mô tả design |
| External Aggregate ID reference | Hash, secret, token lưu trữ kỹ thuật |

Không loại domain concept chỉ vì persistence hiện tại lưu nó dưới dạng JSON, bảng con hoặc một cột scalar.

## 3. Phân loại tactical patterns

Với từng ứng viên, phân loại và ghi lý do. Tham khảo `ddd-tactical-patterns.md`.

### 3.1. Entity

Ghi:

- Identity type/meaning.
- Lifecycle và state.
- Hành vi có trách nhiệm.
- Invariants được bảo vệ.
- Aggregate membership/root status.
- Relationships và reference ra ngoài.

### 3.2. Value Object

Ghi:

- Giá trị cấu thành và ý nghĩa.
- Equality semantics theo value.
- Invariants/validation.
- Immutability expectation.
- Owner hoặc vị trí được sử dụng.

Không xem database ID là bằng chứng đủ để biến VO thành Entity. Ngược lại, nếu đối tượng có identity/lifecycle nghiệp vụ thì không giữ nó là VO chỉ vì code hiện tại dùng record/JSON.

### 3.3. Association Class

Ghi hai đầu quan hệ, data/behavior thuộc relationship, multiplicity và lifecycle. Nếu quan hệ có identity mạnh, hãy cân nhắc promoted Entity.

### 3.4. Enumeration

Enum phải phản ánh một tập giá trị nghiệp vụ có ý nghĩa và phạm vi rõ. Tránh enum gom các khái niệm khác nghĩa (ví dụ một `Level` vừa là trình độ người học vừa là độ khó nội dung) hoặc enum chứa giá trị test/adapter chỉ vì code có nó.

Enum có thể được triển khai khác nhau ở database; việc mapping không quyết định semantics miền.

## 4. Aggregate Map

Aggregate là consistency boundary, không phải cụm class được gom cho đẹp hoặc một bảng cha với bảng con.

Với mỗi Aggregate candidate, ghi:

| Aggregate | Root | Members | Invariants | Update use cases/transactions | Evidence | Status |
|---|---|---|---|---|---|---|

Kiểm tra:

1. Có ít nhất một Entity root.
2. Root là cổng cập nhật bên ngoài cho các thành viên thuộc Aggregate.
3. Members thực sự cần consistency/invariant cùng root; không đưa vào chỉ vì có FK hoặc quan hệ one-to-many.
4. Aggregate không quá rộng; chỉ chứa phần cần consistency boundary chung.
5. Aggregate khác nhau có thể được cập nhật theo transaction/use case riêng.
6. External Aggregate references nên dùng identity/ID theo nguyên tắc DDD phổ biến, trừ khi có lý do và kiến trúc cụ thể khác.
7. Một Entity không đồng thời được tuyên bố là Aggregate Root độc lập và child member của Aggregate khác trong cùng mô hình ownership. Nếu thấy Composition giữa hai root, điều tra xem đó là quan hệ lifecycle UML, aggregate membership hay mô tả sai; không tự kết luận chỉ từ ký hiệu.
8. Aggregate Root không nhất thiết tương đương với một UML class được vẽ composition với tất cả members. Biểu diễn bằng stereotype, note, package hoặc Aggregate Map nếu UML composition không đúng ngữ nghĩa.
9. Không suy ra Aggregate từ database cascade delete, table ownership hoặc package structure.

## 5. Relationships trong DDD model

- Within one Aggregate: associations có thể thể hiện child relationship; chỉ dùng Composition nếu semantics ownership/lifecycle phù hợp.
- Across Aggregates: mô hình identity/reference và ghi rõ consistency boundary. Domain model có thể biểu diễn ID type thay vì object association.
- Across Bounded Contexts: thể hiện integration contract/context map; không để class của Context này trực tiếp mô hình hóa toàn bộ nội bộ Context kia.
- Association Class: dùng khi dữ liệu thuộc chính quan hệ; xem xét promoted Entity nếu có independent lifecycle.

Lưu ý: “reference by ID” là guidance về DDD/consistency boundary, không phải yêu cầu của UML notation. Domain ID không đồng nghĩa database FK.

## 6. Invariants và business rules

Với mỗi invariant quan trọng, ghi:

| Rule ID | Rule | Scope | Enforcer | Trigger/operation | Source | Status |
|---|---|---|---|---|---|---|

Phân loại phạm vi:

- Entity/VO invariant: luôn đúng đối với object.
- Aggregate invariant: phải được bảo vệ trong consistency boundary của root.
- Cross-Aggregate policy: phối hợp qua application service/domain policy/eventual consistency khi phù hợp; không giả định có thể bảo vệ bằng một transaction nội bộ Aggregate.
- Context-level rule: quy tắc thuộc một Bounded Context.

Không gán tất cả validation cho Aggregate Root. Phân bổ theo nơi có đủ thông tin và trách nhiệm để bảo vệ rule.

## 7. Behavior và operation

Operation nên thể hiện domain intent, ví dụ `approveProposal()`, `rescheduleTask(...)`, `recordStudyResult(...)`, thay vì `setStatus(...)` nếu có quy tắc chuyển trạng thái.

Mỗi operation quan trọng có thể ghi:

- Preconditions/guard.
- Input và output.
- State transition.
- Invariant được bảo vệ.
- Domain event phát sinh (nếu có).
- Failure condition.

Không cần hiển thị mọi operation trên sơ đồ. Có thể giữ bảng behavior specification riêng.

## 8. State lifecycle

Tạo bảng chuyển trạng thái khi lifecycle có nhiều điều kiện/guard, side effect hoặc trạng thái kết thúc khác nhau. Không dùng số lượng enum value làm tiêu chí duy nhất.

| Current state | Command/event | Guard | Next state | Side effect/domain event | Source |
|---|---|---|---|---|---|

Phải phân biệt:

- Status nghiệp vụ.
- Technical processing status.
- Payment/authorization status từ external provider.
- UI display state.

Không gom các trạng thái khác bản chất vào một enum.

## 9. Domain Service, Policy, Event và các abstraction khác

- Domain Service: domain behavior không tự nhiên thuộc về một Entity/VO. Nên đặt tên bằng hành động nghiệp vụ, xác định input/output và rule.
- Application Service: điều phối use case, transaction và dependency; không nhầm với Domain Service.
- Domain Event: sự kiện đã xảy ra, đặt tên theo past tense, có ý nghĩa trong domain.
- Domain Policy: định nghĩa phản ứng/decision khi điều kiện hoặc event xảy ra.
- Specification: đóng gói tiêu chí nghiệp vụ có thể tái sử dụng hoặc kết hợp.
- Factory: encapsulate quá trình tạo phức tạp khi constructor đơn giản không đủ.
- Repository: abstraction truy xuất Aggregate, thường là design/architecture concern chứ không phải domain Entity.

Chỉ thêm khi giúp giải quyết complexity thực tế; không bắt buộc mọi model phải có tất cả pattern.

## 10. Traceability và completeness

Mỗi concept/rule/relationship quan trọng nên nối về một hoặc nhiều nguồn. Kiểm tra hai chiều:

- Requirement/Use Case quan trọng đã được phản ánh trong model hoặc được giải thích vì sao không cần class chưa?
- Class/operation/rule có trách nhiệm và nguồn gốc rõ chưa?
- Có khái niệm dùng trong nhiều Use Case nhưng chưa có trong glossary/model không?
- Có class không được sử dụng nhưng vẫn có lý do nghiệp vụ (audit/event/policy/history) không?

Không kết luận class thừa chỉ vì không xuất hiện trực tiếp trong một Use Case.

## 11. Output tối thiểu

1. Scope, assumptions và evidence baseline.
2. Domain vocabulary/classifier inventory.
3. Bounded Context analysis (nếu áp dụng).
4. Aggregate Map.
5. Detailed domain diagrams.
6. Relationship/multiplicity register.
7. Invariant/business rule table.
8. State lifecycle table khi cần.
9. Domain Service/Event/Policy/Specification catalog khi cần.
10. Traceability và open issues.
