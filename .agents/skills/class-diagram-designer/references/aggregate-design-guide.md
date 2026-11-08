# Aggregate Design Guide

## 1. Aggregate là consistency boundary

Aggregate không đơn thuần là object graph, cây composition, nhóm bảng quan hệ hoặc package. Đây là boundary trong đó các invariant cần được duy trì nhất quán theo transaction/update model của hệ thống.

## 2. Quy trình xác định Aggregate

### Bước 1 — Bắt đầu từ business transaction/use case

Liệt kê thao tác nghiệp vụ quan trọng: tạo, sửa, approve, complete, cancel, reschedule, assign, reserve... Hỏi object nào cần được cập nhật cùng nhau để rule luôn đúng.

### Bước 2 — Viết invariant

Ví dụ dạng câu:

- Một proposal chỉ được approve khi ở trạng thái X.
- Không thể thêm item nếu vượt giới hạn Y.
- Một task không thể được hoàn thành trước khi điều kiện Z được thỏa mãn.

Không đưa ví dụ vào model thực tế nếu domain source không nói như vậy.

### Bước 3 — Tìm consistency boundary nhỏ nhất đủ bảo vệ invariant

Không gom các object chỉ vì chúng thường được đọc cùng nhau. Cân nhắc transaction size, contention, lifecycle và khả năng chấp nhận eventual consistency.

### Bước 4 — Chọn Root

Root là Entity có identity của Aggregate và chịu trách nhiệm bảo vệ invariant của boundary. Những thay đổi từ bên ngoài đi qua root. Child Entity có thể có identity nội bộ nhưng không được sửa độc lập qua public boundary của Aggregate.

### Bước 5 — Xác định reference ra ngoài

Nguyên tắc DDD phổ biến là reference Aggregate khác bằng identity. Một số framework có thể dùng object reference/navigation property, nhưng điều đó là implementation choice; cần bảo vệ consistency boundary.

### Bước 6 — Kiểm chứng với lifecycle và use cases

Nếu cùng Aggregate quá nhiều object độc lập, nếu root phải phối hợp nhiều context, hoặc nếu một thao tác buộc cập nhật nhiều Aggregate trong một transaction, xem lại boundary.

## 3. Aggregate map template

| Aggregate | Root | Members | Invariants | Commands/use cases | External IDs | Evidence/status |
|---|---|---|---|---|---|---|

## 4. Các cảnh báo

- Không gán Aggregate Root cho mọi Entity.
- Aggregate có thể chỉ gồm một Entity root.
- Child Entity không bắt buộc phải có composition trong UML; có thể dùng association + aggregate notation/notes nếu hợp ngữ nghĩa hơn.
- Composition không tự tạo Aggregate boundary.
- Aggregate boundary không tự động tạo UML composition.
- Một Entity không thể đồng thời là root độc lập và child member của Aggregate khác theo cùng một mô hình ownership. Nếu thấy vậy, kiểm tra lại định nghĩa.
- Một object có thể có nhiều associations mà không thuộc cùng một Aggregate.
- Root không nên trở thành God Object chỉ vì được xem là “entry point”.
- Không dùng cascade delete từ database làm bằng chứng duy nhất cho aggregate membership.

## 5. Cross-Aggregate consistency

Nếu invariant trải qua nhiều Aggregate:

1. Xem xét liệu invariant có thực sự cần atomic consistency không.
2. Nếu có, kiểm tra liệu Aggregate boundary có đang đặt sai không.
3. Nếu nghiệp vụ cho phép eventual consistency, cân nhắc Domain Event/Policy/Process Manager/Saga hoặc Application Service orchestration phù hợp.
4. Nêu rõ latency, failure và compensation khi cần.
5. Không giấu cross-aggregate invariant bằng một mũi tên Association.

## 6. Khi nào nên gắn stereotype

Có thể dùng `«AggregateRoot»` hoặc note/legend để đánh dấu root. Đây là quy ước DDD của dự án, không phải stereotype mặc định UML. Chỉ đánh dấu sau khi đã xác định consistency boundary; nếu mới là giả thuyết, ghi `«ProposedAggregateRoot»` hoặc dùng bảng Aggregate Map.
