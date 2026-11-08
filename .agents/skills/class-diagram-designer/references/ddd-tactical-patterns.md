# DDD Tactical Patterns — Hướng dẫn phân loại

Tài liệu này giúp nhận diện pattern. Đây không phải danh sách bắt buộc phải có trong mọi dự án.

## 1. Entity

Entity được xác định bởi identity nghiệp vụ liên tục, không chỉ bởi tập thuộc tính hiện tại. Tên, địa chỉ hoặc trạng thái có thể thay đổi mà vẫn là cùng một Entity.

Câu hỏi:

- Identity là gì và ai tạo/cấp identity?
- Identity có ổn định qua lifecycle không?
- Có behavior/invariant cần được bảo vệ không?
- Có trạng thái hoặc lifecycle nghiệp vụ không?

Không kết luận một class là Entity chỉ vì database có primary key. Một record có ID kỹ thuật vẫn có thể chỉ là persistence record.

## 2. Value Object

Value Object được xác định bởi giá trị, không bởi identity riêng. Hai instance tương đương khi các giá trị cấu thành theo semantics của domain là tương đương. VO thường immutable để tránh thay đổi giá trị âm thầm và dễ reasoning.

Câu hỏi:

- Nếu hai instance có cùng giá trị, domain có xem chúng tương đương không?
- Có cần theo dõi một instance cụ thể xuyên thời gian không?
- Thay đổi giá trị có nghĩa là tạo giá trị mới không?
- Các thành phần và invariant của giá trị là gì?

Một VO có thể có behavior (validation, calculation, comparison). Persistence lưu VO trong JSON, embedded columns hoặc table riêng không làm thay đổi bản chất domain.

## 3. Aggregate và Aggregate Root

Aggregate nhóm các Entity/VO cần được duy trì consistency theo một boundary. Root bảo vệ invariant và là entry point cho thay đổi từ bên ngoài.

Câu hỏi:

- Các object nào bắt buộc phải đúng cùng nhau trong cùng một business transaction?
- Có rule nào phải được kiểm tra nguyên tử khi cập nhật?
- Có thể cập nhật các object riêng lẻ mà vẫn hợp lệ không?
- Nếu tách boundary, có chấp nhận eventual consistency không?
- Root nào có đủ thông tin để bảo vệ invariant?

Không thiết kế Aggregate dựa trên quan hệ bảng cha-con, cascade delete, số lượng class hoặc mong muốn load một object graph đầy đủ.

## 4. Association Class và Entity liên kết

Dùng Association Class khi attribute/hành vi thuộc chính mối quan hệ giữa hai hay nhiều classifier. Ví dụ, `Enrollment` có thể ghi ngày đăng ký và điểm của quan hệ Student–Course.

Đặt câu hỏi thêm:

- Relationship có lifecycle riêng không?
- Có cần định danh và truy vấn độc lập không?
- Có thể tồn tại sau khi một phía thay đổi/hủy không?
- Có hành vi nghiệp vụ riêng không?

Nếu có identity/lifecycle đáng kể, cân nhắc mô hình hóa thành Entity liên kết. Association Class là construct UML; việc chọn nó hay Entity trong DDD còn phụ thuộc semantics và cách quản lý vòng đời.

## 5. Enumeration

Enum phù hợp với một tập giá trị hữu hạn và có ngữ nghĩa thống nhất trong một bounded context.

Tránh:

- Enum quá rộng gom nhiều khái niệm chỉ vì cùng dùng từ “Type”, “Level”, “Status”.
- Giá trị dành riêng cho unit test, mock provider hoặc adapter lọt vào domain enum production mà không có ý nghĩa nghiệp vụ.
- Giá trị default dựa trên model/vendor hiện tại nhưng bị coi là business invariant.
- Dùng enum để thay thế một khái niệm có lifecycle, identity hoặc cấu trúc phức tạp.

Enum nên có owner/context và định nghĩa literal rõ khi cần catalog.

## 6. Domain Service

Dùng khi một hành vi nghiệp vụ:

- Có ý nghĩa domain rõ ràng.
- Không tự nhiên thuộc về một Entity/VO cụ thể.
- Có thể đặt tên bằng ngôn ngữ nghiệp vụ.
- Không chỉ là CRUD orchestration hoặc framework wrapper.

Ghi rõ input, output, business rule, lỗi nghiệp vụ và dependency cần thiết. Domain Service thường không có identity/lifecycle riêng và thường stateless, nhưng không dùng “stateless” làm định nghĩa duy nhất.

Phân biệt:

| Loại | Trách nhiệm |
|---|---|
| Domain Service | Logic/nghiệp vụ không thuộc tự nhiên một Entity/VO |
| Application Service | Điều phối use case, transaction, repository và ports |
| Infrastructure Service | Tích hợp kỹ thuật: email, HTTP, queue, storage, calendar adapter... |

Không đưa Domain Service vào Domain Overview theo mặc định; có thể đưa vào Detailed DDD/Design diagram khi giải thích responsibility/dependency thực sự hữu ích.

## 7. Domain Event

Domain Event biểu diễn một sự thật nghiệp vụ đã xảy ra, thường đặt tên ở quá khứ: `GoalCompleted`, `ScheduleProposalApproved`, `StudySessionFinished`.

Một event nên có:

- Tên và ý nghĩa nghiệp vụ.
- Thời điểm xảy ra (nếu domain cần).
- Thông tin cần thiết để consumers hiểu sự kiện.
- Context/source và versioning expectations nếu có integration.

Không nhầm Domain Event với log record, webhook payload, message broker envelope hoặc audit table. Có thể các cấu trúc này được map với nhau trong implementation nhưng chúng không đồng nghĩa.

## 8. Domain Policy

Policy mô tả quyết định hoặc phản ứng nghiệp vụ khi điều kiện/event xảy ra. Ví dụ: khi một milestone hoàn thành, policy có thể đánh giá điều kiện mở milestone kế tiếp.

Policy có thể được triển khai bằng domain service, application workflow, event handler hoặc rules engine. Không mặc định mỗi Policy phải là một class riêng.

## 9. Specification

Specification đóng gói một tiêu chí nghiệp vụ có thể kiểm tra hoặc kết hợp: ví dụ điều kiện một Goal đủ điều kiện kích hoạt, một Task có thể được lập lịch, hoặc một người học đạt prerequisite.

Chỉ tách Specification khi điều kiện có tên, có thể tái sử dụng, phức tạp hoặc cần kiểm thử riêng. Predicate đơn giản không cần biến thành class chỉ để “đúng DDD”.

## 10. Factory

Factory phù hợp khi tạo Entity/Aggregate cần quy trình, phối hợp hoặc đảm bảo invariant phức tạp. Constructor/factory method là đủ khi tạo object đơn giản.

Factory không nên trở thành nơi chứa mọi business logic sau khi khởi tạo.

## 11. Repository

Repository cung cấp abstraction truy xuất Aggregate. Trong DDD, repository thường thao tác ở Aggregate Root boundary.

Không đưa Repository vào Domain Overview. Trong Detailed Domain Model có thể ghi chú vai trò, nhưng interface thường thuộc design/architecture view tùy style dự án.

## 12. Domain ID và Persistence FK

Phân biệt ba thứ:

1. **Domain identity:** khái niệm định danh trong domain, ví dụ `CustomerId`.
2. **Domain reference:** Aggregate/Entity giữ định danh của một đối tượng khác theo mô hình domain.
3. **Persistence FK:** cột vật lý dùng để liên kết record trong database, ví dụ `customer_id`.

Chúng có thể ánh xạ với nhau nhưng không phải cùng một khái niệm. Không loại `CustomerId` khỏi Detailed Domain Model chỉ vì nó trông giống ID; cũng không đưa cột `customer_id` vào Domain Overview chỉ vì schema có nó.
