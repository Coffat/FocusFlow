# Hướng dẫn mô hình hóa lớp

## Mục lục
1. Chọn góc nhìn
2. Tìm và lọc lớp
3. Thuộc tính và thao tác
4. Cây quyết định chọn quan hệ
5. Multiplicity
6. Mẫu thiết kế thường gặp
7. Kế thừa: dùng và tránh
8. Truy vết từ use case / quy tắc nghiệp vụ
9. Lỗi hay gặp

## 1. Chọn góc nhìn
Domain (khái niệm nghiệp vụ, đọc được bởi business) / Design (interface, thao tác, navigability) / Implementation (khớp code). Quyết định trước khi vẽ; không đưa `getXxx/setXxx`, `id` khóa ngoại, kiểu `List<>` vào mô hình domain.

## 2. Tìm và lọc lớp

Nguồn: danh từ trong yêu cầu, glossary, luồng use case, biểu mẫu/báo cáo hiện có, bảng CSDL.

Lọc từng ứng viên bằng các câu hỏi:
1. Nó có **định danh hoặc vòng đời riêng** (tạo, thay đổi, xóa) mà nghiệp vụ quan tâm không? Có → lớp.
2. Nó chỉ là **một giá trị** của lớp khác (tên, địa chỉ email, ngày)? → thuộc tính (hoặc data type nếu có cấu trúc: Money, Address).
3. Nó là **actor ngoài hệ thống**? Chỉ thành lớp nếu hệ thống phải lưu thông tin về nó (Customer thì có, người dùng đăng nhập thì thường là User/Account).
4. Nó là **đồng nghĩa** của lớp khác? → gộp, ghi vào glossary.
5. Nó quá mơ hồ ("hệ thống", "thông tin", "dữ liệu", "quản lý")? → loại hoặc làm rõ.
6. Nó là **cấu trúc kỹ thuật** (Controller, DAO, Utility) khi đang ở góc nhìn domain? → loại khỏi domain.
7. Nó là **sự kiện hoặc giao dịch cần lưu lại** (Order, Payment, Booking)? → lớp, thường có thuộc tính thời gian và trạng thái.

Một lớp tốt: có tên là danh từ số ít, một trách nhiệm rõ, có thuộc tính hoặc thao tác riêng, và tham gia ít nhất một quan hệ.

## 3. Thuộc tính và thao tác

Thuộc tính:
- Mỗi thuộc tính có kiểu; nghiệp vụ có đơn vị thì dùng kiểu có đơn vị (Dollars, Minutes) hoặc ghi trong mô tả.
- Mặc định đáng kể thì ghi: `balance : Dollars = 0`.
- Không đưa **khóa ngoại**; association thể hiện điều đó. Có thể giữ `id` (định danh riêng) khi cần bàn về code.
- Không lặp: nếu có association tới `Plane` thì không thêm thuộc tính `plane : Plane`.
- Thuộc tính tính toán được dùng `/` (derived), ví dụ `/age`.
- Thuộc tính nhiều giá trị dùng multiplicity: `phones : String [1..3]`.

Thao tác:
- Đến từ **trách nhiệm** của lớp: "Flight tính giờ đến", "BankAccount rút tiền".
- Tên là động từ; chữ ký đủ tham số và kiểu trả về khi ở góc nhìn design.
- Đặt thao tác ở lớp **sở hữu dữ liệu** cần thiết để thực hiện (information expert).
- Dấu hiệu God class: > ~15 thao tác, trộn nhiều chủ đề, dùng dữ liệu của lớp khác phần lớn thời gian → tách.
- Dấu hiệu anemic: lớp chỉ có thuộc tính, mọi logic ở lớp "Service" → xem lại nếu đang mô hình domain đáng kể hành vi.

## 4. Cây quyết định chọn quan hệ

Hỏi lần lượt, dừng ở câu trả lời "có" đầu tiên:

1. **A là một loại B** ("A is-a B"), A có thể thay thế B ở mọi nơi, A thừa hưởng toàn bộ đặc tính của B? → **Generalization** (A → B).
2. **A cài đặt hợp đồng (interface) B**, không thừa hưởng cài đặt? → **Realization** (A ⇢ B, nét đứt).
3. **A chỉ tạm dùng B** (tham số thao tác, biến cục bộ, tạo rồi bỏ), không giữ tham chiếu lâu dài? → **Dependency**.
4. **Thông tin cần lưu thuộc về mối quan hệ giữa A và B**, không thuộc riêng bên nào (số dặm của chuyến bay của hội viên, điểm của sinh viên trong môn học)? → **Association class** (hoặc lớp trung gian, xem §6).
5. **B là bộ phận của A và chỉ thuộc đúng một A, bị hủy khi A bị hủy** (Company–Department, Order–OrderLine)? → **Composition** (thoi đặc ở A).
6. **B là bộ phận của A nhưng sống độc lập, có thể chuyển giữa các A, hoặc tồn tại trước A** (Car–Wheel) và việc nhấn mạnh toàn thể–bộ phận có ích cho người đọc? → **Aggregation** (thoi rỗng ở A).
7. Các đối tượng **biết nhau lâu dài** → **Association**; nếu chỉ một phía cần biết → **uni-directional**; mặc định ở domain model là association thường.

Nguyên tắc: khi phân vân giữa aggregation và association thường, chọn **association thường**; khi phân vân giữa composition và association, hỏi "nếu hủy A thì B còn ý nghĩa không?" Nếu không → composition.

## 5. Multiplicity

Hỏi hai chiều, ghi cả cận dưới và cận trên:
- `Flight → Plane`: một Flight có tối thiểu 0 (chưa gán) tối đa 1 Plane → `0..1` ở đầu Plane.
- `Plane → Flight`: một Plane có 0 (máy bay mới) đến nhiều Flight → `*` ở đầu Flight.

Cận dưới quan trọng: `0` nghĩa là tùy chọn, `1` nghĩa là bắt buộc phải có khi đối tượng tồn tại → ảnh hưởng đến validation và NOT NULL. Composition: đầu toàn thể là `1` (hoặc `0..1`).

Nhiều–nhiều (`* -- *`): kiểm tra xem mối quan hệ có thuộc tính riêng không (thời điểm, vai trò, số lượng). Có → association class (mỗi cặp chỉ có đúng một liên kết) hoặc lớp trung gian (cặp có thể có nhiều liên kết, ví dụ nhiều lần đặt cùng một sản phẩm).

## 6. Mẫu thiết kế thường gặp

- **Association class vs lớp trung gian**: association class mặc định ràng buộc "một instance cho mỗi cặp". Nếu cùng một cặp có thể có nhiều bản ghi (nhiều giao dịch, nhiều lần ghi nhận), tách thành lớp thường với hai association `1` – `*`.
- **Trạng thái**: dùng `«enumeration»` (`OrderStatus`) cho trạng thái đơn giản; vòng đời phức tạp có quy tắc chuyển trạng thái thì thêm state machine diagram, đừng nhét vào class diagram.
- **Giá trị có cấu trúc**: `Money{amount, currency}`, `Address`, `DateRange` là data type, không phải entity.
- **Phân cấp tự tham chiếu** (cấp tổ chức, danh mục): reflexive association với hai role (`parent 0..1`, `children *`).
- **Vai trò thay đổi theo thời gian** (một Person vừa là Customer vừa là Employee): dùng quan hệ Person–Role (association/composition), không tạo lớp con Customer, Employee kế thừa Person nếu một người có thể chuyển vai.
- **Đa hình**: tách interface (`PaymentMethod`) và các lớp cài đặt (`CreditCard`, `BankTransfer`) bằng realization.
- **Lớp báo cáo / view**: biết lớp nghiệp vụ nhưng lớp nghiệp vụ không biết lớp báo cáo (uni-directional) để giảm coupling.
- **Lịch sử/hiệu lực theo thời gian**: thêm lớp có `effectiveFrom/effectiveTo` thay vì ghi đè giá trị cũ.

## 7. Kế thừa: dùng và tránh

Dùng khi: các lớp con thật sự là các **loại** (CheckingAccount, SavingsAccount là BankAccount), có hành vi hoặc thuộc tính riêng, dùng đa hình được. Lớp cha abstract khi không có ý nghĩa tạo instance trực tiếp và có thao tác abstract (`withdrawal`) để lớp con hiện thực.

Tránh khi:
- Chỉ để **tái sử dụng code** (dùng composition/delegation thay thế).
- Lớp con **không dùng được** thuộc tính hoặc hành vi của cha (vi phạm Liskov).
- Phân cấp sâu quá 3 mức.
- Phân loại theo thuộc tính chỉ khác giá trị (thay vì tạo `GoldCustomer`, `SilverCustomer`, dùng thuộc tính/enum `tier`), trừ khi hành vi khác nhau thật.
- Lớp con chỉ khác nhau vai trò tạm thời (xem §6).

## 8. Truy vết từ use case và quy tắc nghiệp vụ

Nếu có use case spec (ví dụ từ skill `usecase-analyst`):
- Danh từ trong **luồng chính** và **dữ liệu vào/ra** → lớp ứng viên và thuộc tính.
- Động từ tại mỗi bước hệ thống → thao tác của một lớp (hoặc điều phối giữa các lớp).
- **Tiền/hậu điều kiện** → trạng thái (enum) và ràng buộc.
- **Quy tắc nghiệp vụ** (BR-xx) → ràng buộc `{}` trên thuộc tính/association, multiplicity, hoặc thao tác validate. Ghi mã BR vào mô tả lớp.
- Ghi bảng truy vết: Lớp ↔ Use case (UC-xx) trong mô tả lớp.

## 9. Lỗi hay gặp (kiểm tra trước khi giao)

1. Vẽ **thoi ở sai phía** hoặc nhầm thoi rỗng/đặc.
2. Nhầm **realization (nét đứt)** với **generalization (nét liền)**.
3. **Thiếu multiplicity** hoặc để nguyên giá trị mặc định tưởng tượng.
4. Dùng kế thừa chỉ để tái sử dụng code, hoặc dùng cho vai trò thay đổi.
5. Thêm khóa ngoại thành thuộc tính **và** vẽ association (thông tin trùng).
6. **Lớp không có quan hệ** nào (mồ côi) mà không có lý do.
7. Aggregation tràn lan; quan hệ nào cũng thoi rỗng.
8. Composition nhưng bộ phận dùng chung cho nhiều toàn thể (mâu thuẫn "chỉ thuộc một").
9. Lớp God / lớp rỗng; tên lớp là động từ hoặc số nhiều.
10. Trộn góc nhìn: domain model lẫn Controller, Repository, DTO.
11. Association class nhưng cùng một cặp có thể có nhiều bản ghi.
12. Một diagram > 20 lớp mà không chia gói/chủ đề.
13. Mô tả trình tự hoặc luồng xử lý trên class diagram (thuộc sequence/activity diagram).
