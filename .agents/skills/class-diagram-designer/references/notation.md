# Ký hiệu UML 2 Class Diagram (đối chiếu bài IBM + UML 2.5)

## Mục lục
1. Classifier
2. Thuộc tính và thao tác
3. Visibility và các điều chỉnh
4. Quan hệ
5. Multiplicity
6. Package
7. Instance và role
8. Internal structure
9. Chỗ bài IBM viết lỏng hoặc lỗi in (đã hiệu chỉnh)

## 1. Classifier

| Loại | Ký hiệu | Ghi chú |
|---|---|---|
| Class | Hình chữ nhật 3 ngăn | `«class»` là tùy chọn, mặc định ngầm hiểu |
| Abstract class | Tên **in nghiêng** hoặc `{abstract}` | Không tạo instance trực tiếp; lớp cha không bắt buộc phải abstract |
| Abstract operation | Chữ ký **in nghiêng** hoặc `{abstract}` | Lớp con cài đặt phiên bản riêng |
| Interface | `«interface»` ở ngăn tên | Cần ít nhất một lớp cài đặt; không có instance riêng |
| Data type | `«dataType»` | Giá trị không có định danh riêng (Money, DateRange) |
| Enumeration | `«enumeration»`, ngăn dưới liệt kê literal | Tập giá trị cố định |

Ba ngăn: **tên** bắt buộc; thuộc tính và thao tác tùy chọn (bỏ khi diagram chỉ minh họa quan hệ).

## 2. Thuộc tính và thao tác

Thuộc tính, mỗi dòng một thuộc tính:
```
visibility name : Type [multiplicity] = default {property}
-balance : Dollars = 0
+flightNumber : Integer
-phones : String [0..3]
/age : Integer          ← thuộc tính suy diễn (derived)
```
Thao tác:
```
visibility name(direction paramName : Type = default, ...) : ReturnType
+delayFlight(numberOfMinutes : Minutes)
+getArrivalTime() : Date
```
- Không có `: ReturnType` nghĩa là không trả giá trị (quyết định thiết kế; thay đổi chữ ký là thay đổi thiết kế).
- `in` / `out` / `inout` cho tham số là tùy chọn; `in` là mặc định nên thường bỏ qua (Java, C++ chỉ có in).
- Thành viên **static** gạch chân.
- Kiểu thuộc tính: ở góc nhìn domain dùng kiểu nghiệp vụ (Dollars, Minutes); ở góc nhìn code-gen chỉ dùng kiểu của ngôn ngữ hoặc kiểu đã có trong mô hình.

## 3. Visibility và các điều chỉnh

| Dấu | Ý nghĩa |
|---|---|
| `+` | public |
| `#` | protected |
| `-` | private |
| `~` | package |

Ràng buộc thường dùng đặt trong `{}`: `{readOnly}`, `{ordered}`, `{unique}`, `{nonunique}`. Quy tắc nghiệp vụ phức tạp: đặt trong note hoặc dạng ràng buộc `{balance >= 0}`.

## 4. Quan hệ

| Quan hệ | Đường | Đầu mút | Chiều/vị trí |
|---|---|---|---|
| **Generalization** (kế thừa) | liền | tam giác **rỗng** | Từ lớp con → lớp cha |
| **Realization** (hiện thực interface) | **đứt** | tam giác **rỗng** | Từ lớp cài đặt → interface |
| **Association** (bi-directional, chuẩn) | liền | không mũi tên | Cả hai phía biết nhau; role + multiplicity ở **cả hai** đầu |
| **Uni-directional association** | liền | mũi tên **mở** | Trỏ tới lớp **được biết**; role + multiplicity chỉ ở đầu lớp được biết |
| **Aggregation** | liền | hình thoi **rỗng** | Ở phía **toàn thể** |
| **Composition** | liền | hình thoi **đặc** | Ở phía **toàn thể** |
| **Association class** | liền (association) + **đứt** nối vào giữa đường | lớp bình thường | Lớp chứa thông tin của mối quan hệ |
| **Reflexive association** | liền, vòng về chính lớp | role đặt tên hai vai | Một instance liên kết với instance **khác** cùng lớp |
| **Dependency** | **đứt** | mũi tên **mở** | Từ lớp phụ thuộc (client) → lớp được dùng (supplier); thêm `«use»`, `«create»`… nếu cần |

Phân biệt đầu mút dễ nhầm:
- Tam giác rỗng + nét **liền** = kế thừa. Tam giác rỗng + nét **đứt** = hiện thực interface.
- Mũi tên mở + nét **liền** = navigability. Mũi tên mở + nét **đứt** = dependency.
- Thoi rỗng = aggregation; thoi đặc = composition. Thoi luôn nằm ở phía toàn thể.

Ý nghĩa chính xác:
- **Association**: mặc định theo quy ước IBM là hai chiều (cả hai lớp "biết" nhau). Nếu cần chỉ một phía biết, dùng uni-directional. Ví dụ báo cáo biết `BankAccount` nhưng `BankAccount` không biết báo cáo, giúp giảm coupling.
- **Aggregation**: bộ phận có thể tồn tại độc lập và có thể sống lâu hơn toàn thể (Car–Wheel).
- **Composition**: bộ phận chỉ thuộc **một** toàn thể (multiplicity ở phía toàn thể là `1` hoặc `0..1`); hủy toàn thể thì hủy bộ phận (Company–Department).
- **Association class**: với mỗi liên kết giữa hai instance sẽ có một instance của association class. Ví dụ mỗi cặp (Flight, FrequentFlyer) có một `MileageCredit`.
- **Reflexive**: Employee có thể quản lý Employee khác; không có nghĩa instance liên kết với chính nó. Đặt role khác nhau cho hai đầu.

Tree notation: khi có ≥ 2 lớp con, các đường kế thừa có thể nhập thành một nhánh cây trước khi tới tam giác. Hai cách vẽ tương đương.

## 5. Multiplicity

| Ký hiệu | Nghĩa |
|---|---|
| `1` | đúng một |
| `0..1` | không hoặc một |
| `*` hoặc `0..*` | không hoặc nhiều |
| `1..*` | một hoặc nhiều |
| `3` | đúng ba |
| `0..5` | từ không đến năm |
| `5..15` | từ năm đến mười lăm |

Nếu bỏ qua multiplicity thì giá trị **không xác định**, không mặc định là `1`: luôn ghi rõ.

## 6. Package

Hình chữ nhật lớn có tab nhỏ ở góc trên trái, tên package ở tab. Hai cách thể hiện thành viên:
1. Đặt các lớp **bên trong** hình chữ nhật lớn (chỉ những lớp diagram này muốn hiển thị).
2. Đặt lớp **bên ngoài**, nối từng lớp bằng đường tới vòng tròn có dấu `+` gắn vào package.

Package là namespace. Diagram không cần vẽ hết thành viên của package. Phụ thuộc giữa package vẽ bằng dependency (`«import»`, `«access»`, `«use»`).

## 7. Instance và role

- **Instance specification**: giống class nhưng ngăn tên là `instanceName : ClassName` **gạch chân**. Chỉ hiển thị thuộc tính có giá trị đáng chú ý. Liên kết giữa các instance phải khớp quan hệ và role đã có trên class diagram (đây thực chất là **object diagram**).
- **Role**: hộp chứa `roleName : ClassName` **không gạch chân**. Không vẽ được trên class diagram thuần; cần ký hiệu **internal structure** (composite structure).

## 8. Internal structure

Hộp hai ngăn: trên là tên classifier; dưới là các **part** theo vai trò và cách chúng nối với nhau. Dùng khi class diagram cho biết "Plane gồm 4 Engine và 2 ControlSoftware" nhưng không cho biết ControlSoftware nào điều khiển Engine nào. PlantUML không hỗ trợ composite structure diagram gốc: nếu cần, dùng component diagram hoặc vẽ tay (draw.io), và nói rõ khi mô phỏng.

## 9. Chỗ bài IBM viết lỏng hoặc lỗi in (đã hiệu chỉnh trong skill này)

| Trong bài IBM | Cách skill xử lý |
|---|---|
| Bảng multiplicity ghi `0..` và dòng trống cho "zero or more" (mất dấu `*`) | Dùng `0..*` hoặc `*` |
| "There are five types of associations" gồm bi-directional, uni-directional, association class, aggregation (và composition), reflexive | Giữ cách phân loại này khi giải thích; nhưng khi vẽ phải chọn đúng ký hiệu cho từng loại |
| Ví dụ reflexive dùng role "manager/manages" | Role nên là danh từ vai trò (`manager`, `directReports`) để dễ đọc; nghĩa không đổi |
| Cách tách "chi tiết modeling" | Bài nói rõ chỉ dạy ký hiệu; việc chọn lớp, chọn loại quan hệ, đặt multiplicity theo `modeling-guide.md` |
| Dependency không được đề cập | Bổ sung theo UML 2.5 (§4) vì cần để phân biệt với association |
| Aggregation được trình bày như quan hệ toàn thể–bộ phận thông thường | Giữ định nghĩa IBM; thêm khuyến cáo: UML không gán ngữ nghĩa mạnh cho thoi rỗng, ưu tiên association thường, chỉ dùng aggregation khi người đọc thật sự cần thấy "toàn thể–bộ phận" |
