# Modeling Guide — Phân tích trước khi vẽ

## 1. Mục tiêu

Class Diagram phải là kết quả của phân tích, không phải công cụ để hợp thức hóa danh từ trong SRS hoặc tên bảng trong database. Quy trình này áp dụng cho Domain Overview, Detailed DDD Domain Model và Software Design, nhưng độ sâu đầu ra khác nhau.

## 2. Evidence handling

### 2.1. Các trạng thái bằng chứng

| Trạng thái | Ý nghĩa | Cách trình bày |
|---|---|---|
| `CONFIRMED` | Nguồn có thẩm quyền nêu trực tiếp | Có thể dùng làm baseline; trích dẫn source/ID |
| `INFERRED` | Suy luận từ nhiều phần thông tin nhất quán | Ghi rõ lập luận và cần xác nhận ở đâu |
| `PROPOSED` | Phương án kiến trúc/mô hình do Agent đề xuất | Không trình bày như yêu cầu đã được duyệt |
| `OPEN` | Thiếu thông tin hoặc có mâu thuẫn chưa giải quyết | Dùng TBD/OPEN; không tự điền |

Mỗi class quan trọng, relationship quan trọng, multiplicity, lifecycle, Aggregate boundary và Bounded Context nên có evidence status khi quyết định chưa hiển nhiên.

### 2.2. Nguồn và độ thẩm quyền

Không tồn tại một thứ tự ưu tiên cố định đúng cho mọi dự án. Hãy xác định thẩm quyền theo quy trình quản trị dự án. Thông thường:

- Business policy/requirement được chủ nghiệp vụ phê duyệt: bằng chứng về ý định nghiệp vụ.
- SRS/BRD đã baseline và Use Case được duyệt: bằng chứng về phạm vi và hành vi yêu cầu.
- ADR đã được chấp thuận: bằng chứng về quyết định kiến trúc, không tự thay thế yêu cầu nghiệp vụ.
- API contract: bằng chứng về hợp đồng tích hợp.
- Schema và source code hiện tại: bằng chứng về implementation hiện tại, không đủ để chứng minh thiết kế nghiệp vụ đúng.
- Meeting note, chat, draft: có thể hữu ích nhưng phải xác nhận mức độ chính thức.

Nếu hai nguồn cùng thẩm quyền mâu thuẫn, tạo conflict record thay vì tự chọn.

### 2.3. Mẫu conflict record

| Conflict ID | Nguồn A | Nguồn B | Vấn đề | Tác động lên model | Cách xử lý |
|---|---|---|---|---|---|
| CF-01 | SRS §x | ADR-x §y | Lifecycle khác nhau | Ảnh hưởng status/operation | OPEN — cần owner xác nhận |

### 2.4. Không bịa traceability

- Dùng đúng ID Use Case, requirement, business rule, ADR và file path có trong nguồn.
- Nếu không có ID, dùng tên heading hoặc mô tả nguồn, không tự sinh ID giả.
- Nếu không thể đọc line/page, trích tên file + heading và ghi giới hạn.
- Một class có thể hỗ trợ nhiều Use Case; một Use Case có thể dùng nhiều class.
- Không yêu cầu mọi class phải xuất hiện trực tiếp trong Use Case. Một số class có thể phục vụ invariant, shared concepts, event hoặc persistence boundary.

## 3. Tìm class ứng viên

Bắt đầu từ:

1. Thuật ngữ trong glossary/Ubiquitous Language.
2. Danh từ và cụm danh từ trong requirements, business rules và Use Case.
3. Những đối tượng được tạo, đọc, sửa, hoàn tất, hủy, lưu lịch sử hoặc cần audit.
4. Những khái niệm tham gia vào quyết định/quy tắc nghiệp vụ.
5. Những mối quan hệ có dữ liệu hoặc lifecycle riêng.

Danh từ chỉ là ứng viên. Với mỗi ứng viên, hỏi:

- Nó mô tả một khái niệm nghiệp vụ hay chỉ là dữ liệu/implementation detail?
- Có identity nghiệp vụ không? Identity có ổn định dù thuộc tính thay đổi không?
- Có lifecycle hoặc trạng thái riêng không?
- Có behavior/invariant thuộc về nó không?
- Có thể thay thế bằng thuộc tính/VO của class khác không?
- Nó có phải chỉ là vai trò/alias của khái niệm đã tồn tại không?
- Nó có phải actor/external system thay vì classifier trong domain model không?
- Nó có phải request/response DTO, persistence record, API payload hoặc adapter không?

### 3.1. Dấu hiệu Entity

- Có identity nghiệp vụ xuyên thời gian.
- Có thể thay đổi thuộc tính nhưng vẫn là cùng một đối tượng.
- Có lifecycle hoặc các hành vi gắn với identity đó.
- Có quy tắc cần bảo vệ qua các lần thay đổi.

### 3.2. Dấu hiệu Value Object

- Không cần identity độc lập.
- Hai instance có cùng giá trị được xem là tương đương theo ngữ nghĩa domain.
- Thể hiện một khái niệm bằng giá trị/thuộc tính; thường bất biến.
- Có thể chứa validation và behavior, không chỉ là một struct dữ liệu.

### 3.3. Dấu hiệu Association Class

- Dữ liệu thuộc về chính mối quan hệ giữa hai hoặc nhiều classifier.
- Dữ liệu không có ý nghĩa độc lập ở một đầu quan hệ.
- Có thể có lifecycle/hành vi riêng của relationship.
- Nếu quan hệ có identity/lifecycle mạnh, xem xét mô hình nó thành Entity liên kết thay vì chỉ dùng association class.

### 3.4. Dấu hiệu class không nên tạo

- Chỉ là một trường dữ liệu không có identity, behavior hay cấu trúc phức tạp.
- Chỉ là tên khác của class có sẵn.
- Chỉ đại diện một API request/response hoặc database row.
- Chỉ được tạo ra vì framework/ORM yêu cầu.
- Không có trách nhiệm, dữ liệu hoặc quan hệ có ý nghĩa.
- Actor hoặc hệ thống ngoài phạm vi được đưa nhầm thành domain entity.

Không loại class chỉ vì nó ít thuộc tính hoặc ít method; child entity trong Aggregate có thể dựa vào root để bảo vệ invariant.

## 4. Phân biệt các loại mô hình

| Thành phần | Domain Overview | Detailed Domain Model | Software/Implementation Design |
|---|---|---|---|
| Entity | Tên và quan hệ cốt lõi | Identity, behavior, lifecycle, invariant | Class implementation detail nếu cần |
| Value Object | Chỉ khi là khái niệm trọng yếu | Type, value semantics, invariant | Class/record/struct theo công nghệ |
| Aggregate | Nhóm/ranh giới có thể chú thích | Root, members, invariants, update boundary | Package/transaction implementation khi cần |
| Domain Service | Thường ẩn hoặc ghi catalog | Có thể biểu diễn trách nhiệm | Class/interface và dependency nếu cần |
| Application Service | Không | Không thuộc core domain model | Điều phối use case |
| Repository | Không | Chỉ mô tả vai trò nếu cần | Interface/implementation |
| DTO/API Model | Không | Không | Có |
| Database FK/PK | Không | Không; domain identifier là trường hợp riêng | Có trong persistence model/ERD |

## 5. Relationship discovery

Trước khi chọn ký hiệu, xác định bản chất:

1. **Business association:** hai khái niệm có liên hệ nghiệp vụ.
2. **Ownership/lifecycle:** một object có sở hữu và kiểm soát vòng đời object khác không?
3. **Aggregate membership:** object nằm trong cùng consistency boundary không?
4. **Identity reference:** object giữ định danh của Aggregate khác hay điều hướng trực tiếp?
5. **Implementation dependency:** một class dùng class/interface khác qua parameter, field, local variable hoặc service call?

Không dùng một đường UML để diễn đạt tất cả các ý này. Chẳng hạn, composition không tự chứng minh Aggregate membership; dependency không tự chứng minh bounded-context relationship.

## 6. Attributes và operations

### 6.1. Attributes

Chỉ đưa thuộc tính có ý nghĩa ở profile đã chọn. Với mỗi thuộc tính quan trọng, ghi:

- Tên domain language.
- Type ở mức phù hợp.
- Multiplicity nếu nhiều giá trị.
- Ý nghĩa/đơn vị nghiệp vụ.
- Constraint (range, format, optionality, uniqueness) khi có bằng chứng.
- Nguồn/trạng thái bằng chứng khi chưa chắc chắn.

Không đưa mặc định vào Domain Overview: `createdAt`, `updatedAt`, UUID kỹ thuật, FK/PK, password hash, refresh token, access token, encryption key, cache field, retry counter hoặc telemetry. Các trường này có thể hợp lệ trong Software/Implementation/Data Model nếu mục tiêu yêu cầu.

**Không nhầm domain identifier với database FK:** `CustomerId` có thể là domain value type/reference trong Detailed DDD Model. `customer_id` là tên cột persistence. Hai thứ có thể ánh xạ với nhau nhưng không đồng nghĩa.

### 6.2. Stored và derived attributes

- UML derived property dùng dấu `/`, ví dụ `/totalMinutes`.
- Nếu một giá trị được tính từ dữ liệu khác, hãy chỉ rõ nguồn tính.
- Không vừa đánh dấu derived vừa mô tả thao tác mutate trực tiếp trừ khi có cached/materialized value và quy tắc đồng bộ rõ.
- Khi cùng một thông tin có nhiều nguồn, chỉ định source of truth.

### 6.3. Operations

Operation phù hợp khi:

- Bảo vệ invariant hoặc thay đổi state hợp lệ.
- Thể hiện hành vi nghiệp vụ của Entity/VO.
- Là trách nhiệm design cần được thể hiện ở Software Design.
- Có input, output, điều kiện hoặc side effect có ý nghĩa.

Không đưa getter/setter, CRUD method máy móc hoặc `markX()` chỉ bọc một phép gán nếu không có rule. Không dồn mọi nghiệp vụ vào Service class chỉ vì thuận tiện.

## 7. Multiplicity

Đối với mỗi association, hỏi riêng hai chiều:

- Một instance A liên kết với tối thiểu/tối đa bao nhiêu instance B?
- Một instance B liên kết với tối thiểu/tối đa bao nhiêu instance A?

Các dạng thường dùng: `1`, `0..1`, `0..*`/`*`, `1..*`, `2..5`.

Kiểm tra thêm:

- Quan hệ có bắt buộc ngay lúc tạo hay chỉ sau một bước workflow?
- Có trạng thái draft/unassigned cho phép chưa liên kết không?
- Xét toàn bộ lifecycle hay chỉ một trạng thái?
- Có uniqueness constraint không?
- Cardinality là business invariant hay chỉ là giới hạn UI/database?

Nếu yêu cầu chỉ cho biết “một Roadmap có nhiều Milestone” mà không xác định tối thiểu một hay có thể bằng không, không tự động chọn `1..*`; đưa ra OPEN hoặc đề xuất rõ ràng.

## 8. Phân tách diagram

Tách theo câu hỏi người đọc cần trả lời, không theo một con số lớp cố định. Dấu hiệu cần tách:

- Nhiều đường giao cắt làm mất khả năng đọc.
- Nhiều khái niệm thuộc các quy trình nghiệp vụ khác nhau.
- Người đọc overview bị kéo vào chi tiết persistence/design.
- Một nhóm class có thể được hiểu độc lập trong một context/aggregate.

Giữ overview làm bản đồ; detailed diagrams là nơi mở rộng. Mọi sơ đồ con phải có tên, phạm vi và liên kết về overview.
