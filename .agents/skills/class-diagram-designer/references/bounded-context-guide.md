# Bounded Context Guide

## 1. Phân biệt các khái niệm

| Khái niệm | Ý nghĩa | Câu hỏi chính |
|---|---|---|
| Domain | Lĩnh vực vấn đề mà hệ thống đang giải quyết | Hệ thống phục vụ lĩnh vực nào? |
| Subdomain | Phần problem space được phân rã theo nghiệp vụ | Những năng lực nghiệp vụ nào cần giải quyết? |
| Bounded Context (BC) | Ranh giới nơi một domain model và ngôn ngữ nghiệp vụ nhất quán có hiệu lực | Mô hình nào có ý nghĩa thống nhất trong ranh giới nào? |
| Module/Package | Cách tổ chức code hoặc model | Thành phần được nhóm trong source/design ra sao? |
| Microservice/Deployment unit | Đơn vị triển khai/vận hành | Thành phần nào deploy và scale độc lập? |

Các khái niệm có thể được ánh xạ với nhau nhưng không đồng nghĩa. Một Bounded Context không nhất thiết là một microservice; một package không tự động là Bounded Context; một Subdomain có thể được mô hình hóa bởi một hoặc nhiều Context tùy bài toán.

## 2. Dấu hiệu nhận diện Bounded Context

Một candidate BC có thể có:

- Ubiquitous Language riêng và định nghĩa thuật ngữ nhất quán.
- Business rules/invariants và lifecycle có ranh giới tương đối rõ.
- Mô hình dữ liệu và behavior riêng phù hợp với trách nhiệm nghiệp vụ.
- Nhu cầu thay đổi/evolution tương đối độc lập.
- Ranh giới ownership và tích hợp xác định được.

Không có một tiêu chí đơn lẻ quyết định BC. Số lượng class, package, bảng, team hoặc API không đủ để xác nhận.

## 3. Quy trình đề xuất Context

1. Xác định domain boundary.
2. Phân rã Subdomain theo năng lực và vấn đề nghiệp vụ.
3. Thu thập thuật ngữ và phát hiện cùng một từ có nghĩa khác nhau.
4. Xác định nhóm quy tắc/lifecycle và ownership.
5. Xác định nơi một model cần có semantics riêng.
6. Phân tích tích hợp với model khác.
7. Đề xuất BC boundary; đánh dấu CONFIRMED/INFERRED/PROPOSED/OPEN.
8. Xem lại ranh giới bằng Use Case thực tế và thay đổi dự kiến.

Nếu chưa có bằng chứng đủ mạnh, dùng `Candidate Bounded Context` thay vì ép chốt.

## 4. Context Map

Context Map mô tả quan hệ và điểm tích hợp giữa các Bounded Context. Nó không chỉ là package dependency graph và không nhất thiết là DAG.

Các quan hệ/pattern có thể gặp:

| Pattern | Ý nghĩa khái quát | Khi cân nhắc |
|---|---|---|
| Upstream / Downstream | Một Context cung cấp mô hình/contract, Context khác tiêu thụ | Có chiều ảnh hưởng hoặc phụ thuộc rõ |
| Customer-Supplier | Downstream có tiếng nói trong việc thương lượng contract với upstream | Hai team cần phối hợp thay đổi |
| Open Host Service (OHS) | Upstream cung cấp một protocol/API ổn định để nhiều consumers dùng | Cần contract công khai/ổn định |
| Published Language | Định dạng/ngôn ngữ trao đổi được công bố | Cần schema/protocol chung |
| Anti-Corruption Layer (ACL) | Downstream chuyển đổi mô hình upstream để bảo vệ domain model của mình | Model bên ngoài không phù hợp hoặc thay đổi độc lập |
| Conformist | Downstream chấp nhận mô hình upstream | Chi phí ACL không đáng hoặc ít quyền thương lượng |
| Shared Kernel | Một phần model được chia sẻ và thay đổi có phối hợp | Phạm vi chia sẻ nhỏ, governance rõ |
| Separate Ways | Hai Context không cần tích hợp | Không có business value đủ để kết nối |

Không dùng hết pattern để làm sơ đồ “đầy đủ”. Chỉ ghi pattern khi có bằng chứng và tác động kiến trúc.

## 5. Context Map register

| Upstream | Downstream | Business capability/contract | Relationship pattern | Translation/ACL | Evidence | Status |
|---|---|---|---|---|---|---|

Ghi rõ:

- Dữ liệu/operation nào được cung cấp.
- Ai sở hữu nguồn dữ liệu và semantics.
- Consumer cần model nào, có cần mapping/translation không.
- Đồng bộ synchronous/asynchronous ở mức cần thiết.
- Failure, consistency và versioning concerns khi đã biết.

## 6. Mapping sang UML/package

- UML Package có thể nhóm class theo BC.
- Stereotype `«BoundedContext»` chỉ là quy ước/project-defined nếu không chỉ rõ profile chuẩn.
- Context Map nên là diagram riêng (context map, package-level overview hoặc notation tự định nghĩa có legend).
- Class association giữa hai BC không thay thế integration contract.
- Không vẽ toàn bộ class nội bộ của upstream vào downstream chỉ vì downstream sử dụng dữ liệu upstream.

## 7. Sai lầm cần tránh

- Mỗi module/package = một BC.
- Mỗi microservice = một Subdomain.
- Chia Context theo CRUD entity hoặc database schema.
- Ép có 3/4/5 Context vì muốn kiến trúc nhìn cân đối.
- Dùng một model “User”, “Status”, “Level” xuyên tất cả Context mà không kiểm tra ngữ nghĩa từng nơi.
- Dùng class diagram để thể hiện toàn bộ integration topology.
