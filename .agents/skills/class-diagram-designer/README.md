# Class Diagram Designer

Skill hỗ trợ thiết kế và review UML 2 Class Diagram, Domain Overview và Detailed DDD Domain Model.

## Nội dung

- `SKILL.md`: workflow chính và quy tắc điều phối.
- `references/`: hướng dẫn chuyên sâu, notation, template và checklist.

## Cài đặt

1. Giải nén thư mục `class-diagram-designer` vào thư mục skills mà Agent/IDE của bạn đang cấu hình.
2. Giữ nguyên cấu trúc `SKILL.md` và thư mục `references/`; không chuyển các reference ra khỏi thư mục skill.
3. Kiểm tra Agent có thể đọc file tham chiếu theo đường dẫn tương đối.
4. Thử kích hoạt bằng yêu cầu: “Review class diagram này theo profile Domain Overview, kiểm tra evidence và không tự suy diễn Aggregate/Bounded Context.”

Skill không phụ thuộc framework hoặc ngôn ngữ lập trình cụ thể. Nếu môi trường Agent có quy định riêng về nơi đặt skill, hãy dùng đúng đường dẫn do môi trường đó cấu hình; gói này không giả định một đường dẫn cài đặt cố định.

## Nguyên tắc phiên bản

- UML baseline: UML 2.5.1 (OMG).
- DDD: áp dụng theo ngữ cảnh; không ép mọi hệ thống dùng đầy đủ tactical patterns.
- Các stereotype như `«Entity»`, `«ValueObject»`, `«AggregateRoot»`, `«BoundedContext»` là quy ước của dự án, không tự nhận là stereotype chuẩn UML.
