# Checklist rà soát class diagram (tự chạy trước khi giao)

## Ký hiệu
- [ ] Mỗi lớp có tên (số ít, danh từ, UpperCamelCase); thuộc tính lowerCamelCase; thao tác là động từ.
- [ ] Cú pháp thuộc tính `name : Type [= default]`; thao tác `name(param : Type) : Return`.
- [ ] Abstract class/operation in nghiêng hoặc `{abstract}`; interface có `«interface»`; enum có `«enumeration»`.
- [ ] Generalization: nét liền + tam giác rỗng, **con → cha**.
- [ ] Realization: nét **đứt** + tam giác rỗng, lớp → interface.
- [ ] Uni-directional: mũi tên mở trỏ về lớp **được biết**; role + multiplicity ở đầu đó.
- [ ] Aggregation = thoi **rỗng**, composition = thoi **đặc**, thoi ở **phía toàn thể**.
- [ ] Association class nối bằng nét đứt vào **giữa** đường association.
- [ ] Dependency: nét đứt + mũi tên mở, từ client → supplier.
- [ ] Visibility đã xác định cho mọi thành viên (hiển thị hay không tùy mức chi tiết).

## Nội dung
- [ ] Đã nêu rõ góc nhìn (domain / design / implementation) và diagram nhất quán với nó.
- [ ] Mọi association (trừ generalization/realization/dependency) có **multiplicity hai đầu**; role name ở đầu có ý nghĩa.
- [ ] Cận dưới multiplicity phản ánh đúng bắt buộc/tùy chọn.
- [ ] Composition: đầu toàn thể là `1` hoặc `0..1`, bộ phận không dùng chung.
- [ ] Không có khóa ngoại làm thuộc tính khi đã có association; không có thông tin trùng lặp.
- [ ] Mọi lớp có ít nhất một quan hệ hoặc lý do ghi rõ.
- [ ] Kế thừa qua được kiểm tra "is-a" và thay thế được; không quá 3 mức.
- [ ] Association class chỉ dùng khi mỗi cặp có đúng một liên kết; ngược lại dùng lớp trung gian.
- [ ] Quan hệ nhiều–nhiều đã được xét xem có cần association class/lớp trung gian.
- [ ] Không lớp God, không lớp rỗng vô nghĩa.
- [ ] Quy tắc nghiệp vụ liên quan được thể hiện (ràng buộc, multiplicity, enum) và ghi mã BR trong mô tả.

## Bố cục và phạm vi
- [ ] Mỗi diagram ≤ 15–20 lớp, một chủ đề, đã chia package nếu lớn.
- [ ] Không vẽ trình tự/luồng xử lý trên class diagram.
- [ ] Tên khớp giữa diagram, danh sách lớp, bảng mô tả và truy vết use case.
- [ ] Mã PlantUML/Mermaid biên dịch được (cú pháp đúng, dấu ngoặc, nhãn).

## Bàn giao
- [ ] Tóm tắt: góc nhìn, số lớp, giả định chính, câu hỏi mở cần người dùng xác nhận.
