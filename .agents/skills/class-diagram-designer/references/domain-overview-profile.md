# Domain Overview Profile

## 1. Định nghĩa

Trong skill này, **Domain Overview Class Diagram** là UML Class Diagram ở mức conceptual/overview nhằm giúp người đọc hiểu cấu trúc nghiệp vụ tổng thể. Đây không phải một diagram type độc lập được OMG chuẩn hóa.

Nó trả lời:

- Hệ thống xử lý những khái niệm nghiệp vụ lớn nào?
- Những khái niệm đó liên hệ với nhau ra sao?
- Có những nhóm nghiệp vụ/Bounded Context nào đã được xác nhận hoặc đang đề xuất?
- Người đọc nên xem diagram chi tiết nào để hiểu sâu hơn?

Nó không nhằm trả lời mọi chi tiết triển khai.

## 2. Nội dung nên có

### 2.1. Class/concept

Ưu tiên:

- Entity hoặc domain concept có vai trò trung tâm.
- Value Object nếu nó là khái niệm nghiệp vụ độc lập và cần thiết để hiểu mô hình.
- Association class chỉ khi dữ liệu của relationship là thiết yếu để hiểu domain overview.
- Abstract concept hoặc interface nghiệp vụ khi có giá trị giải thích rõ ràng.

Không bắt buộc đưa tất cả classifier của Detailed DDD Model lên overview.

### 2.2. Attributes

Mặc định chỉ hiển thị tên class. Có thể thêm một đến ba thuộc tính có ý nghĩa để phân biệt concept hoặc làm rõ nghiệp vụ. Không đặt giới hạn cứng; phải có lý do khi đưa thêm.

Không hiển thị mặc định:

- PK/FK, UUID kỹ thuật, database column name.
- `createdAt`/`updatedAt` phổ quát.
- Password hash, token, secret, encryption metadata.
- ORM annotation, index, nullable database column.
- Cache, telemetry, retry, queue metadata.

### 2.3. Operations

Mặc định không hiển thị operations. Chỉ thêm khi một hành vi nghiệp vụ cấp cao giúp người đọc hiểu trách nhiệm class và không làm overview quá chi tiết.

### 2.4. Enumerations

Dùng enum ở type nếu cần, ví dụ `status: GoalStatus`, nhưng không cần vẽ toàn bộ enum và literal values. Tạo Enum Catalog riêng khi người đọc cần tra cứu.

### 2.5. Relationships

Hiển thị các association quan trọng và multiplicity khi có bằng chứng. Không thêm đường nối chỉ vì hai class cùng nằm trong một module hoặc cùng có FK trong database.

Association label nên dùng động từ/cụm động từ nghiệp vụ như `contains`, `targets`, `is scheduled in`, `records`, `evaluates`, nhưng phải phản ánh đúng ngữ nghĩa.

## 3. Bounded Context và package trên overview

- Có thể dùng UML Package để nhóm khái niệm.
- Chỉ gắn tên `«BoundedContext»` khi đó thực sự là một Bounded Context được phân tích; nếu chưa xác nhận, ghi `«ProposedContext»` hoặc trong chú giải ghi “candidate grouping”. Đây là stereotype quy ước của dự án, không phải stereotype UML mặc định.
- Không đặt tên package hiện tại của source code rồi tự kết luận đó là Context.
- Không bắt buộc có nhiều Context. Một domain model thống nhất cũng là phương án có thể đúng.
- Nếu cần giải thích quan hệ giữa các Context, tạo Context Map riêng thay vì nhồi mọi chi tiết tích hợp vào class associations.

## 4. Quy tắc hình thức

- Tên class bằng tiếng Anh nếu mô hình dùng trực tiếp cho code; tiếng Việt nếu phục vụ business audience. Một sơ đồ phải nhất quán.
- Dùng stereotype `«Entity»`/`«ValueObject»` khi nó giúp phân biệt, nhưng chú thích rằng đây là stereotype DDD/project-defined, không phải metaclass UML mặc định.
- Không gắn `«AggregateRoot»` cho tất cả class quan trọng. Chỉ gắn khi Aggregate đã được phân tích.
- Có thể lược bỏ visibility và operation compartments.
- Không thể hiện dependency đến enum chỉ để khai báo kiểu thuộc tính.
- Không dùng Composition để thay thế association khi chưa chứng minh ownership/lifecycle.

## 5. Quy trình tạo overview

1. Chốt domain/system boundary và audience.
2. Đọc các nguồn nghiệp vụ có liên quan.
3. Lập inventory domain concepts với evidence status.
4. Gom khái niệm trùng nghĩa; tách các khái niệm khác nghĩa dù cùng tên.
5. Xác định subdomain và candidate Bounded Context nếu phù hợp.
6. Chọn concepts quan trọng nhất để hiển thị; ghi lại concepts bị chuyển sang detailed diagrams và lý do.
7. Xác định relationships và multiplicity; đánh dấu OPEN nếu chưa đủ căn cứ.
8. Vẽ overview và kiểm tra nó có trả lời được câu hỏi tổng thể mà không trở thành ERD/design diagram không.
9. Cung cấp danh mục sơ đồ chi tiết cần có.

## 6. Đầu ra chuẩn

### A. Scope

- Domain/system boundary.
- Audience và mục đích.
- Profile: Domain Overview Class Diagram.
- Các giả định và giới hạn nguồn.

### B. Domain concept inventory

| Concept | Classification | Group/Context | Purpose | Evidence status | Source |
|---|---|---|---|---|---|

### C. Diagram

Một diagram hoặc nhóm diagram overview. Khi hệ thống lớn, có thể tạo:

- System Domain Overview.
- Context-level overview cho từng nhóm.
- Context Map tách riêng.

### D. Relationship register

| From | Relationship | To | Multiplicity A→B | Multiplicity B→A | Evidence | Status |
|---|---|---|---|---|---|---|

### E. Detail deliberately omitted

| Concept/detail | Đưa sang đâu | Vì sao không nằm trong overview |
|---|---|---|

Ví dụ: enum literals → Enum Catalog; Aggregate members → Detailed DDD diagram; method signature → Software Design diagram; persistence fields → ERD.

### F. Open questions

Chỉ liệt kê những câu hỏi có thể làm thay đổi domain model, relationship, multiplicity, lifecycle hoặc Context boundary.

## 7. Tiêu chí đạt

- Người mới đọc có thể giải thích được các khái niệm và mối quan hệ lớn.
- Diagram không bị chi phối bởi PK/FK, database tables, framework types hoặc method kỹ thuật.
- Không có Context/aggregate được khẳng định chỉ dựa trên tên package.
- Mọi multiplicity quan trọng đều có căn cứ hoặc được đánh dấu OPEN.
- Không nhầm lẫn giữa “không hiển thị trong overview” và “không tồn tại trong domain”.
