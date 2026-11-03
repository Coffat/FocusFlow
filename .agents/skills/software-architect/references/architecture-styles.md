# Phong cách kiến trúc và cách chọn

## Mục lục
1. Bảng phong cách
2. Cách chọn
3. Modular monolith đúng cách
4. Microservices: điều kiện và bẫy
5. Event-driven, CQRS, Event Sourcing
6. Hexagonal / Clean / Onion (cấu trúc bên trong)
7. Dữ liệu và nhất quán trong hệ phân tán
8. Đồng bộ hay bất đồng bộ
9. Ngụy biện về hệ phân tán

## 1. Bảng phong cách

| Phong cách | Ý tưởng | Mạnh | Yếu | Hợp khi | Tránh khi |
|---|---|---|---|---|---|
| **Layered (n-tier)** | Tầng: trình bày, nghiệp vụ, dữ liệu; phụ thuộc một chiều | Quen thuộc, đơn giản | Dễ thành "tầng mỏng", thay đổi chạm mọi tầng | CRUD nghiệp vụ nhỏ-vừa | Miền phức tạp cần ranh giới nghiệp vụ rõ |
| **Monolith (một khối)** | Một đơn vị triển khai | Đơn giản phát triển, kiểm thử, triển khai, giao dịch ACID cục bộ | Co giãn theo khối, build/triển khai chậm khi lớn | Khởi đầu, đội nhỏ, miền chưa rõ | Cần triển khai/co giãn độc lập từng phần ở quy mô lớn |
| **Modular monolith** | Một đơn vị triển khai, chia **module nghiệp vụ** có ranh giới ép được | Giữ đơn giản vận hành, tách module sau này dễ | Cần kỷ luật ranh giới; vẫn co giãn theo khối | **Mặc định** cho phần lớn hệ thống doanh nghiệp | Các phần có yêu cầu co giãn/công nghệ rất khác nhau |
| **Microservices** | Nhiều dịch vụ nhỏ, triển khai độc lập, mỗi dịch vụ sở hữu dữ liệu | Triển khai/co giãn/công nghệ độc lập, tự chủ đội | Độ phức tạp phân tán, nhất quán cuối cùng, vận hành, kiểm thử tích hợp | Nhiều đội, miền rõ, nhu cầu độc lập cao, DevOps trưởng thành | Đội nhỏ, miền chưa rõ, chưa có tự động hóa/quan sát |
| **SOA / ESB** | Dịch vụ lớn qua bus trung tâm | Tích hợp doanh nghiệp, tái dùng | Bus thành nút thắt và điểm lỗi, quản trị nặng | Tích hợp hệ thống doanh nghiệp hiện hữu | Hệ thống mới tự chủ |
| **Event-driven** | Thành phần giao tiếp bằng sự kiện qua broker | Ghép nối lỏng, co giãn, mở rộng dễ | Khó theo dõi luồng, nhất quán cuối cùng, thứ tự/trùng lặp | Luồng bất đồng bộ, tích hợp nhiều bên | Cần phản hồi đồng bộ nhất quán ngay |
| **CQRS** | Tách mô hình ghi và đọc | Tối ưu riêng đọc/ghi, co giãn đọc | Hai mô hình, đồng bộ, phức tạp | Tải đọc ≫ ghi, mô hình đọc rất khác mô hình ghi | CRUD đơn giản |
| **Event Sourcing** | Lưu chuỗi sự kiện thay vì trạng thái | Lịch sử đầy đủ, kiểm toán, dựng lại trạng thái | Truy vấn khó, đổi schema sự kiện, đường cong học | Kiểm toán mạnh, miền sự kiện tự nhiên (tài chính, sổ cái) | Phần lớn ứng dụng thông thường |
| **Serverless / FaaS** | Hàm chạy theo sự kiện, nhà cung cấp quản lý hạ tầng | Không quản máy chủ, trả theo dùng, co giãn tự động | Giới hạn thời gian/trạng thái, khởi động lạnh, lock-in, gỡ lỗi | Tải bất thường/thưa, tác vụ nền, tích hợp | Tải ổn định cao, độ trễ cực thấp, tác vụ dài |
| **Microkernel / plug-in** | Lõi nhỏ + mô-đun cắm | Mở rộng bằng plug-in | Ranh giới plug-in phức tạp | Sản phẩm nền tảng, IDE, quy tắc theo khách hàng | Hệ thống ít biến thể |
| **Pipeline (pipes & filters)** | Chuỗi bước xử lý dữ liệu | Tái dùng, song song | Không hợp xử lý tương tác | ETL, xử lý dữ liệu, media | Giao dịch tương tác |
| **Space-based** | Lưới dữ liệu trong bộ nhớ, bỏ nút thắt CSDL | Co giãn cực lớn | Phức tạp, đắt | Đỉnh tải cực lớn khó dự đoán | Hầu hết hệ thống |

## 2. Cách chọn

Dựa trên ASR và ngữ cảnh, không dựa trên xu hướng:

| Yếu tố | Nghiêng về |
|---|---|
| Đội nhỏ (≤ ~10 dev), một đội | Monolith / **modular monolith** |
| Miền nghiệp vụ chưa rõ, thay đổi nhiều | Monolith/modular monolith (ranh giới dịch vụ sai tốn kém hơn ranh giới module sai) |
| Nhiều đội cần phát hành độc lập | Microservices (hoặc modular monolith nếu phát hành chung được) |
| Phần nào đó co giãn khác hẳn phần còn lại | Tách riêng phần đó (không cần tách tất cả) |
| Cần nhất quán mạnh trên một tập dữ liệu | Giữ chung CSDL giao dịch/ranh giới ACID |
| Tích hợp bất đồng bộ nhiều bên | Event-driven, hàng đợi |
| Tải đọc rất nặng | Cache, bản sao đọc, CQRS có chọn lọc |
| Tải thưa, bất thường | Serverless cho phần đó |
| Mức trưởng thành DevOps thấp | Tránh kiến trúc nhiều thành phần triển khai |

Quy tắc: **tách khi có lý do đo được**, không tách vì "sau này có thể cần". Đường tiến hóa khuyến nghị: monolith → modular monolith → tách dịch vụ từ các module đã có ranh giới rõ.

## 3. Modular monolith đúng cách

- Module theo **khả năng nghiệp vụ** (Catalog, Booking, Payment), không theo tầng.
- Mỗi module có **API công khai** (interface/facade) và nội bộ ẩn; module khác chỉ gọi qua API công khai hoặc sự kiện nội bộ.
- Mỗi module **sở hữu bảng riêng** (schema/prefix riêng); không join chéo bảng của module khác; không FK chéo module (hoặc chỉ qua id). Đọc dữ liệu module khác qua API hoặc bản sao đọc.
- Hướng phụ thuộc một chiều, không vòng; **ép bằng công cụ** (kiểm thử kiến trúc như ArchUnit/NetArchTest/dependency-cruiser, ranh giới package/assembly), không chỉ bằng thỏa thuận.
- Giao tiếp giữa module bằng sự kiện nội bộ cho luồng không cần đồng bộ; giao dịch xuyên module cần được cân nhắc (sao cho khi tách sau này không phải đổi mô hình).
- Có thể tách thành dịch vụ sau này mà không viết lại logic: ranh giới đã sạch.

## 4. Microservices: điều kiện và bẫy

Điều kiện tiên quyết (theo kinh nghiệm cộng đồng, Fowler): cấp phát hạ tầng nhanh, giám sát cơ bản tốt, triển khai ứng dụng nhanh/tự động, văn hóa DevOps; cộng thêm quan sát phân tán, quản lý cấu hình/bí mật, và thiết kế API ổn định.

Dấu hiệu **distributed monolith** (tệ nhất cả hai): triển khai phải đồng bộ nhiều dịch vụ; dịch vụ dùng chung một CSDL; gọi đồng bộ chuỗi dài; thay đổi một chức năng chạm nhiều dịch vụ; chia theo tầng kỹ thuật.

Nguyên tắc: một dịch vụ = một bounded context, sở hữu dữ liệu riêng, giao tiếp qua API/sự kiện, triển khai độc lập, đội sở hữu rõ. Kích thước theo ranh giới nghiệp vụ và đội, không theo số dòng code. Dịch vụ quá nhỏ ("nano") sinh ra gọi chéo liên tục.

## 5. Event-driven, CQRS, Event Sourcing

Ba kiểu dùng sự kiện, đừng lẫn:
1. **Event notification**: sự kiện báo "đã xảy ra X" (chỉ chứa id); bên nhận gọi lại nếu cần dữ liệu.
2. **Event-carried state transfer**: sự kiện mang đủ dữ liệu để bên nhận giữ bản sao cục bộ (giảm gọi chéo, tăng độ lệch dữ liệu).
3. **Event sourcing**: sự kiện **là** nguồn sự thật; trạng thái suy ra từ chuỗi sự kiện.

Lưu ý bắt buộc: giao hàng ít nhất một lần (at-least-once) → bên nhận **idempotent**; thứ tự chỉ đảm bảo trong phạm vi khóa phân vùng; schema sự kiện có phiên bản và tương thích; dead-letter queue và giám sát độ trễ; dùng **outbox** để phát sự kiện nhất quán với giao dịch.

CQRS không bắt buộc đi cùng event sourcing và không phải mặc định: chỉ dùng cho phần đọc/ghi lệch nhau rõ.

## 6. Hexagonal / Clean / Onion

Cấu trúc **bên trong** một module/dịch vụ (không phải kiểu triển khai): lõi miền và use case ở giữa, **không phụ thuộc** vào framework, CSDL, giao diện; giao tiếp với bên ngoài qua **port** (interface do lõi định nghĩa) và **adapter** (cài đặt cho web, CSDL, message). Quy tắc phụ thuộc: luôn hướng vào trong. Lợi ích: kiểm thử lõi không cần hạ tầng, thay công nghệ ít đau. Chi phí: nhiều lớp trừu tượng, không đáng cho CRUD thuần.

## 7. Dữ liệu và nhất quán trong hệ phân tán

- **Một dịch vụ sở hữu một dữ liệu**; chia sẻ qua API/sự kiện, không qua CSDL chung.
- **CAP**: khi mạng bị phân vùng, phải chọn nhất quán hoặc sẵn sàng cho thao tác bị ảnh hưởng. **PACELC**: ngay cả khi không có phân vùng vẫn đánh đổi độ trễ và nhất quán. Chọn theo từng loại dữ liệu, không cho cả hệ thống.
- **ACID cục bộ** trong một CSDL; xuyên dịch vụ dùng **saga** (chuỗi giao dịch cục bộ + hành động bù) hoặc thiết kế lại ranh giới để thao tác nghiệp vụ quan trọng nằm gọn trong một dịch vụ. Hạn chế two-phase commit xuyên dịch vụ (khóa lâu, phụ thuộc, hỗ trợ kém).
- **Nhất quán cuối cùng** cần được nghiệp vụ chấp nhận và thiết kế trải nghiệm tương ứng (trạng thái "đang xử lý").
- Truy vấn xuyên dịch vụ: API composition, bản sao đọc (CQRS read model), kho dữ liệu báo cáo; tránh join phân tán.
- **Polyglot persistence** chỉ khi đáng (tìm kiếm → search engine, cache → key-value); mỗi kho thêm chi phí vận hành.

## 8. Đồng bộ hay bất đồng bộ

| Dùng đồng bộ (REST/gRPC) khi | Dùng bất đồng bộ (hàng đợi/sự kiện) khi |
|---|---|
| Người dùng chờ kết quả ngay | Kết quả không cần ngay |
| Thao tác truy vấn đơn giản | Tác vụ nặng/dài, cần san tải |
| Cần nhất quán ngay | Nhiều bên cùng quan tâm một sự kiện |
| Đơn giản, dễ theo dõi | Cần chịu lỗi/độ trễ của bên nhận, tách vòng đời |

Chuỗi gọi đồng bộ dài làm khả dụng nhân lên (xem công thức nối tiếp) và độ trễ cộng dồn; đặt **timeout** và chiến lược lỗi cho mọi lời gọi.

## 9. Tám ngụy biện về điện toán phân tán (Deutsch/Gosling)

Mạng đáng tin cậy; độ trễ bằng không; băng thông vô hạn; mạng an toàn; cấu trúc mạng không đổi; chỉ có một quản trị viên; chi phí vận chuyển bằng không; mạng đồng nhất. Mọi thiết kế phân tán phải trả lời cho từng điều khi lời gọi từ xa sai.
