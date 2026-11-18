# Blind Review Pack — Đánh giá chất lượng 10 Roadmap (A/B Blind)

> **Hướng dẫn đánh giá mù (Blind Review):** Tài liệu này chứa **10 lộ trình học tập** (`R-01` đến `R-10`) tương ứng với 5 mục tiêu học tập (mỗi mục tiêu có 2 phương án độc lập đã được xáo trộn ngẫu nhiên). Mọi thông tin về arm thử nghiệm, model, thinking budget, số lần retry và điểm Judge tự động đã được ẩn hoàn toàn.

## Quy tắc chấm điểm (Thang 1–5 cho mỗi tiêu chí)

- **1 — Rất kém:** Sai lệch mục tiêu/ràng buộc nghiêm trọng, thiếu kiến thức cốt lõi hoặc không thể học theo.
- **2 — Yếu:** Còn lỗ hổng rõ rệt về tiên quyết, nhiệm vụ mơ hồ hoặc lịch học quá tải/bất hợp lý.
- **3 — Đạt yêu cầu cơ bản:** Bao phủ phần lớn mục tiêu nhưng còn điểm cần chỉnh sửa về độ chi tiết, phân bổ tải hoặc tiêu chí kiểm chứng.
- **4 — Tốt:** Logic sư phạm mạch lạc, task cụ thể, lịch khả thi, tiêu chí hoàn thành rõ ràng.
- **5 — Xuất sắc:** Phù hợp trình độ, tiến trình tối ưu, bài tập thực hành sắc nét, kiểm chứng được và tôn trọng chặt chẽ quỹ thời gian.

### 5 Tiêu chí đánh giá

1. **C1 — Độ phủ mục tiêu & phạm vi (Goal & Scope Coverage):** Milestones và tasks có bao phủ đầy đủ các yêu cầu trong mô tả mục tiêu và phù hợp trình độ đầu vào không?
2. **C2 — Tính logic tiên quyết & tiến trình sư phạm (Prerequisite & Pedagogical Progression):** Thứ tự milestone/task và đồ thị dependencies có đi từ nền tảng → thực hành → tổng hợp một cách tự nhiên, không nhảy cóc không?
3. **C3 — Độ cụ thể & tính hành động của task (Task Granularity & Actionability):** Tên task, mô tả và mục tiêu học tập có đủ rõ để người học bắt tay làm ngay trong một phiên học không?
4. **C4 — Tính khả thi lịch học & tải nhận thức (Schedule Realism & Cognitive Load):** Thời lượng từng task, mật độ theo ngày/tuần và tổng tải có tôn trọng khung ngày + quỹ giờ rảnh mà không gây kiệt sức hoặc quá thưa không?
5. **C5 — Độ rõ ràng tiêu chí hoàn thành & kiểm chứng (Completion Criteria & Measurability):** `completion_criteria` của milestone và task có đo lường/kiểm chứng được thay vì nói chung chung không?

## Bảng chấm điểm (Điền điểm 1–5)

| Mã Roadmap | C1: Độ phủ mục tiêu | C2: Tiến trình sư phạm | C3: Độ cụ thể task | C4: Khả thi lịch học | C5: Tiêu chí kiểm chứng | Tổng (/25) | Ghi chú / Nhận xét nổi bật |
|---|---:|---:|---:|---:|---:|---:|---|
| **R-01** | | | | | | | |
| **R-02** | | | | | | | |
| **R-03** | | | | | | | |
| **R-04** | | | | | | | |
| **R-05** | | | | | | | |
| **R-06** | | | | | | | |
| **R-07** | | | | | | | |
| **R-08** | | | | | | | |
| **R-09** | | | | | | | |
| **R-10** | | | | | | | |

---

## R-01 — Nền tảng Python & FastAPI cho người mới bắt đầu

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `BEGINNER`
- **Mô tả mục tiêu:** Học Python cơ bản (biến, hàm, cấu trúc dữ liệu, type hints), Pydantic v2 và xây dựng REST API CRUD với FastAPI + kiểm thử pytest cơ bản trong 30 ngày.
- **Khung thời gian:** `2026-11-17` → `2026-12-17`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_A — Thứ 2–Thứ 6: 90 phút/ngày; Thứ 7 & CN: 120 phút/ngày
- **Tóm tắt phạm vi lộ trình:** Lộ trình bao phủ toàn bộ mục tiêu: từ nền tảng cú pháp, cấu trúc dữ liệu và type hints của Python, đến xây dựng REST API CRUD hoàn chỉnh bằng FastAPI kết hợp Pydantic v2, và cuối cùng là kiểm thử tự động với pytest và TestClient.
- **Tổng quan cấu trúc:** 4 milestones | 12 tasks (PRACTICE: 4, PROJECT: 2, REVIEW: 2, THEORY: 4) | 11 dependencies | Tổng thời lượng: 810 phút (13.5 giờ) | Đã xếp lịch: 12/12 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Cú pháp Python cơ bản, Biến, Luồng điều khiển và Hàm (210 phút)
- **Mô tả:** Nắm vững cú pháp cơ bản của Python, cách khai báo biến, các kiểu dữ liệu nguyên thủy, cấu trúc rẽ nhánh, vòng lặp và cách định nghĩa hàm có tham số.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: Viết được script Python sử dụng biến, chuỗi và biểu thức số học cơ bản
  - `M1-O2`: Tổ chức mã nguồn thành các hàm tái sử dụng có tham số mặc định và xử lý luồng rẽ nhánh, vòng lặp chính xác
- **Tiêu chí hoàn thành Milestone:** Hoàn thành bộ bài tập thực hành viết hàm xử lý tính toán, rẽ nhánh logic và vòng lặp không phát sinh lỗi cú pháp hay logic cơ bản.
- **Khái niệm nền tảng:** `py-syntax-variables`, `py-control-flow-functions`

#### M2. Cấu trúc dữ liệu Python và Type Hints (180 phút)
- **Mô tả:** Làm chủ các cấu trúc dữ liệu cốt lõi (list, tuple, dict, set), kỹ thuật comprehension và áp dụng type annotations chuẩn bị cho việc làm việc với Pydantic.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: Lựa chọn và thao tác thành thạo cấu trúc dữ liệu phù hợp với bài toán kết hợp list/dict comprehension
  - `M2-O2`: Khai báo type hints rõ ràng cho biến, tham số hàm và giá trị trả về theo chuẩn Python typing
- **Tiêu chí hoàn thành Milestone:** Viết được chương trình thao tác, chuyển đổi và lọc dữ liệu dạng dictionary/list có gắn type hints đầy đủ và kiểm tra đạt chuẩn với mypy hoặc IDE linter.
- **Khái niệm nền tảng:** `py-collections-comprehensions`
- **Khái niệm mở rộng (chưa có trong KB):** `python-type-hints`

#### M3. Nền tảng RESTful API, FastAPI và Xác thực Schema với Pydantic v2 (240 phút)
- **Mô tả:** Hiểu kiến trúc RESTful HTTP và ứng dụng FastAPI kết hợp Pydantic v2 để xây dựng trọn vẹn các endpoint CRUD cho một tài nguyên cụ thể.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: Áp dụng chuẩn HTTP methods, status codes và thiết kế endpoint RESTful rõ ràng
  - `M3-O2`: Định nghĩa schema request/response với Pydantic BaseModel v2 để validate dữ liệu vào/ra tự động
  - `M3-O3`: Xây dựng trọn vẹn bộ endpoint CRUD với FastAPI APIRouter
- **Tiêu chí hoàn thành Milestone:** Xây dựng được một REST API CRUD hoàn chỉnh (Create, Read, Update, Delete) cho một tài nguyên trên FastAPI, tự động validate dữ liệu bằng Pydantic v2 và tương tác thành công qua Swagger UI (/docs).
- **Khái niệm nền tảng:** `http-rest-fundamentals`, `fastapi-routing-pydantic`

#### M4. Kiểm thử tự động REST API với Pytest và TestClient (180 phút)
- **Mô tả:** Thiết lập môi trường kiểm thử tự động với thư viện pytest, viết test case đơn vị và tích hợp các endpoint FastAPI bằng TestClient.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: Cấu hình và viết các test function cơ bản sử dụng thư viện pytest với assert và fixture
  - `M4-O2`: Sử dụng FastAPI TestClient để mô phỏng HTTP request và kiểm tra mã trạng thái, nội dung payload trả về của các endpoint CRUD
- **Tiêu chí hoàn thành Milestone:** Viết bộ kiểm thử pytest bao phủ các trường hợp thành công (200, 201) và lỗi dữ liệu (404, 422) cho toàn bộ API CRUD đã tạo, tất cả test case đều chạy pass.
- **Khái niệm mở rộng (chưa có trong KB):** `pytest-fundamentals`, `fastapi-testclient`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Cú pháp Python, Biến và Kiểu dữ liệu nguyên thủy | M1 | `THEORY` | 60 phút | 2026-11-17 19:00–20:00 (60p) | M1-O1 | Không |
| **T2**: Cấu trúc điều khiển và Tổ chức hàm trong Python | M1 | `PRACTICE` | 90 phút | 2026-11-18 19:00–19:45 (45p); 2026-11-18 19:45–20:30 (45p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Luyện tập tổng hợp: Cú pháp, Luồng điều khiển và Hàm | M1 | `REVIEW` | 60 phút | 2026-11-19 19:00–20:00 (60p) | M1-O1, M1-O2 | T2 (bắt buộc) |
| **T4**: Cấu trúc dữ liệu Collection và Comprehensions | M2 | `THEORY` | 60 phút | 2026-11-20 19:00–20:00 (60p) | M2-O1 | T3 (bắt buộc) |
| **T5**: Khai báo Type Hints chuẩn theo Python Typing | M2 | `PRACTICE` | 60 phút | 2026-11-21 19:00–20:00 (60p) | M2-O2 | T4 (bắt buộc) |
| **T6**: Thực hành chuyển đổi và lọc dữ liệu với Type Hints | M2 | `REVIEW` | 60 phút | 2026-11-21 20:00–21:00 (60p) | M2-O1, M2-O2 | T5 (bắt buộc) |
| **T7**: Nền tảng HTTP/REST và Schema Validation với Pydantic v2 | M3 | `THEORY` | 60 phút | 2026-11-22 19:00–20:00 (60p) | M3-O1, M3-O2 | T6 (bắt buộc) |
| **T8**: Thiết kế Routing và Path/Query Parameters trong FastAPI | M3 | `PRACTICE` | 90 phút | 2026-11-22 20:00–20:45 (45p); 2026-11-23 19:00–19:45 (45p) | M3-O2, M3-O3 | T7 (bắt buộc) |
| **T9**: Dự án nhỏ: Xây dựng RESTful API CRUD hoàn chỉnh | M3 | `PROJECT` | 90 phút | 2026-11-23 19:45–20:30 (45p); 2026-11-24 19:00–19:45 (45p) | M3-O1, M3-O2, M3-O3 | T8 (bắt buộc) |
| **T10**: Nền tảng kiểm thử tự động với Pytest | M4 | `THEORY` | 60 phút | 2026-11-25 19:00–20:00 (60p) | M4-O1 | T9 (bắt buộc) |
| **T11**: Kiểm thử API Endpoint với FastAPI TestClient | M4 | `PRACTICE` | 60 phút | 2026-11-26 19:00–20:00 (60p) | M4-O2 | T10 (bắt buộc) |
| **T12**: Xây dựng bộ kiểm thử hồi quy bao phủ toàn diện cho CRUD API | M4 | `PROJECT` | 60 phút | 2026-11-27 19:00–20:00 (60p) | M4-O1, M4-O2 | T11 (bắt buộc) |

#### Chi tiết nội dung M1 (3 tasks)

- **T1 — Cú pháp Python, Biến và Kiểu dữ liệu nguyên thủy** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu và thực hành khai báo biến, các kiểu dữ liệu nguyên thủy (int, float, str, bool), toán tử số học và ép kiểu trong Python.
  - *Mục tiêu học tập:* Nắm vững cú pháp cơ bản của Python và viết được script sử dụng biến, chuỗi và toán tử số học.
  - *Tiêu chí hoàn thành:* Viết được script Python tính toán và in kết quả chính xác, xử lý ép kiểu an toàn giữa chuỗi và số mà không gặp lỗi runtime.
  - *Concepts:* `py-syntax-variables`
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:00–20:00 (60p)
- **T2 — Cấu trúc điều khiển và Tổ chức hàm trong Python** (`PRACTICE`, 90 phút)
  - *Mô tả:* Học cách sử dụng câu lệnh rẽ nhánh if/elif/else, vòng lặp for/while và đóng gói mã nguồn vào các hàm với tham số mặc định.
  - *Mục tiêu học tập:* Tổ chức mã nguồn thành các hàm tái sử dụng có tham số và xử lý luồng rẽ nhánh, lặp chuẩn xác.
  - *Tiêu chí hoàn thành:* Cài đặt thành công 3-5 hàm xử lý logic nghiệp vụ có phân nhánh điều kiện và vòng lặp duyệt dữ liệu.
  - *Concepts:* `py-control-flow-functions`
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-18 19:00–19:45 (45p); 2026-11-18 19:45–20:30 (45p)
- **T3 — Luyện tập tổng hợp: Cú pháp, Luồng điều khiển và Hàm** (`REVIEW`, 60 phút)
  - *Mô tả:* Làm bài tập tổng hợp kết hợp biến, luồng điều khiển và hàm để giải quyết bài toán tính toán và định dạng dữ liệu hoàn chỉnh.
  - *Mục tiêu học tập:* Củng cố và áp dụng đồng bộ kiến thức cú pháp, rẽ nhánh và cấu trúc hàm.
  - *Tiêu chí hoàn thành:* Hoàn thành bài kiểm tra nhỏ gồm bài toán tính toán chi phí/xử lý văn bản chạy đúng 100% test case đầu vào.
  - *Concepts:* `py-syntax-variables`, `py-control-flow-functions`
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 19:00–20:00 (60p)

#### Chi tiết nội dung M2 (3 tasks)

- **T4 — Cấu trúc dữ liệu Collection và Comprehensions** (`THEORY`, 60 phút)
  - *Mô tả:* Khám phá các cấu trúc dữ liệu cốt lõi (List, Dict, Set, Tuple) và cú pháp List/Dict comprehension để biến đổi dữ liệu ngắn gọn.
  - *Mục tiêu học tập:* Lựa chọn cấu trúc dữ liệu phù hợp và sử dụng thành thạo comprehension để lọc, biến đổi dữ liệu.
  - *Tiêu chí hoàn thành:* Viết được các biểu thức list comprehension và dict comprehension thay thế cho vòng lặp lồng nhau truyền thống.
  - *Concepts:* `py-collections-comprehensions`
  - *Tiên quyết:* T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:00–20:00 (60p)
- **T5 — Khai báo Type Hints chuẩn theo Python Typing** (`PRACTICE`, 60 phút)
  - *Mô tả:* Học cú pháp type annotations cho biến, tham số hàm, giá trị trả về và các kiểu phức hợp (List, Dict, Optional, Union).
  - *Mục tiêu học tập:* Khai báo type hints rõ ràng, chính xác cho mã nguồn theo chuẩn PEP 484.
  - *Tiêu chí hoàn thành:* Gắn chú thích kiểu dữ liệu đầy đủ cho một module xử lý dữ liệu và kiểm tra không có lỗi cảnh báo qua linter/mypy.
  - *Concepts:* `py-collections-comprehensions`
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 19:00–20:00 (60p)
- **T6 — Thực hành chuyển đổi và lọc dữ liệu với Type Hints** (`REVIEW`, 60 phút)
  - *Mô tả:* Thực hành xây dựng chương trình đọc, lọc và tổng hợp dữ liệu danh mục/từ điển có kiểm soát kiểu dữ liệu nghiêm ngặt.
  - *Mục tiêu học tập:* Kết hợp nhuần nhuyễn collection operations và type hints để tạo mã nguồn sạch, an toàn kiểu.
  - *Tiêu chí hoàn thành:* Script thao tác dữ liệu dạng dictionary/list hoàn thành các tiêu chí lọc/gom nhóm và vượt qua kiểm tra kiểu tĩnh.
  - *Concepts:* `py-collections-comprehensions`
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 20:00–21:00 (60p)

#### Chi tiết nội dung M3 (3 tasks)

- **T7 — Nền tảng HTTP/REST và Schema Validation với Pydantic v2** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu các phương thức HTTP (GET, POST, PUT, DELETE), mã trạng thái HTTP và định nghĩa data schema với Pydantic BaseModel v2.
  - *Mục tiêu học tập:* Hiểu chuẩn thiết kế RESTful API và cách áp dụng Pydantic v2 để tự động parse, validate dữ liệu request/response.
  - *Tiêu chí hoàn thành:* Định nghĩa được các Pydantic schema (Create, Update, Response) có ràng buộc kiểu, độ dài và giá trị hợp lệ.
  - *Concepts:* `http-rest-fundamentals`, `fastapi-routing-pydantic`
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-22 19:00–20:00 (60p)
- **T8 — Thiết kế Routing và Path/Query Parameters trong FastAPI** (`PRACTICE`, 90 phút)
  - *Mô tả:* Sử dụng FastAPI APIRouter để xây dựng các route nhận path parameters, query parameters và request body với schema đã tạo.
  - *Mục tiêu học tập:* Tổ chức endpoint API chuẩn mực, xử lý tham số đường dẫn và tham số truy vấn đúng quy ước REST.
  - *Tiêu chí hoàn thành:* Tạo được router FastAPI tiếp nhận và kiểm tra hợp lệ dữ liệu đầu vào, trả về mã trạng thái 200, 201 hoặc 404 phù hợp.
  - *Concepts:* `fastapi-routing-pydantic`
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-22 20:00–20:45 (45p); 2026-11-23 19:00–19:45 (45p)
- **T9 — Dự án nhỏ: Xây dựng RESTful API CRUD hoàn chỉnh** (`PROJECT`, 90 phút)
  - *Mô tả:* Hiện thực hóa một dịch vụ RESTful API CRUD hoàn chỉnh (Create, Read, Update, Delete) cho một tài nguyên quản lý thực tế (ví dụ: Item, Task).
  - *Mục tiêu học tập:* Tích hợp toàn diện HTTP methods, Pydantic validation và FastAPI APIRouter thành một service hoàn chỉnh.
  - *Tiêu chí hoàn thành:* Mọi endpoint CRUD hoạt động trơn tru, validate đúng dữ liệu và tương tác thành công qua giao diện tự sinh Swagger UI (/docs).
  - *Concepts:* `http-rest-fundamentals`, `fastapi-routing-pydantic`
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:45–20:30 (45p); 2026-11-24 19:00–19:45 (45p)

#### Chi tiết nội dung M4 (3 tasks)

- **T10 — Nền tảng kiểm thử tự động với Pytest** (`THEORY`, 60 phút)
  - *Mô tả:* Cài đặt pytest, tìm hiểu quy ước đặt tên test file/function, sử dụng assert statements và xây dựng fixtures cơ bản.
  - *Mục tiêu học tập:* Nắm vững cơ chế vận hành của pytest và cấu hình được môi trường kiểm thử tự động trong Python.
  - *Tiêu chí hoàn thành:* Viết và thực thi thành công các test case đơn vị độc lập bằng pytest có sử dụng fixture mẫu.
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:00–20:00 (60p)
- **T11 — Kiểm thử API Endpoint với FastAPI TestClient** (`PRACTICE`, 60 phút)
  - *Mô tả:* Sử dụng starlette/fastapi TestClient để mô phỏng HTTP requests (GET, POST, PUT, DELETE) gửi tới các route của ứng dụng.
  - *Mục tiêu học tập:* Viết kịch bản kiểm thử tích hợp cho API endpoint, xác minh status code và cấu trúc payload JSON trả về.
  - *Tiêu chí hoàn thành:* Các test functions gửi request thành công tới TestClient và assert đúng payload cho các mã HTTP 200, 201.
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-11-26 19:00–20:00 (60p)
- **T12 — Xây dựng bộ kiểm thử hồi quy bao phủ toàn diện cho CRUD API** (`PROJECT`, 60 phút)
  - *Mô tả:* Hoàn thiện bộ test suite bao phủ cả các kịch bản thành công và các trường hợp biên, lỗi xác thực (422 Unprocessable Entity, 404 Not Found).
  - *Mục tiêu học tập:* Bao phủ toàn diện các ca kiểm thử cho ứng dụng CRUD API, đảm bảo độ tin cậy của mã nguồn.
  - *Tiêu chí hoàn thành:* Toàn bộ test suite chạy lệnh `pytest` đều pass mà không có lỗi hồi quy, bao phủ các trường hợp 200, 201, 404 và 422.
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-11-27 19:00–20:00 (60p)

---

## R-02 — Nền tảng Python & FastAPI cho người mới bắt đầu

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `BEGINNER`
- **Mô tả mục tiêu:** Học Python cơ bản (biến, hàm, cấu trúc dữ liệu, type hints), Pydantic v2 và xây dựng REST API CRUD với FastAPI + kiểm thử pytest cơ bản trong 30 ngày.
- **Khung thời gian:** `2026-11-17` → `2026-12-17`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_A — Thứ 2–Thứ 6: 90 phút/ngày; Thứ 7 & CN: 120 phút/ngày
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE bao phủ toàn bộ mục tiêu đề ra trong 30 ngày: từ nền tảng Python cơ bản (cú pháp, biến, hàm, cấu trúc dữ liệu, type hints) đến Pydantic v2, phát triển RESTful CRUD API với FastAPI và kiểm thử tự động với Pytest.
- **Tổng quan cấu trúc:** 5 milestones | 18 tasks (PRACTICE: 6, PROJECT: 2, REVIEW: 2, THEORY: 8) | 17 dependencies | Tổng thời lượng: 1200 phút (20.0 giờ) | Đã xếp lịch: 18/18 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Cơ bản về Cú pháp Python, Kiểu dữ liệu và Cấu trúc điều khiển (210 phút)
- **Mô tả:** Nắm vững cú pháp cơ bản, biến, kiểu dữ liệu nguyên thủy, ép kiểu và các cấu trúc điều khiển rẽ nhánh, vòng lặp trong Python.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: Khai báo biến, sử dụng các kiểu dữ liệu nguyên thủy và toán tử số học/logic chính xác
  - `M1-O2`: Áp dụng cấu trúc điều khiển if/elif/else và vòng lặp for/while để xử lý luồng logic chương trình
- **Tiêu chí hoàn thành Milestone:** Viết được tập lệnh Python giải quyết các bài toán logic cơ bản mà không có lỗi cú pháp hoặc lỗi logic lặp.
- **Khái niệm nền tảng:** `py-syntax-variables`, `py-control-flow-functions`

#### M2. Cấu trúc dữ liệu Python, Hàm nâng cao và Type Hints (240 phút)
- **Mô tả:** Làm chủ các cấu trúc dữ liệu cốt lõi (list, tuple, dict, set), kỹ thuật comprehension, định nghĩa hàm với type hints chuẩn PEP 484.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: Thao tác thuần thục với list, dict, set, tuple và áp dụng comprehension ngắn gọn
  - `M2-O2`: Định nghĩa hàm tái sử dụng với tham số mặc định, *args, **kwargs và gắn chú thích kiểu dữ liệu (type hints) rõ ràng
- **Tiêu chí hoàn thành Milestone:** Hoàn thành bài tập xử lý dữ liệu tổng hợp sử dụng dict/list comprehension và hàm có type hints đầy đủ được mypy kiểm tra hợp lệ.
- **Khái niệm nền tảng:** `py-collections-comprehensions`
- **Khái niệm mở rộng (chưa có trong KB):** `python-type-hints-pep484`

#### M3. Nền tảng HTTP/REST và Xác thực mô hình dữ liệu với Pydantic v2 (240 phút)
- **Mô tả:** Hiểu kiến trúc RESTful, HTTP methods/status codes và sử dụng Pydantic v2 BaseModel để định nghĩa schema, tiền xử lý và validate dữ liệu.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: Phân biệt các phương thức HTTP, quy chuẩn thiết kế RESTful endpoint và mã phản hồi chuẩn
  - `M3-O2`: Xây dựng Pydantic v2 schemas với Field, validator tùy biến và serialize dữ liệu an toàn
- **Tiêu chí hoàn thành Milestone:** Tạo được bộ schema Pydantic v2 hoàn chỉnh cho bài toán CRUD, kiểm thử thành công việc parse và validate dữ liệu đúng/sai.
- **Khái niệm nền tảng:** `http-rest-fundamentals`
- **Khái niệm mở rộng (chưa có trong KB):** `pydantic-v2-schema-validation`

#### M4. Xây dựng REST API CRUD với FastAPI (300 phút)
- **Mô tả:** Tạo ứng dụng FastAPI, triển khai đầy đủ các endpoint CRUD, quản lý path/query/body parameters, xử lý HTTP exceptions và tích hợp Swagger UI.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: Xây dựng ứng dụng FastAPI với APIRouter và phân chia module rõ ràng
  - `M4-O2`: Hiện thực hóa đầy đủ các thao tác CRUD với dữ liệu in-memory/mock và xử lý ngoại lệ HTTP chuẩn
- **Tiêu chí hoàn thành Milestone:** Chạy máy chủ Uvicorn, thực hiện kiểm thử thành công toàn bộ luồng Create, Read, Update, Delete qua FastAPI Swagger UI tương tác.
- **Khái niệm nền tảng:** `fastapi-routing-pydantic`

#### M5. Kiểm thử tự động API với Pytest và TestClient (210 phút)
- **Mô tả:** Học cách viết unit test và integration test cho các endpoint FastAPI bằng thư viện pytest kết hợp HTTPX/TestClient.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M5-O1`: Thiết lập cấu trúc thư mục test, fixtures với pytest
  - `M5-O2`: Viết các kịch bản test case thành công và thất bại cho toàn bộ endpoint CRUD sử dụng FastAPI TestClient
- **Tiêu chí hoàn thành Milestone:** Bộ test suite chạy bằng lệnh `pytest` vượt qua 100% test cases cho các endpoint CRUD đã xây dựng.
- **Khái niệm mở rộng (chưa có trong KB):** `fastapi-testing-pytest-testclient`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Lý thuyết Cú pháp Python, Biến và Kiểu dữ liệu nguyên thủy | M1 | `THEORY` | 60 phút | 2026-11-17 19:00–20:00 (60p) | M1-O1 | Không |
| **T2**: Lý thuyết và Thực hành Cấu trúc điều khiển (if/else, loops) | M1 | `THEORY` | 60 phút | 2026-11-18 19:00–20:00 (60p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Thực hành giải bài toán logic thuật toán cơ bản với Python | M1 | `PRACTICE` | 90 phút | 2026-11-19 19:00–19:45 (45p); 2026-11-19 19:45–20:30 (45p) | M1-O1, M1-O2 | T2 (bắt buộc) |
| **T4**: Cấu trúc dữ liệu Python: List, Tuple, Set, Dict và Comprehensions | M2 | `THEORY` | 60 phút | 2026-11-20 19:00–20:00 (60p) | M2-O1 | T3 (bắt buộc) |
| **T5**: Định nghĩa Hàm nâng cao, Arguments và Type Hints (PEP 484) | M2 | `THEORY` | 60 phút | 2026-11-21 19:00–20:00 (60p) | M2-O2 | T4 (bắt buộc) |
| **T6**: Thực hành cấu trúc hóa dữ liệu và kiểm tra Type Hints | M2 | `PRACTICE` | 60 phút | 2026-11-21 20:00–21:00 (60p) | M2-O1, M2-O2 | T5 (bắt buộc) |
| **T7**: Ôn tập và Tối ưu hóa mã nguồn Python cơ bản | M2 | `REVIEW` | 60 phút | 2026-11-22 19:00–20:00 (60p) | M2-O1, M2-O2 | T6 (bắt buộc) |
| **T8**: Kiến trúc HTTP/RESTful và Quy chuẩn thiết kế API | M3 | `THEORY` | 60 phút | 2026-11-22 20:00–21:00 (60p) | M3-O1 | T7 (bắt buộc) |
| **T9**: Xác thực mô hình dữ liệu với Pydantic v2 | M3 | `THEORY` | 60 phút | 2026-11-23 19:00–20:00 (60p) | M3-O2 | T8 (bắt buộc) |
| **T10**: Thực hành thiết kế Schemas Pydantic v2 cho CRUD Model | M3 | `PRACTICE` | 60 phút | 2026-11-24 19:00–20:00 (60p) | M3-O2 | T9 (bắt buộc) |
| **T11**: Ôn tập và Tổng hợp kiến thức HTTP & Pydantic Validation | M3 | `REVIEW` | 60 phút | 2026-11-25 19:00–20:00 (60p) | M3-O1, M3-O2 | T10 (bắt buộc) |
| **T12**: Khởi tạo ứng dụng FastAPI và Cấu trúc dự án với APIRouter | M4 | `THEORY` | 60 phút | 2026-11-26 19:00–20:00 (60p) | M4-O1 | T11 (bắt buộc) |
| **T13**: Hiện thực hóa Endpoint Create & Read với In-memory Storage | M4 | `PRACTICE` | 60 phút | 2026-11-27 19:00–20:00 (60p) | M4-O2 | T12 (bắt buộc) |
| **T14**: Hiện thực hóa Endpoint Update, Delete và Xử lý HTTPException | M4 | `PRACTICE` | 60 phút | 2026-11-28 19:00–20:00 (60p) | M4-O2 | T13 (bắt buộc) |
| **T15**: Xây dựng Mini Project: Hoàn thiện CRUD REST API với FastAPI | M4 | `PROJECT` | 120 phút | 2026-11-28 20:00–21:00 (60p); 2026-11-29 19:00–20:00 (60p) | M4-O1, M4-O2 | T14 (bắt buộc) |
| **T16**: Cơ chế kiểm thử Pytest và cấu hình Test Fixtures | M5 | `THEORY` | 60 phút | 2026-11-29 20:00–21:00 (60p) | M5-O1 | T15 (bắt buộc) |
| **T17**: Kiểm thử API Endpoint với FastAPI TestClient | M5 | `PRACTICE` | 60 phút | 2026-11-30 19:00–20:00 (60p) | M5-O2 | T16 (bắt buộc) |
| **T18**: Hoàn thiện Bộ kiểm thử tự động toàn diện cho CRUD API | M5 | `PROJECT` | 90 phút | 2026-12-01 19:00–19:45 (45p); 2026-12-01 19:45–20:30 (45p) | M5-O1, M5-O2 | T17 (bắt buộc) |

#### Chi tiết nội dung M1 (3 tasks)

- **T1 — Lý thuyết Cú pháp Python, Biến và Kiểu dữ liệu nguyên thủy** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu quy tắc đặt tên biến, các kiểu dữ liệu cơ bản (int, float, str, bool), toán tử số học, logic và ép kiểu an toàn trong Python.
  - *Mục tiêu học tập:* Nắm vững cú pháp cơ bản của Python, cách khai báo biến và vận hành các toán tử số học/logic.
  - *Tiêu chí hoàn thành:* Tóm tắt được các kiểu dữ liệu nguyên thủy và giải thích đúng quy tắc ép kiểu cùng độ ưu tiên toán tử qua ví dụ minh họa.
  - *Concepts:* `py-syntax-variables`
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:00–20:00 (60p)
- **T2 — Lý thuyết và Thực hành Cấu trúc điều khiển (if/else, loops)** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu và thực hành cấu trúc rẽ nhánh if/elif/else cùng các vòng lặp for/while, sử dụng break, continue để kiểm soát luồng thực thi.
  - *Mục tiêu học tập:* Hiểu rõ cơ chế điều hướng luồng chương trình và cách duyệt tập hợp dữ liệu bằng vòng lặp.
  - *Tiêu chí hoàn thành:* Viết được các đoạn mã lặp và rẽ nhánh giải quyết các điều kiện logic đa tầng mà không gặp lỗi vô tận.
  - *Concepts:* `py-control-flow-functions`
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-18 19:00–20:00 (60p)
- **T3 — Thực hành giải bài toán logic thuật toán cơ bản với Python** (`PRACTICE`, 90 phút)
  - *Mô tả:* Lập trình giải quyết các bài toán thao tác chuỗi, kiểm tra số nguyên tố, tính toán số học sử dụng cấu trúc điều khiển và biến.
  - *Mục tiêu học tập:* Vận dụng kết hợp biến, toán tử và cấu trúc điều khiển để xây dựng script xử lý logic hoàn chỉnh.
  - *Tiêu chí hoàn thành:* Hoàn thành tập lệnh Python giải quyết tối thiểu 3 bài toán logic mà không có lỗi cú pháp hoặc ngoại lệ runtime.
  - *Concepts:* `py-syntax-variables`, `py-control-flow-functions`
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 19:00–19:45 (45p); 2026-11-19 19:45–20:30 (45p)

#### Chi tiết nội dung M2 (4 tasks)

- **T4 — Cấu trúc dữ liệu Python: List, Tuple, Set, Dict và Comprehensions** (`THEORY`, 60 phút)
  - *Mô tả:* Học cách khởi tạo, truy xuất và biến đổi dữ liệu trên List, Tuple, Set, Dict. Thực hành viết List/Dict Comprehension cô đọng.
  - *Mục tiêu học tập:* Hiểu rõ đặc điểm mutable/immutable và ứng dụng comprehension để tinh gọn xử lý dữ liệu.
  - *Tiêu chí hoàn thành:* Giải thích được sự khác nhau giữa các collection và chuyển đổi thành công vòng lặp truyền thống sang dạng comprehension.
  - *Concepts:* `py-collections-comprehensions`
  - *Tiên quyết:* T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:00–20:00 (60p)
- **T5 — Định nghĩa Hàm nâng cao, Arguments và Type Hints (PEP 484)** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu cách định nghĩa hàm với tham số mặc định, *args, **kwargs, gán Type Hints theo chuẩn PEP 484 và kiểm tra kiểu với mypy.
  - *Mục tiêu học tập:* Nắm vững cách xây dựng hàm linh hoạt và sử dụng Type Hints để tăng độ an toàn cho mã nguồn.
  - *Tiêu chí hoàn thành:* Viết được các hàm nhận tham số biến thiên và khai báo chú thích kiểu đầy đủ cho đối số lẫn giá trị trả về.
  - *Concepts:* `py-control-flow-functions`
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 19:00–20:00 (60p)
- **T6 — Thực hành cấu trúc hóa dữ liệu và kiểm tra Type Hints** (`PRACTICE`, 60 phút)
  - *Mô tả:* Viết module xử lý tập dữ liệu mẫu (danh sách học viên/sản phẩm) sử dụng comprehension, cấu trúc dữ liệu tối ưu và type hints chuẩn.
  - *Mục tiêu học tập:* Áp dụng thuần thục collections, hàm nâng cao và Type Hints vào bài toán tiền xử lý dữ liệu thực tế.
  - *Tiêu chí hoàn thành:* Mã nguồn chạy thành công và vượt qua công cụ kiểm tra tĩnh mypy mà không có cảnh báo vi phạm kiểu.
  - *Concepts:* `py-collections-comprehensions`
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 20:00–21:00 (60p)
- **T7 — Ôn tập và Tối ưu hóa mã nguồn Python cơ bản** (`REVIEW`, 60 phút)
  - *Mô tả:* Đánh giá lại phong cách lập trình (PEP 8), tối ưu độ phức tạp thuật toán và tái cấu trúc mã nguồn đã viết từ M1 và M2.
  - *Mục tiêu học tập:* Củng cố kiến thức nền tảng Python, nâng cao kỹ năng đọc hiểu và refactor code sạch.
  - *Tiêu chí hoàn thành:* Hoàn thành bản refactor chuẩn hóa định dạng, có docstrings và type hints rõ ràng cho tất cả hàm tiện ích.
  - *Concepts:* `py-collections-comprehensions`, `py-control-flow-functions`
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-22 19:00–20:00 (60p)

#### Chi tiết nội dung M3 (4 tasks)

- **T8 — Kiến trúc HTTP/RESTful và Quy chuẩn thiết kế API** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu mô hình Client-Server, HTTP Methods (GET, POST, PUT, DELETE, PATCH), HTTP Status Codes (2xx, 4xx, 5xx) và tính lũy đẳng (idempotency).
  - *Mục tiêu học tập:* Nắm vững nguyên lý hoạt động của giao thức HTTP và cách thiết kế tài nguyên RESTful chuẩn mực.
  - *Tiêu chí hoàn thành:* Vẽ hoặc lập bảng phân định đúng vai trò, tính an toàn/lũy đẳng của từng phương thức HTTP tương ứng với các thao tác dữ liệu.
  - *Concepts:* `http-rest-fundamentals`
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-22 20:00–21:00 (60p)
- **T9 — Xác thực mô hình dữ liệu với Pydantic v2** (`THEORY`, 60 phút)
  - *Mô tả:* Khám phá Pydantic v2 BaseModel, Field validation, custom validators (@field_validator, @model_validator) và serialization sang JSON.
  - *Mục tiêu học tập:* Hiểu cách Pydantic v2 parse và validate dữ liệu đầu vào tự động dựa trên type annotations.
  - *Tiêu chí hoàn thành:* Định nghĩa được các model Pydantic có ràng buộc min/max length, regex và custom validator báo lỗi chính xác.
  - *Concepts:* `http-rest-fundamentals`
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:00–20:00 (60p)
- **T10 — Thực hành thiết kế Schemas Pydantic v2 cho CRUD Model** (`PRACTICE`, 60 phút)
  - *Mô tả:* Xây dựng các bộ schemas Create, Read, Update cho thực thể nghiệp vụ (ví dụ: Item/User) với kiểm tra dữ liệu đầu vào nghiêm ngặt.
  - *Mục tiêu học tập:* Thành thạo việc phân tách request schemas và response schemas bằng Pydantic v2.
  - *Tiêu chí hoàn thành:* Viết script kiểm thử parse dữ liệu hợp lệ và bắt ngoại lệ ValidationError khi truyền sai kiểu dữ liệu hoặc vi phạm ràng buộc.
  - *Concepts:* `http-rest-fundamentals`
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-24 19:00–20:00 (60p)
- **T11 — Ôn tập và Tổng hợp kiến thức HTTP & Pydantic Validation** (`REVIEW`, 60 phút)
  - *Mô tả:* Rà soát lại sự liên kết giữa HTTP Status Codes và các lỗi validate từ Pydantic; chuẩn hóa cấu trúc lỗi trả về.
  - *Mục tiêu học tập:* Đảm bảo sự nhất quán giữa đặc tả REST API và mô hình kiểm thực dữ liệu.
  - *Tiêu chí hoàn thành:* Tổng hợp tài liệu thiết kế API endpoint mapping với schemas Pydantic tương ứng cùng danh mục mã phản hồi dự kiến.
  - *Concepts:* `http-rest-fundamentals`
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:00–20:00 (60p)

#### Chi tiết nội dung M4 (4 tasks)

- **T12 — Khởi tạo ứng dụng FastAPI và Cấu trúc dự án với APIRouter** (`THEORY`, 60 phút)
  - *Mô tả:* Cài đặt FastAPI, Uvicorn; thiết lập cấu trúc mã nguồn module hóa sử dụng APIRouter để phân chia tài nguyên hợp lý.
  - *Mục tiêu học tập:* Hiểu vòng đời ứng dụng FastAPI và cách tổ chức các route có cấu trúc rõ ràng, dễ bảo trì.
  - *Tiêu chí hoàn thành:* Khởi chạy server Uvicorn và truy cập thành công tài liệu Swagger UI tự động tại đường dẫn /docs.
  - *Concepts:* `fastapi-routing-pydantic`
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-11-26 19:00–20:00 (60p)
- **T13 — Hiện thực hóa Endpoint Create & Read với In-memory Storage** (`PRACTICE`, 60 phút)
  - *Mô tả:* Viết endpoint POST (tạo mới tài nguyên) và GET (danh sách & chi tiết theo ID), xử lý Path và Query Parameters kết hợp Pydantic.
  - *Mục tiêu học tập:* Làm chủ việc tiếp nhận tham số đường dẫn, query string và request body trong FastAPI.
  - *Tiêu chí hoàn thành:* Gửi request qua Swagger UI tạo thành công bản ghi mới (mã 201) và đọc lại thông tin bản ghi vừa tạo (mã 200).
  - *Concepts:* `fastapi-routing-pydantic`
  - *Tiên quyết:* T12 (bắt buộc) | *Lịch dự kiến:* 2026-11-27 19:00–20:00 (60p)
- **T14 — Hiện thực hóa Endpoint Update, Delete và Xử lý HTTPException** (`PRACTICE`, 60 phút)
  - *Mô tả:* Hoàn thiện endpoint PUT/PATCH và DELETE; tích hợp HTTPException để trả về lỗi 404 Not Found hoặc 400 Bad Request chuẩn chuẩn mực.
  - *Mục tiêu học tập:* Xây dựng trọn vẹn vòng đời thao tác dữ liệu CRUD và kiểm soát lỗi nghiệp vụ bằng HTTPException.
  - *Tiêu chí hoàn thành:* Thực hiện thành công thao tác cập nhật và xóa tài nguyên, đồng thời nhận phản hồi lỗi 404 khi truy vấn ID không tồn tại.
  - *Concepts:* `fastapi-routing-pydantic`
  - *Tiên quyết:* T13 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 19:00–20:00 (60p)
- **T15 — Xây dựng Mini Project: Hoàn thiện CRUD REST API với FastAPI** (`PROJECT`, 120 phút)
  - *Mô tả:* Tổng hợp mã nguồn thành dự án quản lý tài nguyên hoàn chỉnh (ví dụ: Task/Book Management) có đầy đủ routing, validation và error handling.
  - *Mục tiêu học tập:* Tích hợp toàn bộ kỹ năng định tuyến, xác thực dữ liệu và xử lý phản hồi HTTP vào một ứng dụng backend mạch lạc.
  - *Tiêu chí hoàn thành:* Dự án chạy trơn tru trên Uvicorn, vượt qua bài kiểm thử thủ công tất cả chức năng CRUD trên giao diện OpenAPI Swagger.
  - *Concepts:* `fastapi-routing-pydantic`
  - *Tiên quyết:* T14 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 20:00–21:00 (60p); 2026-11-29 19:00–20:00 (60p)

#### Chi tiết nội dung M5 (3 tasks)

- **T16 — Cơ chế kiểm thử Pytest và cấu hình Test Fixtures** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu kiến trúc của framework pytest, quy ước đặt tên tệp/hàm test, sử dụng assertions và xây dựng @pytest.fixture tái sử dụng.
  - *Mục tiêu học tập:* Hiểu nguyên lý viết unit/integration tests tự động và cơ chế cô lập môi trường kiểm thử với Fixtures.
  - *Tiêu chí hoàn thành:* Thiết lập cấu trúc thư mục tests/ chuẩn và chạy thành công lệnh pytest cho các hàm toán học/logic đơn giản.
  - *Tiên quyết:* T15 (bắt buộc) | *Lịch dự kiến:* 2026-11-29 20:00–21:00 (60p)
- **T17 — Kiểm thử API Endpoint với FastAPI TestClient** (`PRACTICE`, 60 phút)
  - *Mô tả:* Sử dụng Starlette TestClient/HTTPX trong Pytest để mô phỏng HTTP requests đến các endpoint FastAPI mà không cần bật server thủ công.
  - *Mục tiêu học tập:* Thành thạo việc gửi request giả lập và kiểm tra assertions trên Status Code, Response Body JSON headers.
  - *Tiêu chí hoàn thành:* Viết test cases kiểm tra thành công luồng Create (201) và Read (200), assert đúng schema trả về.
  - *Concepts:* `fastapi-routing-pydantic`
  - *Tiên quyết:* T16 (bắt buộc) | *Lịch dự kiến:* 2026-11-30 19:00–20:00 (60p)
- **T18 — Hoàn thiện Bộ kiểm thử tự động toàn diện cho CRUD API** (`PROJECT`, 90 phút)
  - *Mô tả:* Viết bổ sung các ca kiểm thử cho trường hợp biên, lỗi xác thực dữ liệu đầu vào (422) và không tìm thấy tài nguyên (404).
  - *Mục tiêu học tập:* Xây dựng bộ kiểm thử tích hợp hoàn chỉnh bảo đảm độ tin cậy và chất lượng cho API backend.
  - *Tiêu chí hoàn thành:* Lệnh `pytest` thực thi toàn bộ test suite chạy thành công 100% không có failure hay error nào.
  - *Concepts:* `fastapi-routing-pydantic`
  - *Tiên quyết:* T17 (bắt buộc) | *Lịch dự kiến:* 2026-12-01 19:00–19:45 (45p); 2026-12-01 19:45–20:30 (45p)

---

## R-03 — Data Engineering thực chiến với Apache Airflow & dbt

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Xây dựng pipeline ELT hiện đại: thiết kế DAG Airflow idempotent (XCom, TaskFlow API, retry/SLA), mô hình hóa dữ liệu staging/mart với dbt (tests, snapshots, incremental models) và kiểm soát chất lượng dữ liệu.
- **Khung thời gian:** `2026-11-17` → `2026-12-22`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_B — Thứ 2, Thứ 4, Thứ 6: 19:30–21:00 (90 phút); Thứ 7: 09:00–12:00 (180 phút)
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE bao phủ toàn diện toàn bộ mục tiêu Data Engineering thực chiến với Apache Airflow và dbt: từ nền tảng ELT, thiết kế DAG TaskFlow idempotent, retry/SLA, đến mô hình hóa dữ liệu staging/marts, incremental models, snapshot SCD Type 2, kiểm thử chất lượng và tích hợp điều phối toàn diện.
- **Tổng quan cấu trúc:** 6 milestones | 12 tasks (PRACTICE: 5, PROJECT: 1, REVIEW: 2, THEORY: 4) | 11 dependencies | Tổng thời lượng: 1080 phút (18.0 giờ) | Đã xếp lịch: 12/12 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Thiết kế Luồng ELT Hiện đại & Nền tảng Dữ liệu Quan hệ với PostgreSQL (240 phút)
- **Mô tả:** Xác lập kiến trúc ELT phân lớp, chuẩn hóa mô hình dữ liệu quan hệ nguồn và thiết lập môi trường Data Warehouse/Data Lakehouse cục bộ với Docker và PostgreSQL.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Phân tích kiến trúc ELT hiện đại và phân biệt mô hình dữ liệu 3NF tầng nguồn với Dimensional Modeling (Star Schema) tầng phân tích
  - `M1-O2`: M1-O2: Khởi tạo môi trường phát triển Data Engineering tích hợp PostgreSQL và cấu hình cơ sở dữ liệu nguồn/đích
- **Tiêu chí hoàn thành Milestone:** Thiết kế hoàn chỉnh sơ đồ ERD dữ liệu nguồn chuẩn 3NF và khởi chạy thành công cơ sở dữ liệu phân tích cục bộ qua Docker Compose.
- **Khái niệm nền tảng:** `sql-relational-modeling`
- **Khái niệm mở rộng (chưa có trong KB):** `elt-modern-data-stack-architecture`, `docker-data-engineering-env`

#### M2. Lập trình Pipeline Tự động hóa với Apache Airflow & TaskFlow API (360 phút)
- **Mô tả:** Nắm vững nguyên lý hoạt động của Apache Airflow, xây dựng DAGs theo phong cách TaskFlow API hiện đại, xử lý truyền thông tin XCom an toàn và quản lý cấu hình kết nối.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Xây dựng DAGs bằng TaskFlow API (@dag, @task) với cấu trúc mô-đun hóa rõ ràng và đúng chuẩn cú pháp Python
  - `M2-O2`: M2-O2: Trao đổi dữ liệu metadata giữa các task qua Airflow XCom mà không vi phạm nguyên tắc anti-pattern về dung lượng
  - `M2-O3`: M2-O3: Quản lý Connections, Variables và cấu hình môi trường bảo mật trên Airflow Webserver/Scheduler
- **Tiêu chí hoàn thành Milestone:** Triển khai được ít nhất 2 DAGs chạy tự động thành công trên Airflow Web UI sử dụng TaskFlow API và trao đổi metadata qua XCom.
- **Khái niệm nền tảng:** `py-oop-dataclasses`
- **Khái niệm mở rộng (chưa có trong KB):** `apache-airflow-taskflow-api`, `airflow-xcom-architecture`, `airflow-dag-scheduling-execution`

#### M3. Bảo đảm Tính Lũy Đẳng (Idempotency), Khả Năng Phục Hồi & Quản lý SLA trong Airflow (300 phút)
- **Mô tả:** Tối ưu hóa các DAGs sản xuất với tính chất lũy đẳng (idempotent), cơ chế retry thông minh, callback thông báo lỗi và giám sát cam kết thời gian hoàn thành (SLA).
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Áp dụng kỹ thuật phân vùng theo execution_date và Upsert/Merge để đảm bảo pipeline chạy lại nhiều lần không trùng lặp dữ liệu (idempotency)
  - `M3-O2`: M3-O2: Cấu hình chính sách retry, exponential backoff, on_failure_callback và SLA miss alerts để cảnh báo sự cố tự động
- **Tiêu chí hoàn thành Milestone:** Kiểm thử mô phỏng lỗi gián đoạn pipeline và backfill thành công dữ liệu lịch sử 7 ngày mà không sinh ra bản ghi trùng lặp hoặc vi phạm SLA.
- **Khái niệm mở rộng (chưa có trong KB):** `pipeline-idempotency-backfill`, `airflow-retries-sla-callbacks`

#### M4. Mô hình hóa Dữ liệu Tầng Staging & Marts với dbt Core (360 phút)
- **Mô tả:** Cài đặt dbt Core, kết nối Data Warehouse, xây dựng cấu trúc dự án chuẩn dbt với các tầng Staging (nguồn thô), Intermediate (làm sạch/biến đổi) và Marts (chiều/bản ghi sự kiện).
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Thiết lập cấu trúc dự án dbt tiêu chuẩn (models, staging, marts, seeds) và quản lý dependency thông qua hàm ref() và source()
  - `M4-O2`: M4-O2: Xây dựng các model staging làm sạch dữ liệu và marts phân tích theo cấu trúc Fact/Dimension (Kimball Star Schema)
- **Tiêu chí hoàn thành Milestone:** Thực thi lệnh `dbt run` thành công toàn bộ chuỗi mô hình từ staging tới marts, sinh ra sơ đồ DAG lineage hoàn chỉnh trên tài liệu dbt docs.
- **Khái niệm nền tảng:** `sql-relational-modeling`
- **Khái niệm mở rộng (chưa có trong KB):** `dbt-project-structure-ref-source`, `dbt-dimensional-modeling-star-schema`

#### M5. Nâng cao dbt: Incremental Models, Snapshot (SCD Type 2) & Kiểm thử Dữ liệu (360 phút)
- **Mô tả:** Tối ưu hóa chi phí và tốc độ truy vấn với incremental loading, theo dõi biến động dữ liệu lịch sử bằng dbt snapshots và thiết lập chốt kiểm soát chất lượng dữ liệu tự động.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M5-O1`: M5-O1: Triển khai incremental models với `is_incremental()` macro và chiến lược merge/insert_overwrite để xử lý dữ liệu lớn
  - `M5-O2`: M5-O2: Thiết lập dbt snapshots để theo dõi sự biến đổi thuộc tính theo thời gian (Slowly Changing Dimensions - SCD Type 2)
  - `M5-O3`: M5-O3: Định nghĩa generic tests (unique, not_null, accepted_values, relationships) và singular tests để chặn đứng dữ liệu bẩn
- **Tiêu chí hoàn thành Milestone:** Thực thi kiểm thử `dbt test` đạt 100% pass trên toàn bộ mart models và chạy cập nhật gia tăng (incremental run) kiểm chứng tính toàn vẹn của SCD Type 2 snapshot.
- **Khái niệm mở rộng (chưa có trong KB):** `dbt-incremental-models`, `dbt-snapshots-scd2`, `dbt-data-quality-tests`

#### M6. Tích hợp Toàn diện ELT: Điều phối dbt bằng Airflow & Giám sát Vận hành (420 phút)
- **Mô tả:** Ghép nối hoàn chỉnh Airflow và dbt thành một hệ thống ELT khép kín phục vụ sản xuất thông qua Cosmos/BashOperator, đồng thời hoàn thiện quy trình kiểm soát chất lượng đầu-cuối.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M6-O1`: M6-O1: Tích hợp dbt vào Airflow pipeline bằng cách chuyển đổi dbt DAG sang Airflow tasks tự động (sử dụng Astronomer Cosmos hoặc Subprocess/BashOperator)
  - `M6-O2`: M6-O2: Xây dựng cơ chế chốt chặn chất lượng dữ liệu đầu nguồn (Data Quality Gates) ngăn chặn task phân tích hạ nguồn thực thi khi test thất bại
  - `M6-O3`: M6-O3: Đóng gói toàn bộ pipeline ELT và tài liệu hóa quy trình vận hành, bảo trì, giám sát hạ tầng dữ liệu
- **Tiêu chí hoàn thành Milestone:** Chạy trơn tru pipeline ELT đầu-cuối từ trích xuất, nạp, biến đổi incremental bằng dbt, thực hiện test chất lượng dữ liệu và bắn cảnh báo thành công qua Slack/Email khi có lỗi.
- **Khái niệm nền tảng:** `py-oop-dataclasses`
- **Khái niệm mở rộng (chưa có trong KB):** `airflow-dbt-integration-cosmos`, `end-to-end-data-quality-governance`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Tổng quan kiến trúc ELT và Mô hình hóa dữ liệu quan hệ (3NF vs Star Schema) | M1 | `THEORY` | 90 phút | 2026-11-18 19:30–20:15 (45p); 2026-11-18 20:15–21:00 (45p) | M1-O1 | Không |
| **T2**: Thiết lập môi trường PostgreSQL và thiết kế Schema dữ liệu mẫu | M1 | `PRACTICE` | 90 phút | 2026-11-20 19:30–20:15 (45p); 2026-11-20 20:15–21:00 (45p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Lập trình DAG với Apache Airflow TaskFlow API | M2 | `THEORY` | 90 phút | 2026-11-21 09:00–09:45 (45p); 2026-11-21 09:45–10:30 (45p) | M2-O1 | T2 (bắt buộc) |
| **T4**: Quản lý XCom, Airflow Connections và Variables | M2 | `PRACTICE` | 90 phút | 2026-11-21 10:30–11:15 (45p); 2026-11-21 11:15–12:00 (45p) | M2-O2, M2-O3 | T3 (bắt buộc) |
| **T5**: Thiết kế Pipeline Idempotent với Upsert và Execution Date | M3 | `THEORY` | 90 phút | 2026-11-23 19:30–20:15 (45p); 2026-11-23 20:15–21:00 (45p) | M3-O1 | T4 (bắt buộc) |
| **T6**: Cấu hình Retry, Alerts, Callback và Backfill thực chiến | M3 | `PRACTICE` | 90 phút | 2026-11-25 19:30–20:15 (45p); 2026-11-25 20:15–21:00 (45p) | M3-O1, M3-O2 | T5 (bắt buộc) |
| **T7**: Khởi tạo dự án dbt Core và quản lý nguồn dữ liệu (Sources & Ref) | M4 | `THEORY` | 90 phút | 2026-11-27 19:30–20:15 (45p); 2026-11-27 20:15–21:00 (45p) | M4-O1 | T6 (bắt buộc) |
| **T8**: Xây dựng Tầng Phân tích Marts với Star Schema trên dbt | M4 | `PRACTICE` | 90 phút | 2026-11-28 09:00–09:45 (45p); 2026-11-28 09:45–10:30 (45p) | M4-O2 | T7 (bắt buộc) |
| **T9**: Cài đặt dbt Incremental Models và Snapshots (SCD Type 2) | M5 | `PRACTICE` | 90 phút | 2026-11-28 10:30–11:15 (45p); 2026-11-28 11:15–12:00 (45p) | M5-O1, M5-O2 | T8 (bắt buộc) |
| **T10**: Thiết lập Bộ kiểm thử chất lượng dữ liệu dbt Test | M5 | `REVIEW` | 90 phút | 2026-11-30 19:30–20:15 (45p); 2026-11-30 20:15–21:00 (45p) | M5-O3 | T9 (bắt buộc) |
| **T11**: Tích hợp và Điều phối dbt trong Airflow Pipeline | M6 | `PROJECT` | 90 phút | 2026-12-02 19:30–20:15 (45p); 2026-12-02 20:15–21:00 (45p) | M6-O1, M6-O2 | T10 (bắt buộc) |
| **T12**: Đóng gói, Đánh giá và Hoàn thiện Pipeline ELT Toàn diện | M6 | `REVIEW` | 90 phút | 2026-12-04 19:30–20:15 (45p); 2026-12-04 20:15–21:00 (45p) | M6-O3 | T11 (bắt buộc) |

#### Chi tiết nội dung M1 (2 tasks)

- **T1 — Tổng quan kiến trúc ELT và Mô hình hóa dữ liệu quan hệ (3NF vs Star Schema)** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu nguyên lý Modern Data Stack, so sánh luồng ETL truyền thống và ELT hiện đại; đối chiếu mô hình 3NF tầng OLTP với Star Schema (Fact/Dimension) cho phân tích dữ liệu.
  - *Mục tiêu học tập:* Phân tích được kiến trúc ELT hiện đại và phân biệt mô hình 3NF với Dimensional Modeling.
  - *Tiêu chí hoàn thành:* Vẽ được sơ đồ kiến trúc ELT và bảng so sánh chi tiết giữa 3NF và Dimensional Modeling.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-18 19:30–20:15 (45p); 2026-11-18 20:15–21:00 (45p)
- **T2 — Thiết lập môi trường PostgreSQL và thiết kế Schema dữ liệu mẫu** (`PRACTICE`, 90 phút)
  - *Mô tả:* Cấu hình Docker Compose chạy PostgreSQL, khởi tạo schema chuẩn 3NF đại diện cho nguồn dữ liệu giao dịch và kiểm tra kết nối.
  - *Mục tiêu học tập:* Khởi tạo môi trường phát triển Data Engineering tích hợp PostgreSQL thành công.
  - *Tiêu chí hoàn thành:* Docker container PostgreSQL hoạt động ổn định, nạp thành công schema nguồn 3NF.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:30–20:15 (45p); 2026-11-20 20:15–21:00 (45p)

#### Chi tiết nội dung M2 (2 tasks)

- **T3 — Lập trình DAG với Apache Airflow TaskFlow API** (`THEORY`, 90 phút)
  - *Mô tả:* Tìm hiểu kiến trúc Airflow 2.x, sử dụng decorators @dag và @task để định nghĩa luồng dữ liệu theo chuẩn Pythonic.
  - *Mục tiêu học tập:* Hiểu và áp dụng TaskFlow API để xây dựng DAGs mô-đun hóa.
  - *Tiêu chí hoàn thành:* Viết được mã nguồn DAG hoàn chỉnh sử dụng @dag và @task chạy không lỗi cú pháp.
  - *Concepts:* `py-oop-dataclasses`
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 09:00–09:45 (45p); 2026-11-21 09:45–10:30 (45p)
- **T4 — Quản lý XCom, Airflow Connections và Variables** (`PRACTICE`, 90 phút)
  - *Mô tả:* Thực hành truyền dữ liệu metadata an toàn qua XCom, cấu hình Connection kết nối PostgreSQL và biến cấu hình trong Airflow Web UI.
  - *Mục tiêu học tập:* Sử dụng XCom truyền metadata đúng chuẩn và quản trị Connection/Variables an toàn.
  - *Tiêu chí hoàn thành:* DAG trích xuất metadata và tương tác PostgreSQL Connection thành công trên Airflow UI.
  - *Concepts:* `py-oop-dataclasses`
  - *Tiên quyết:* T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 10:30–11:15 (45p); 2026-11-21 11:15–12:00 (45p)

#### Chi tiết nội dung M3 (2 tasks)

- **T5 — Thiết kế Pipeline Idempotent với Upsert và Execution Date** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu nguyên lý Idempotency trong data pipeline, áp dụng Upsert/Merge logic và phân vùng theo execution_date để chạy lại an toàn.
  - *Mục tiêu học tập:* Nắm vững nguyên lý và phương pháp bảo đảm tính lũy đẳng (Idempotency) khi backfill dữ liệu.
  - *Tiêu chí hoàn thành:* Tài liệu hóa cơ chế Upsert và xử lý tham số logical_date/execution_date.
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:30–20:15 (45p); 2026-11-23 20:15–21:00 (45p)
- **T6 — Cấu hình Retry, Alerts, Callback và Backfill thực chiến** (`PRACTICE`, 90 phút)
  - *Mô tả:* Cài đặt tham số retries, retry_delay, on_failure_callback và mô phỏng lỗi gián đoạn mạng để kiểm tra khả năng tự phục hồi và backfill.
  - *Mục tiêu học tập:* Cấu hình chính sách retry, cảnh báo SLA và thực hiện backfill 7 ngày an toàn.
  - *Tiêu chí hoàn thành:* Mô phỏng task lỗi kích hoạt callback thành công; lệnh backfill 7 ngày chạy hoàn tất không duplicate dữ liệu.
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:30–20:15 (45p); 2026-11-25 20:15–21:00 (45p)

#### Chi tiết nội dung M4 (2 tasks)

- **T7 — Khởi tạo dự án dbt Core và quản lý nguồn dữ liệu (Sources & Ref)** (`THEORY`, 90 phút)
  - *Mô tả:* Thiết lập dbt project, cấu hình profiles.yml kết nối PostgreSQL, khai báo sources.yml và tạo các staging models chuẩn hóa.
  - *Mục tiêu học tập:* Nắm vững cấu trúc dbt project và cơ chế quan hệ giữa source và ref.
  - *Tiêu chí hoàn thành:* dbt debug pass 100%, biên dịch thành công source và staging models bằng hàm ref().
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-27 19:30–20:15 (45p); 2026-11-27 20:15–21:00 (45p)
- **T8 — Xây dựng Tầng Phân tích Marts với Star Schema trên dbt** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết SQL transformations tạo Dimension tables và Fact tables phục vụ báo cáo kinh doanh từ dữ liệu staging.
  - *Mục tiêu học tập:* Tạo các model marts hoàn chỉnh theo cấu trúc Star Schema (Fact/Dimension).
  - *Tiêu chí hoàn thành:* Lệnh `dbt run` thực thi trơn tru và sinh ra sơ đồ lineage DAG chính xác trên dbt docs.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 09:00–09:45 (45p); 2026-11-28 09:45–10:30 (45p)

#### Chi tiết nội dung M5 (2 tasks)

- **T9 — Cài đặt dbt Incremental Models và Snapshots (SCD Type 2)** (`PRACTICE`, 90 phút)
  - *Mô tả:* Áp dụng macro is_incremental() với chiến lược merge trên Fact table; xây dựng snapshot để lưu giữ lịch sử thay đổi thông tin khách hàng (SCD Type 2).
  - *Mục tiêu học tập:* Thực hiện xử lý cập nhật gia tăng và theo dõi lịch sử thay đổi kích thước bằng dbt snapshots.
  - *Tiêu chí hoàn thành:* Snapshot ghi nhận đúng dbt_valid_from/to; incremental model chỉ nạp các bản ghi mới.
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 10:30–11:15 (45p); 2026-11-28 11:15–12:00 (45p)
- **T10 — Thiết lập Bộ kiểm thử chất lượng dữ liệu dbt Test** (`REVIEW`, 90 phút)
  - *Mô tả:* Định nghĩa các Generic Tests (unique, not_null, accepted_values, relationships) và Singular SQL Tests phát hiện dị biệt dữ liệu.
  - *Mục tiêu học tập:* Kiểm thử tự động tính toàn vẹn và chất lượng dữ liệu cho toàn bộ models.
  - *Tiêu chí hoàn thành:* Lệnh `dbt test` đạt kết quả pass 100% trên toàn bộ các bảng staging và marts.
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-30 19:30–20:15 (45p); 2026-11-30 20:15–21:00 (45p)

#### Chi tiết nội dung M6 (2 tasks)

- **T11 — Tích hợp và Điều phối dbt trong Airflow Pipeline** (`PROJECT`, 90 phút)
  - *Mô tả:* Điều phối dbt execution trong Airflow sử dụng Cosmos hoặc BashOperator, thiết lập chốt chặn Data Quality Gates dừng pipeline nếu test lỗi.
  - *Mục tiêu học tập:* Tự động hóa toàn bộ quy trình ELT kết hợp Airflow và dbt với chốt chặn an toàn dữ liệu.
  - *Tiêu chí hoàn thành:* Pipeline tự động ngắt khi dbt test fail và gửi notification cảnh báo; hoàn tất quy trình khi test pass.
  - *Concepts:* `py-oop-dataclasses`
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-12-02 19:30–20:15 (45p); 2026-12-02 20:15–21:00 (45p)
- **T12 — Đóng gói, Đánh giá và Hoàn thiện Pipeline ELT Toàn diện** (`REVIEW`, 90 phút)
  - *Mô tả:* Đóng gói toàn bộ hạ tầng Airflow, PostgreSQL và dbt thành repository hoàn chỉnh, xây dựng tài liệu vận hành và kiểm tra luồng end-to-end.
  - *Mục tiêu học tập:* Hoàn thiện tài liệu kiến trúc, đóng gói mã nguồn và kiểm thử toàn diện pipeline ELT.
  - *Tiêu chí hoàn thành:* Pipeline chạy end-to-end từ ingest đến mart thành công trong một lệnh điều phối duy nhất.
  - *Concepts:* `py-oop-dataclasses`
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-12-04 19:30–20:15 (45p); 2026-12-04 20:15–21:00 (45p)

---

## R-04 — Rust Async Programming & Tokio Runtime chuyên sâu

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Làm chủ Future trait, Pin/Unpin, Waker, Tokio work-stealing scheduler, channels, backpressure, graceful shutdown và tối ưu lock-free concurrency cho network service hiệu năng cao trong 6 tuần.
- **Khung thời gian:** `2026-11-17` → `2026-12-29`
- **Thời lượng phiên học tối ưu:** 90 phút
- **Quỹ thời gian rảnh:** MODE_A — Thứ 2–Thứ 6: 90 phút/ngày; Thứ 7 & CN: 150 phút/ngày
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE trong 6 tuần bao phủ toàn diện từ nền tảng ngôn ngữ (Future, Pin, Waker, State Machine), kiến trúc Tokio Runtime nội bộ (work-stealing, IO reactor), cơ chế đồng bộ (channels, backpressure, cancellation safety, graceful shutdown) đến tối ưu hóa cao cấp với Atomics/Lock-free và xây dựng Network Service thực chiến.
- **Tổng quan cấu trúc:** 6 milestones | 33 tasks (PRACTICE: 13, PROJECT: 5, REVIEW: 6, THEORY: 9) | 34 dependencies | Tổng thời lượng: 3090 phút (51.5 giờ) | Đã xếp lịch: 33/33 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Bản chất Async Rust: Future Trait, State Machine và Cơ chế Pin/Unpin (450 phút)
- **Mô tả:** Hiểu sâu mô hình thực thi lười (pull-based) của Rust, cách compiler sinh state machine từ async/await và bảo đảm an toàn bộ nhớ qua Pinning.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Phân tích cơ chế biến đổi cú pháp async/await thành State Machine cấu trúc enum trong quá trình biên dịch
  - `M1-O2`: M1-O2: Giải thích bản chất trait Future, phương thức poll, và trạng thái Poll::Ready / Poll::Pending
  - `M1-O3`: M1-O3: Ứng dụng Pin<P<T>> và trait Unpin để xử lý self-referential struct một cách an toàn mà không bị Move
- **Tiêu chí hoàn thành Milestone:** Viết tay struct tự tham chiếu (self-referential) cài đặt Future trait thủ công bằng Pin và Unpin, vượt qua bài kiểm tra bộ nhớ không dùng cú pháp async/await mặc định.
- **Khái niệm mở rộng (chưa có trong KB):** `rust-future-trait`, `rust-pin-unpin`, `self-referential-structs`, `async-state-machine`

#### M2. Cơ chế Waker, RawWaker và Xây dựng Minimal Single-threaded Executor (480 phút)
- **Mô tả:** Nắm vững cơ chế thông báo đánh thức task qua Waker vtable và hiện thực hóa một executor tối giản từ con trỏ thô.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Xây dựng RawWaker và RawWakerVTable thủ công để hiểu vòng đời đánh thức luồng thực thi
  - `M2-O2`: M2-O2: Tích hợp ArcWake / std::task::Waker vào hàng đợi thực thi (Task Queue)
  - `M2-O3`: M2-O3: Hiện thực một single-threaded executor hoàn chỉnh có khả năng block luồng khi nhàn rỗi và đánh thức khi có sự kiện
- **Tiêu chí hoàn thành Milestone:** Cài đặt hoàn chỉnh một minimal executor độc lập không phụ thuộc thư viện ngoài, có thể chạy và đánh thức lặp lại 3 tác vụ async giả lập I/O.
- **Khái niệm mở rộng (chưa có trong KB):** `rust-waker-contract`, `raw-waker-vtable`, `custom-async-executor`, `arc-wake-pattern`

#### M3. Kiến trúc Tokio Runtime: Work-Stealing Scheduler và I/O Reactor (540 phút)
- **Mô tả:** Khám phá tầng bên dưới của Tokio runtime: multi-threaded scheduler, cơ chế work-stealing, cooperative budget và tích hợp epoll/kqueue qua Mio.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Phân tích kiến trúc đa luồng work-stealing scheduler của Tokio (local queue vs global queue)
  - `M3-O2`: M3-O2: Làm rõ cơ chế Tokio Cooperative Scheduling nhằm ngăn chặn starvation tác vụ do vòng lặp tính toán nặng
  - `M3-O3`: M3-O3: Phân biệt rõ nhiệm vụ giữa tokio::spawn (compute/IO ngắn) và tokio::task::spawn_blocking (blocking task)
- **Tiêu chí hoàn thành Milestone:** Thiết lập môi trường benchmark so sánh độ trễ giữa spawn_blocking và tokio::spawn trên workload hỗn hợp CPU-bound và I/O-bound, kiểm chứng hiện tượng starvation qua tokio-console.
- **Khái niệm mở rộng (chưa có trong KB):** `tokio-work-stealing-scheduler`, `tokio-cooperative-budget`, `mio-reactor-integration`, `tokio-task-spawn-blocking`

#### M4. Async Concurrency, Channels và Kỹ thuật Điều phối Backpressure (540 phút)
- **Mô tả:** Làm chủ các kênh giao tiếp bất đồng bộ, xử lý dồn ứ dữ liệu (backpressure) và kết hợp đa luồng bằng select! / join! an toàn.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Phân biệt các loại kênh trong Tokio: mpsc (bounded vs unbounded), oneshot, broadcast, watch và ngữ cảnh sử dụng
  - `M4-O2`: M4-O2: Thiết kế pipeline xử lý dữ liệu với cơ chế bounded channels để bảo vệ bộ nhớ khỏi áp lực tràn tải (backpressure)
  - `M4-O3`: M4-O3: Sử dụng macro tokio::select! đúng cách, nhận diện các cạm bẫy hủy ngang task (cancellation hazard) và drop branch
- **Tiêu chí hoàn thành Milestone:** Xây dựng hệ thống pipeline xử lý luồng sự kiện đa producer/consumer sử dụng bounded mpsc channel và select!, chứng minh cơ chế backpressure chặn producer khi buffer đạt ngưỡng giới hạn mà không làm rò rỉ RAM.
- **Khái niệm mở rộng (chưa có trong KB):** `tokio-channels-mpsc-broadcast`, `backpressure-handling`, `tokio-select-macro`, `cancellation-safety`

#### M5. Graceful Shutdown, Cancellation Safety và Quản lý Tài nguyên (480 phút)
- **Mô tả:** Thiết kế hệ thống chịu lỗi với khả năng dừng mềm (graceful shutdown), an toàn khi hủy tác vụ (cancellation token) và dọn dẹp kết nối mạng.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M5-O1`: M5-O1: Tích hợp tokio_util::sync::CancellationToken để truyền tín hiệu dừng xuyên suốt cây tác vụ
  - `M5-O2`: M5-O2: Phân tích và sửa chữa lỗi Cancellation Safety trong các hàm async khi Future bị drop giữa chừng
  - `M5-O3`: M5-O3: Áp dụng idiom RAII guard và Drop trait để dọn dẹp tài nguyên socket/kết nối cơ sở dữ liệu khi nhận tín hiệu SIGINT/SIGTERM
- **Tiêu chí hoàn thành Milestone:** Viết bộ kiểm thử kiểm chứng server xử lý xong toàn bộ các request đang dở dang (in-flight requests) trong vòng 5 giây trước khi tắt hẳn sau khi kích hoạt CancellationToken, không làm đứt gãy kết nối client đột ngột.
- **Khái niệm mở rộng (chưa có trong KB):** `tokio-cancellation-token`, `graceful-shutdown-patterns`, `raii-async-cleanup`, `posix-signals-tokio`

#### M6. Lock-free Concurrency, Atomics và Dự án Network Service Hiệu năng cao (600 phút)
- **Mô tả:** Tối ưu hóa throughput cho dịch vụ mạng bằng cấu trúc dữ liệu lock-free, Rust Atomics (std::sync::atomic) và công cụ profiling chuyên sâu.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M6-O1`: M6-O1: Ứng dụng Memory Ordering (Relaxed, Acquire, Release, SeqCst) và các kiểu Atomics vào bộ đếm metric / cờ đồng bộ không khóa
  - `M6-O2`: M6-O2: Tích hợp lock-free queue / concurrent cache vào dịch vụ mạng nhằm giảm thiểu contention giữa các worker thread
  - `M6-O3`: M6-O3: Hoàn thiện Network Service đa luồng hiệu năng cao bằng Tokio TCP Stream, kết hợp đo lường hiệu năng bằng tokio-console và flamegraph
- **Tiêu chí hoàn thành Milestone:** Triển khai dự án TCP Network Service đạt thông lượng tối thiểu 50,000 QPS trên môi trường thử nghiệm với zero lock-contention cảnh báo từ công cụ profiling, có đầy đủ cơ chế graceful shutdown và backpressure.
- **Khái niệm mở rộng (chưa có trong KB):** `rust-atomic-memory-ordering`, `lock-free-data-structures`, `tokio-tcp-network-service`, `profiling-tokio-console`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Lý thuyết State Machine và Future Trait trong Async Rust | M1 | `THEORY` | 90 phút | 2026-11-17 19:00–20:30 (90p) | M1-O1, M1-O2 | Không |
| **T2**: Cơ chế Pin, Unpin và Vấn đề Self-Referential Structs | M1 | `THEORY` | 90 phút | 2026-11-18 19:00–20:30 (90p) | M1-O3 | T1 (bắt buộc) |
| **T3**: Thực hành triển khai Self-Referential Struct và Custom Future | M1 | `PRACTICE` | 90 phút | 2026-11-19 19:00–20:30 (90p) | M1-O2, M1-O3 | T2 (bắt buộc) |
| **T4**: Thực hành mô phỏng State Machine khử đường cú pháp async | M1 | `PRACTICE` | 90 phút | 2026-11-20 19:00–20:30 (90p) | M1-O1 | T1 (bắt buộc) |
| **T5**: Ôn tập và Đánh giá Bản chất Async Rust & Pinning | M1 | `REVIEW` | 90 phút | 2026-11-21 19:00–20:30 (90p) | M1-O1, M1-O2, M1-O3 | T3 (bắt buộc), T4 (bắt buộc) |
| **T6**: Lý thuyết Hợp đồng Waker, RawWaker và RawWakerVTable | M2 | `THEORY` | 90 phút | 2026-11-22 19:00–20:30 (90p) | M2-O1 | T5 (bắt buộc) |
| **T7**: Thực hành cài đặt RawWakerVTable và ArcWake | M2 | `PRACTICE` | 90 phút | 2026-11-23 19:00–20:30 (90p) | M2-O1, M2-O2 | T6 (bắt buộc) |
| **T8**: Thực hành xây dựng Event Loop và Task Queue cho Minimal Executor | M2 | `PRACTICE` | 90 phút | 2026-11-24 19:00–20:30 (90p) | M2-O2, M2-O3 | T7 (bắt buộc) |
| **T9**: Dự án nhỏ: Hoàn thiện Minimal Single-threaded Executor Độc lập | M2 | `PROJECT` | 120 phút | 2026-11-25 19:00–20:00 (60p); 2026-11-26 19:00–20:00 (60p) | M2-O3 | T8 (bắt buộc) |
| **T10**: Ôn tập và Rà soát Cơ chế Đánh thức Luồng (Waker Contract) | M2 | `REVIEW` | 90 phút | 2026-11-27 19:00–20:30 (90p) | M2-O1, M2-O2, M2-O3 | T9 (bắt buộc) |
| **T11**: Lý thuyết Kiến trúc Work-Stealing Scheduler và Tokio Runtime | M3 | `THEORY` | 90 phút | 2026-11-28 19:00–20:30 (90p) | M3-O1 | T10 (bắt buộc) |
| **T12**: Lý thuyết Cơ chế Tokio Cooperative Scheduling và Ngân sách Tác vụ | M3 | `THEORY` | 90 phút | 2026-11-29 19:00–20:30 (90p) | M3-O2 | T11 (bắt buộc) |
| **T13**: Thực hành Phân tách Tokio::spawn và Spawn_blocking | M3 | `PRACTICE` | 90 phút | 2026-11-30 19:00–20:30 (90p) | M3-O3 | T12 (bắt buộc) |
| **T14**: Thực hành Quan sát và Giám sát Runtime với Tokio-Console | M3 | `PRACTICE` | 90 phút | 2026-12-01 19:00–20:30 (90p) | M3-O1, M3-O2 | T13 (bắt buộc) |
| **T15**: Dự án nhỏ: Benchmark Điều phối Workload Hỗn hợp trên Tokio | M3 | `PROJECT` | 90 phút | 2026-12-02 19:00–20:30 (90p) | M3-O2, M3-O3 | T14 (bắt buộc) |
| **T16**: Ôn tập và Tổng kết Kiến trúc Tokio Runtime | M3 | `REVIEW` | 90 phút | 2026-12-03 19:00–20:30 (90p) | M3-O1, M3-O2, M3-O3 | T15 (bắt buộc) |
| **T17**: Lý thuyết Các Loại Kênh Truyền Thông trong Tokio | M4 | `THEORY` | 90 phút | 2026-12-04 19:00–20:30 (90p) | M4-O1 | T16 (bắt buộc) |
| **T18**: Lý thuyết Macro Tokio::select! và Cạm bẫy Cancellation Hazard | M4 | `THEORY` | 90 phút | 2026-12-05 19:00–20:30 (90p) | M4-O3 | T17 (bắt buộc) |
| **T19**: Thực hành Thiết kế Bounded Channel và Xử lý Backpressure | M4 | `PRACTICE` | 90 phút | 2026-12-06 19:00–20:30 (90p) | M4-O1, M4-O2 | T17 (bắt buộc) |
| **T20**: Thực hành Đa kênh với Tokio::select! và Biased Flag | M4 | `PRACTICE` | 90 phút | 2026-12-07 19:00–20:30 (90p) | M4-O3 | T18 (bắt buộc) |
| **T21**: Dự án nhỏ: Xây dựng Event-Driven Processing Pipeline | M4 | `PROJECT` | 90 phút | 2026-12-08 19:00–20:30 (90p) | M4-O1, M4-O2, M4-O3 | T19 (bắt buộc), T20 (bắt buộc) |
| **T22**: Ôn tập và Kiểm thử Stress Testing Kênh Giao tiếp | M4 | `REVIEW` | 90 phút | 2026-12-09 19:00–20:30 (90p) | M4-O1, M4-O2, M4-O3 | T21 (bắt buộc) |
| **T23**: Lý thuyết CancellationToken và Cơ chế Phát Tín hiệu Dừng | M5 | `THEORY` | 90 phút | 2026-12-10 19:00–20:30 (90p) | M5-O1 | T22 (bắt buộc) |
| **T24**: Lý thuyết và Thực hành Phân tích Cancellation Safety Chuyên sâu | M5 | `PRACTICE` | 90 phút | 2026-12-11 19:00–20:30 (90p) | M5-O2, M5-O3 | T23 (bắt buộc) |
| **T25**: Thực hành Quản lý Tài nguyên với Drop Guard và Tracker Dở dang | M5 | `PRACTICE` | 90 phút | 2026-12-12 19:00–20:30 (90p) | M5-O1, M5-O3 | T24 (bắt buộc) |
| **T26**: Dự án nhỏ: Xây dựng Server Graceful Shutdown Hoàn chỉnh | M5 | `PROJECT` | 120 phút | 2026-12-12 20:30–21:30 (60p); 2026-12-13 19:00–20:00 (60p) | M5-O1, M5-O2, M5-O3 | T25 (bắt buộc) |
| **T27**: Ôn tập và Đánh giá Rủi ro Đứt gãy Dữ liệu khi Tắt Hệ thống | M5 | `REVIEW` | 90 phút | 2026-12-13 20:00–21:30 (90p) | M5-O1, M5-O2, M5-O3 | T26 (bắt buộc) |
| **T28**: Lý thuyết Memory Ordering và Kiểu Dữ liệu Atomics trong Rust | M6 | `THEORY` | 90 phút | 2026-12-14 19:00–20:30 (90p) | M6-O1 | T27 (bắt buộc) |
| **T29**: Thực hành Cài đặt Cấu trúc Dữ liệu Lock-free (Concurrent Queue/Counter) | M6 | `PRACTICE` | 90 phút | 2026-12-15 19:00–20:30 (90p) | M6-O1, M6-O2 | T28 (bắt buộc) |
| **T30**: Thực hành Xây dựng Core Network Engine với Tokio TCP Stream | M6 | `PRACTICE` | 90 phút | 2026-12-16 19:00–20:30 (90p) | M6-O2, M6-O3 | T29 (bắt buộc) |
| **T31**: Dự án Tổng hợp: Triển khai High-Performance Network Service Hoàn chỉnh | M6 | `PROJECT` | 120 phút | 2026-12-17 19:00–20:00 (60p); 2026-12-18 19:00–20:00 (60p) | M6-O1, M6-O2, M6-O3 | T30 (bắt buộc) |
| **T32**: Thực hành Đo lường Hiệu năng với Flamegraph và Tối ưu Contention | M6 | `PRACTICE` | 120 phút | 2026-12-19 19:00–20:00 (60p); 2026-12-19 20:00–21:00 (60p) | M6-O2, M6-O3 | T31 (bắt buộc) |
| **T33**: Ôn tập và Nghiệm thu Toàn diện Lộ trình Async Rust | M6 | `REVIEW` | 90 phút | 2026-12-20 19:00–20:30 (90p) | M6-O1, M6-O2, M6-O3 | T32 (bắt buộc) |

#### Chi tiết nội dung M1 (5 tasks)

- **T1 — Lý thuyết State Machine và Future Trait trong Async Rust** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu kiến trúc biến đổi từ cú pháp async/await sang State Machine enum do trình biên dịch rustc sinh ra, cùng cấu trúc và vòng đời của trait Future.
  - *Mục tiêu học tập:* Hiểu rõ cơ chế compiler hạ cấp async block thành state machine enum và hợp đồng gọi hàm poll với Context/Waker.
  - *Tiêu chí hoàn thành:* Vẽ được sơ đồ các trạng thái chuyển giao của một async block gồm 2 điểm await và giải thích ý nghĩa Poll::Ready/Pending.
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:00–20:30 (90p)
- **T2 — Cơ chế Pin, Unpin và Vấn đề Self-Referential Structs** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu nguyên lý an toàn bộ nhớ của Pin<P<T>>, auto trait Unpin, và lý do cấu trúc tự tham chiếu gây Undefined Behavior khi bị Move.
  - *Mục tiêu học tập:* Nắm vững lý do toán học và an toàn bộ nhớ của Pin, cách con trỏ tự tham chiếu bị vô hiệu hóa nếu struct bị di chuyển trên stack.
  - *Tiêu chí hoàn thành:* Viết tài liệu phân tích chứng minh vì sao việc Move struct chứa self-reference tạo ra con trỏ treo (dangling pointer) nếu thiếu Pin.
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-18 19:00–20:30 (90p)
- **T3 — Thực hành triển khai Self-Referential Struct và Custom Future** (`PRACTICE`, 90 phút)
  - *Mô tả:* Hiện thực thủ công một struct tự tham chiếu an toàn bằng Pin::new_unchecked và cài đặt Future trait mà không sử dụng async/await.
  - *Mục tiêu học tập:* Áp dụng Pin và Unpin để cài đặt thủ công hàm poll cho struct tự tham chiếu an toàn bộ nhớ.
  - *Tiêu chí hoàn thành:* Biên dịch thành công struct tự tham chiếu cài Future::poll và chạy kiểm thử bộ nhớ không phát sinh lỗi với Miri.
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 19:00–20:30 (90p)
- **T4 — Thực hành mô phỏng State Machine khử đường cú pháp async** (`PRACTICE`, 90 phút)
  - *Mô tả:* Xây dựng enum State Machine thủ công mô phỏng chính xác mã sinh bởi async/await cho một chuỗi tác vụ async tuần tự.
  - *Mục tiêu học tập:* Tự tay viết enum đại diện cho các bước thực thi async, lưu trữ context giữa các lần poll.
  - *Tiêu chí hoàn thành:* Mã nguồn State Machine thủ công vượt qua toàn bộ unit test mô phỏng kịch bản pending và resume đúng trình tự.
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:00–20:30 (90p)
- **T5 — Ôn tập và Đánh giá Bản chất Async Rust & Pinning** (`REVIEW`, 90 phút)
  - *Mô tả:* Tổng kết kiến thức về Pin/Unpin, rà soát lại các bất biến an toàn (safety invariants) và kiểm thử các corner cases của Future.
  - *Mục tiêu học tập:* Củng cố kiến thức nền tảng về hệ thống kiểu và quản lý bộ nhớ của Rust trong ngữ cảnh lập trình bất đồng bộ.
  - *Tiêu chí hoàn thành:* Hoàn thành bài kiểm tra phân tích lỗi Pinning và giải quyết 3 tình huống lỗi biên dịch phổ biến liên quan đến Unpin trait.
  - *Tiên quyết:* T3 (bắt buộc), T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 19:00–20:30 (90p)

#### Chi tiết nội dung M2 (5 tasks)

- **T6 — Lý thuyết Hợp đồng Waker, RawWaker và RawWakerVTable** (`THEORY`, 90 phút)
  - *Mô tả:* Phân tích đặc tả kỹ thuật của RawWaker, RawWakerVTable và cách Context truyền waker vào hàm poll để kích hoạt đánh thức luồng.
  - *Mục tiêu học tập:* Nắm vững cơ chế đánh thức luồng thực thi cấp thấp không cần cấp phát động hoặc dùng ArcWake.
  - *Tiêu chí hoàn thành:* Giải thích chi tiết 4 con trỏ hàm trong RawWakerVTable (clone, wake, wake_by_ref, drop) và vòng đời của RawWaker.
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-22 19:00–20:30 (90p)
- **T7 — Thực hành cài đặt RawWakerVTable và ArcWake** (`PRACTICE`, 90 phút)
  - *Mô tả:* Hiện thực thủ công RawWakerVTable an toàn và tích hợp pattern ArcWake để đưa tác vụ vào hàng đợi Task Queue.
  - *Mục tiêu học tập:* Xây dựng waker tùy biến liên kết trực tiếp với hàng đợi tác vụ thông qua con trỏ Arc.
  - *Tiêu chí hoàn thành:* Viết thành công struct Task đóng gói Future và ArcWake đưa được reference task vào crossbeam/mpsc queue khi wake() được gọi.
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:00–20:30 (90p)
- **T8 — Thực hành xây dựng Event Loop và Task Queue cho Minimal Executor** (`PRACTICE`, 90 phút)
  - *Mô tả:* Thiết lập cấu trúc Single-threaded Executor với vòng lặp xử lý tác vụ, hỗ trợ cơ chế park/unpark luồng khi hàng đợi rỗng.
  - *Mục tiêu học tập:* Tạo vòng lặp điều phối chính có khả năng block hệ điều hành khi nhàn rỗi và phản hồi tức thì khi waker gửi tín hiệu.
  - *Tiêu chí hoàn thành:* Executor xử lý chính xác chuỗi tác vụ đồng thời, đưa CPU về trạng thái nghỉ khi không có tác vụ nào sẵn sàng.
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-24 19:00–20:30 (90p)
- **T9 — Dự án nhỏ: Hoàn thiện Minimal Single-threaded Executor Độc lập** (`PROJECT`, 120 phút)
  - *Mô tả:* Tích hợp Spawner, Task Queue, Timer/IO giả lập vào Executor và thực thi 3 tác vụ async độc lập không dùng thư viện runtime ngoài.
  - *Mục tiêu học tập:* Đóng gói hoàn chỉnh một runtime async tối giản có khả năng lên lịch và điều phối tác vụ async hoàn toàn độc lập.
  - *Tiêu chí hoàn thành:* Chương trình chạy và hoàn tất 3 tác vụ async giả lập I/O timer theo đúng thứ tự đánh thức, không rò rỉ bộ nhớ.
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:00–20:00 (60p); 2026-11-26 19:00–20:00 (60p)
- **T10 — Ôn tập và Rà soát Cơ chế Đánh thức Luồng (Waker Contract)** (`REVIEW`, 90 phút)
  - *Mô tả:* Đánh giá lại toàn bộ luồng thực thi từ poll -> pending -> wake -> reschedule và kiểm tra tuân thủ Waker contract.
  - *Mục tiêu học tập:* Nhận diện các lỗi thất thoát waker (lost wakeup) và cạm bẫy vòng lặp vô tận (busy spin) trong custom executor.
  - *Tiêu chí hoàn thành:* Vượt qua checklist đánh giá độ trễ và khả năng giải phóng tài nguyên của minimal executor qua bài test stress lặp lại 1,000 lần.
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-27 19:00–20:30 (90p)

#### Chi tiết nội dung M3 (6 tasks)

- **T11 — Lý thuyết Kiến trúc Work-Stealing Scheduler và Tokio Runtime** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu kiến trúc đa luồng của Tokio: Local run queue, Global injector queue, và thuật toán work-stealing giữa các worker thread.
  - *Mục tiêu học tập:* Hiểu cấu trúc luồng của Tokio multi-thread runtime và cơ chế cân bằng tải tự động giữa các CPU core.
  - *Tiêu chí hoàn thành:* Mô tả được lưu đồ phân phối tác vụ từ lúc spawn đến khi worker thread trộm tác vụ từ hàng đợi cục bộ của worker khác.
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 19:00–20:30 (90p)
- **T12 — Lý thuyết Cơ chế Tokio Cooperative Scheduling và Ngân sách Tác vụ** (`THEORY`, 90 phút)
  - *Mô tả:* Khảo sát cơ chế budget (coop budget) của Tokio giúp ngăn chặn tình trạng một Future chiếm giữ luồng quá lâu gây bỏ đói (starvation).
  - *Mục tiêu học tập:* Làm rõ cách Tokio tự động yield tác vụ khi vượt quá hạn mức budget trong các vòng lặp xử lý socket/channel.
  - *Tiêu chí hoàn thành:* Chỉ ra cơ chế đếm ngân sách trong tokio::task::consume_budget và giải thích cách tokio::task::yield_now hoạt động.
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-11-29 19:00–20:30 (90p)
- **T13 — Thực hành Phân tách Tokio::spawn và Spawn_blocking** (`PRACTICE`, 90 phút)
  - *Mô tả:* Xây dựng ứng dụng xử lý hỗn hợp tác vụ tính toán hashing CPU-bound và socket I/O, đo lường tác động khi chạy sai ngữ cảnh.
  - *Mục tiêu học tập:* Áp dụng đúng đắn spawn_blocking cho các tác vụ đồng bộ nặng để bảo vệ pool worker thread của runtime.
  - *Tiêu chí hoàn thành:* Chứng minh sự khác biệt thông lượng I/O khi chuyển đổi tính toán nặng từ worker thread sang spawn_blocking threadpool.
  - *Tiên quyết:* T12 (bắt buộc) | *Lịch dự kiến:* 2026-11-30 19:00–20:30 (90p)
- **T14 — Thực hành Quan sát và Giám sát Runtime với Tokio-Console** (`PRACTICE`, 90 phút)
  - *Mô tả:* Tích hợp console-subscriber vào ứng dụng Tokio để theo dõi trạng thái tác vụ, thời gian poll, và phát hiện task starvation.
  - *Mục tiêu học tập:* Sử dụng công cụ tokio-console để quan sát trực quan metrics của task, queue depth và hiện tượng nghẽn luồng.
  - *Tiêu chí hoàn thành:* Kết nối thành công tokio-console tới ứng dụng và ghi nhận cảnh báo khi cố tình chèn vòng lặp tính toán không yield.
  - *Tiên quyết:* T13 (bắt buộc) | *Lịch dự kiến:* 2026-12-01 19:00–20:30 (90p)
- **T15 — Dự án nhỏ: Benchmark Điều phối Workload Hỗn hợp trên Tokio** (`PROJECT`, 90 phút)
  - *Mô tả:* Xây dựng bộ benchmark so sánh độ trễ p99 và throughput của hệ thống dưới tải CPU-bound kết hợp hàng nghìn kết nối I/O.
  - *Mục tiêu học tập:* Tối ưu hóa cấu hình Tokio runtime (worker_threads, max_blocking_threads) cho kịch bản tải thực tế.
  - *Tiêu chí hoàn thành:* Báo cáo benchmark kèm biểu đồ chỉ ra độ trễ p99 cải thiện rõ rệt khi cô lập blocking calls qua spawn_blocking.
  - *Tiên quyết:* T14 (bắt buộc) | *Lịch dự kiến:* 2026-12-02 19:00–20:30 (90p)
- **T16 — Ôn tập và Tổng kết Kiến trúc Tokio Runtime** (`REVIEW`, 90 phút)
  - *Mô tả:* Đánh giá lại toàn bộ cơ chế lập lịch, tương tác giữa I/O Reactor (mio) và Executor, củng cố quy tắc bất di bất dịch trong async.
  - *Mục tiêu học tập:* Khắc sâu nguyên tắc 'never block the async worker thread' và các phương pháp profiling runtime chuyên sâu.
  - *Tiêu chí hoàn thành:* Hoàn thành tài liệu tổng kết các quy tắc vàng khi viết ứng dụng production trên Tokio đa luồng.
  - *Tiên quyết:* T15 (bắt buộc) | *Lịch dự kiến:* 2026-12-03 19:00–20:30 (90p)

#### Chi tiết nội dung M4 (6 tasks)

- **T17 — Lý thuyết Các Loại Kênh Truyền Thông trong Tokio** (`THEORY`, 90 phút)
  - *Mô tả:* Phân tích đặc tính, cấu trúc dữ liệu và trường hợp sử dụng của mpsc (bounded/unbounded), oneshot, broadcast và watch channel.
  - *Mục tiêu học tập:* Phân biệt chính xác ưu nhược điểm của từng loại channel để lựa chọn phù hợp cho mô hình giao tiếp liên task.
  - *Tiêu chí hoàn thành:* Lập ma trận so sánh chi tiết giữa 4 loại kênh về hiệu năng, kích thước buffer, và khả năng hỗ trợ multi-producer/consumer.
  - *Tiên quyết:* T16 (bắt buộc) | *Lịch dự kiến:* 2026-12-04 19:00–20:30 (90p)
- **T18 — Lý thuyết Macro Tokio::select! và Cạm bẫy Cancellation Hazard** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu nguyên lý hoạt động của macro tokio::select!, hiện tượng Future bị drop khi một nhánh khác hoàn thành và cancellation safety.
  - *Mục tiêu học tập:* Nắm vững quy tắc kiểm tra tính Cancellation Safety của các Future khi đặt vào nhánh tokio::select!.
  - *Tiêu chí hoàn thành:* Chỉ ra 3 ví dụ Future không an toàn khi bị drop giữa chừng (như AsyncReadExt::read_exact) và cách khắc phục.
  - *Tiên quyết:* T17 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 19:00–20:30 (90p)
- **T19 — Thực hành Thiết kế Bounded Channel và Xử lý Backpressure** (`PRACTICE`, 90 phút)
  - *Mô tả:* Cài đặt mô hình Producer-Consumer sử dụng bounded mpsc channel, thiết lập giới hạn dung lượng để kiểm soát áp lực bộ nhớ.
  - *Mục tiêu học tập:* Làm chủ kỹ thuật điều tiết tốc độ sản sinh dữ liệu khi downstream consumer xử lý chậm bằng backpressure tự nhiên.
  - *Tiêu chí hoàn thành:* Viết test chứng minh producer tự động pending khi channel đầy và tiếp tục gửi khi consumer giải phóng buffer.
  - *Tiên quyết:* T17 (bắt buộc) | *Lịch dự kiến:* 2026-12-06 19:00–20:30 (90p)
- **T20 — Thực hành Đa kênh với Tokio::select! và Biased Flag** (`PRACTICE`, 90 phút)
  - *Mô tả:* Hiện thực luồng điều phối nhận dữ liệu đồng thời từ nhiều nguồn (timer, channel, stop signal) bằng tokio::select! và flag biased.
  - *Mục tiêu học tập:* Xây dựng vòng lặp event-driven xử lý nhiều nguồn tín hiệu cạnh tranh một cách công bằng hoặc ưu tiên có chủ đích.
  - *Tiêu chí hoàn thành:* Đoạn mã xử lý mượt mà sự kiện từ 3 channel khác nhau, đảm bảo nhánh ưu tiên không làm chết đói các nhánh còn lại.
  - *Tiên quyết:* T18 (bắt buộc) | *Lịch dự kiến:* 2026-12-07 19:00–20:30 (90p)
- **T21 — Dự án nhỏ: Xây dựng Event-Driven Processing Pipeline** (`PROJECT`, 90 phút)
  - *Mô tả:* Hiện thực pipeline xử lý stream dữ liệu đa tầng (Ingestion -> Transform -> Sink) tích hợp bounded channel, select! và broadcast metric.
  - *Mục tiêu học tập:* Kết hợp các loại channel và kỹ thuật backpressure vào một hệ thống xử lý dữ liệu thông lượng cao hoàn chỉnh.
  - *Tiêu chí hoàn thành:* Pipeline chạy ổn định dưới tải 100,000 sự kiện/giây, bộ nhớ RAM giữ nguyên mức cố định không phát sinh Out-Of-Memory.
  - *Tiên quyết:* T19 (bắt buộc), T20 (bắt buộc) | *Lịch dự kiến:* 2026-12-08 19:00–20:30 (90p)
- **T22 — Ôn tập và Kiểm thử Stress Testing Kênh Giao tiếp** (`REVIEW`, 90 phút)
  - *Mô tả:* Thực hiện review mã nguồn, phân tích rủi ro deadlock do vòng lặp channel và kiểm tra stress test giải phóng bộ nhớ.
  - *Mục tiêu học tập:* Nhận diện và phòng chống các lỗi deadlock khi sử dụng circular channel hoặc sender không được drop đúng cách.
  - *Tiêu chí hoàn thành:* Hoàn tất bộ unit test kiểm tra việc đóng kênh tự động khi all senders/receivers drop và không rò rỉ bất kỳ task nào.
  - *Tiên quyết:* T21 (bắt buộc) | *Lịch dự kiến:* 2026-12-09 19:00–20:30 (90p)

#### Chi tiết nội dung M5 (5 tasks)

- **T23 — Lý thuyết CancellationToken và Cơ chế Phát Tín hiệu Dừng** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu nguyên lý hoạt động của tokio_util::sync::CancellationToken, phân cấp token cha-con và xử lý tín hiệu OS (SIGINT/SIGTERM).
  - *Mục tiêu học tập:* Hiểu cách thức lan truyền tín hiệu dừng phi đồng bộ xuyên suốt cây tác vụ mà không làm gián đoạn luồng dữ liệu thô bạo.
  - *Tiêu chí hoàn thành:* Vẽ được sơ đồ lan truyền tín hiệu từ tokio::signal::ctrl_c() qua CancellationToken phân cấp tới các worker task.
  - *Tiên quyết:* T22 (bắt buộc) | *Lịch dự kiến:* 2026-12-10 19:00–20:30 (90p)
- **T24 — Lý thuyết và Thực hành Phân tích Cancellation Safety Chuyên sâu** (`PRACTICE`, 90 phút)
  - *Mô tả:* Phân tích các hàm async không an toàn khi hủy (cancellation-unsafe), tái cấu trúc sử dụng pattern buffer giữ trạng thái và RAII Drop guard.
  - *Mục tiêu học tập:* Nhận diện và sửa chữa triệt để lỗi mất dữ liệu khi Future bị drop giữa chừng trong tokio::select! hoặc timeout.
  - *Tiêu chí hoàn thành:* Chuyển đổi thành công một network reader không cancellation-safe thành một cấu trúc an toàn hoàn toàn không làm mất byte dữ liệu.
  - *Tiên quyết:* T23 (bắt buộc) | *Lịch dự kiến:* 2026-12-11 19:00–20:30 (90p)
- **T25 — Thực hành Quản lý Tài nguyên với Drop Guard và Tracker Dở dang** (`PRACTICE`, 90 phút)
  - *Mô tả:* Sử dụng tokio::sync::watch kết hợp RAII drop guard hoặc tokio_util::task::TaskTracker để theo dõi và hoàn tất in-flight requests.
  - *Mục tiêu học tập:* Áp dụng RAII guard để tự động giải phóng tài nguyên socket và chờ tất cả các request đang xử lý hoàn thành trước khi thoát.
  - *Tiêu chí hoàn thành:* Viết bộ quản lý request sử dụng TaskTracker đảm bảo hàm shutdown() chỉ return khi bộ đếm tác vụ dở dang về 0.
  - *Tiên quyết:* T24 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 19:00–20:30 (90p)
- **T26 — Dự án nhỏ: Xây dựng Server Graceful Shutdown Hoàn chỉnh** (`PROJECT`, 120 phút)
  - *Mô tả:* Tích hợp toàn bộ kỹ thuật Graceful Shutdown vào một TCP Echo/HTTP mock server, xử lý timeout dừng và dọn dẹp kết nối an toàn.
  - *Mục tiêu học tập:* Triển khai luồng dừng hoàn chỉnh có giới hạn thời gian (grace period timeout) và bảo toàn tính toàn vẹn dữ liệu khách hàng.
  - *Tiêu chí hoàn thành:* Hệ thống vượt qua bài kiểm tra gửi tín hiệu SIGINT khi đang có 500 kết nối: toàn bộ request dở dang phản hồi xong, server tắt êm ả.
  - *Tiên quyết:* T25 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 20:30–21:30 (60p); 2026-12-13 19:00–20:00 (60p)
- **T27 — Ôn tập và Đánh giá Rủi ro Đứt gãy Dữ liệu khi Tắt Hệ thống** (`REVIEW`, 90 phút)
  - *Mô tả:* Rà soát toàn diện các kịch bản crash, kill signal bất ngờ và đánh giá độ tin cậy của quy trình dọn dẹp tài nguyên RAII.
  - *Mục tiêu học tập:* Hệ thống hóa các pattern chuẩn công nghiệp về graceful shutdown cho các dịch vụ mạng phân tán bằng Rust.
  - *Tiêu chí hoàn thành:* Xây dựng checklist 8 bước kiểm tra độ an toàn shutdown cho mọi microservice async viết bằng Tokio.
  - *Tiên quyết:* T26 (bắt buộc) | *Lịch dự kiến:* 2026-12-13 20:00–21:30 (90p)

#### Chi tiết nội dung M6 (6 tasks)

- **T28 — Lý thuyết Memory Ordering và Kiểu Dữ liệu Atomics trong Rust** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu mô hình bộ nhớ phần cứng (hardware memory model), atomic primitives và các thứ tự bộ nhớ: Relaxed, Acquire, Release, SeqCst.
  - *Mục tiêu học tập:* Hiểu rõ cơ chế CPU reordering và cách thiết lập đồng bộ hóa không khóa an toàn qua cặp Acquire-Release.
  - *Tiêu chí hoàn thành:* Giải thích đúng đắn kịch bản race condition nếu dùng sai Relaxed thay cho Acquire-Release trong cờ thông báo trạng thái.
  - *Tiên quyết:* T27 (bắt buộc) | *Lịch dự kiến:* 2026-12-14 19:00–20:30 (90p)
- **T29 — Thực hành Cài đặt Cấu trúc Dữ liệu Lock-free (Concurrent Queue/Counter)** (`PRACTICE`, 90 phút)
  - *Mô tả:* Hiện thực bộ đếm metric hiệu năng cao và một lock-free ring buffer / queue đơn giản sử dụng AtomicPtr và AtomicUsize.
  - *Mục tiêu học tập:* Áp dụng các thao tác CAS (compare_exchange) và atomic ordering để loại bỏ hoàn toàn Mutex contention.
  - *Tiêu chí hoàn thành:* Cấu trúc lock-free vượt qua kiểm thử đa luồng với Loom / ThreadSanitizer không phát sinh data race hay memory leak.
  - *Tiên quyết:* T28 (bắt buộc) | *Lịch dự kiến:* 2026-12-15 19:00–20:30 (90p)
- **T30 — Thực hành Xây dựng Core Network Engine với Tokio TCP Stream** (`PRACTICE`, 90 phút)
  - *Mô tả:* Thiết lập server TCP bất đồng bộ tối ưu xử lý frame nhị phân, phân luồng read/write split và tích hợp ring buffer không khóa.
  - *Mục tiêu học tập:* Làm chủ việc điều phối I/O tầng thấp với Tokio AsyncRead/AsyncWrite và buffer pool không khóa để đạt throughput tối đa.
  - *Tiêu chí hoàn thành:* Server TCP thiết lập kết nối và phản hồi các gói tin nhị phân với độ trễ sub-millisecond dưới tải mô phỏng.
  - *Tiên quyết:* T29 (bắt buộc) | *Lịch dự kiến:* 2026-12-16 19:00–20:30 (90p)
- **T31 — Dự án Tổng hợp: Triển khai High-Performance Network Service Hoàn chỉnh** (`PROJECT`, 120 phút)
  - *Mô tả:* Tích hợp toàn bộ kiến thức vào Network Service: Lock-free metrics, TCP streams, backpressure bounded channels, CancellationToken và shutdown.
  - *Mục tiêu học tập:* Xây dựng dịch vụ mạng chuẩn production đạt hiệu năng vượt trội, an toàn bộ nhớ và chịu tải cực lớn.
  - *Tiêu chí hoàn thành:* Triển khai service hoàn chỉnh và thực hiện bài test tải đạt trên 50,000 QPS mà không bị crash hoặc nghẽn thread.
  - *Tiên quyết:* T30 (bắt buộc) | *Lịch dự kiến:* 2026-12-17 19:00–20:00 (60p); 2026-12-18 19:00–20:00 (60p)
- **T32 — Thực hành Đo lường Hiệu năng với Flamegraph và Tối ưu Contention** (`PRACTICE`, 120 phút)
  - *Mô tả:* Sử dụng cargo-flamegraph và tokio-console để profiling Network Service, loại bỏ các điểm nóng (hotspots) và lock contention.
  - *Mục tiêu học tập:* Thu thập và phân tích flamegraph để nhận diện các chi phí phụ (overhead) về phân bổ bộ nhớ heap hoặc tranh chấp CPU.
  - *Tiêu chí hoàn thành:* Xuất flamegraph phân tích trước và sau tối ưu, chứng minh giảm thiểu tối đa thời gian chờ đợi trên synchronization primitives.
  - *Tiên quyết:* T31 (bắt buộc) | *Lịch dự kiến:* 2026-12-19 19:00–20:00 (60p); 2026-12-19 20:00–21:00 (60p)
- **T33 — Ôn tập và Nghiệm thu Toàn diện Lộ trình Async Rust** (`REVIEW`, 90 phút)
  - *Mô tả:* Tổng kết toàn bộ kiến trúc từ Future, Waker, Tokio Scheduler, Backpressure tới Lock-free Atomics và đánh giá tiêu chí hoàn thành.
  - *Mục tiêu học tập:* Hệ thống hóa toàn diện năng lực lập trình async cấp độ chuyên gia trong hệ sinh thái Rust hiện đại.
  - *Tiêu chí hoàn thành:* Hoàn tất báo cáo kỹ thuật nghiệm thu dự án Network Service với đầy đủ số liệu benchmark 50k QPS và tài liệu kiến trúc.
  - *Tiên quyết:* T32 (bắt buộc) | *Lịch dự kiến:* 2026-12-20 19:00–20:30 (90p)

---

## R-05 — Rust Async Programming & Tokio Runtime chuyên sâu

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Làm chủ Future trait, Pin/Unpin, Waker, Tokio work-stealing scheduler, channels, backpressure, graceful shutdown và tối ưu lock-free concurrency cho network service hiệu năng cao trong 6 tuần.
- **Khung thời gian:** `2026-11-17` → `2026-12-29`
- **Thời lượng phiên học tối ưu:** 90 phút
- **Quỹ thời gian rảnh:** MODE_A — Thứ 2–Thứ 6: 90 phút/ngày; Thứ 7 & CN: 150 phút/ngày
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE toàn diện trong 6 tuần bao phủ toàn bộ các khía cạnh chuyên sâu của Rust Async và Tokio: từ bản chất Future trait/Pin/Waker, scheduler nội tại của Tokio, backpressure/channels, cancellation safety & graceful shutdown, cho đến lock-free concurrency và tối ưu hóa zero-copy cho network service hiệu năng cao.
- **Tổng quan cấu trúc:** 5 milestones | 23 tasks (PRACTICE: 7, PROJECT: 1, REVIEW: 5, THEORY: 10) | 25 dependencies | Tổng thời lượng: 2070 phút (34.5 giờ) | Đã xếp lịch: 23/23 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Bản chất Async Rust: Future Trait, Pinning và Cơ chế Waker (360 phút)
- **Mô tả:** Nghiên cứu sâu cơ chế thực thi bất đồng bộ tầng thấp trong Rust: cấu trúc Future trait, trạng thái Poll, cơ chế bộ nhớ tự tham chiếu (self-referential structs), quy tắc Pin/Unpin và cách thức Waker thông báo cho reactor/executor.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Tự triển khai thủ công một custom Future với hàm poll, quản lý trạng thái chuyển đổi và tái đăng ký Waker chính xác
  - `M1-O2`: M1-O2: Phân tích và xử lý an toàn cấu trúc self-referential sử dụng std::pin::Pin và hiểu rõ ngữ nghĩa an toàn của Unpin
- **Tiêu chí hoàn thành Milestone:** Viết và kiểm thử thành công một custom Future (chẳng hạn TimerFuture hoặc I/O readiness future) không dùng thư viện ngoài, đảm bảo không rò rỉ Waker và an toàn bộ nhớ tuyệt đối với Pin.
- **Khái niệm mở rộng (chưa có trong KB):** `rust-future-trait`, `rust-pin-unpin-semantics`, `rust-waker-context`

#### M2. Kiến trúc Tokio Runtime: Multi-threaded Work-Stealing Scheduler và I/O Reactor (360 phút)
- **Mô tả:** Giải phẫu kiến trúc bên trong của Tokio Runtime bao gồm Mio-based event loop (epoll/kqueue), cơ chế work-stealing deque, phân biệt task blocking vs non-blocking, và cấu hình tối ưu luồng thực thi.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Phân tích cơ chế work-stealing scheduler của Tokio và nguyên lý phân phối task giữa các worker threads
  - `M2-O2`: M2-O2: Phân tách an toàn các tác vụ CPU-bound/blocking I/O bằng spawn_blocking để chống suy thoái event loop
- **Tiêu chí hoàn thành Milestone:** Cấu hình Tokio runtime tùy chỉnh, đo lường độ trễ và thông lượng khi thực thi tải hỗn hợp (I/O non-blocking kết hợp CPU-intensive blocking task) mà không làm tắc nghẽn worker thread.
- **Khái niệm mở rộng (chưa có trong KB):** `tokio-work-stealing-scheduler`, `tokio-io-reactor-mio`, `tokio-spawn-blocking-isolation`

#### M3. Giao tiếp Concurrency: Tokio Channels, Backpressure và Stream Processing (450 phút)
- **Mô tả:** Làm chủ các loại kênh truyền thông mpsc, oneshot, broadcast, watch trong Tokio; thiết kế cơ chế backpressure chống tràn bộ nhớ và xử lý luồng dữ liệu liên tục với AsyncRead/AsyncWrite và Stream trait.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Thiết kế hệ thống producer-consumer có giới hạn dung lượng (bounded mpsc) xử lý backpressure triệt để
  - `M3-O2`: M3-O2: Xử lý streaming dữ liệu mạng nhị phân hiệu quả bằng tokio::io::{AsyncReadExt, AsyncWriteExt} và Framing pattern
- **Tiêu chí hoàn thành Milestone:** Triển khai một pipeline pipeline pipeline stream xử lý dữ liệu nhị phân với bounded channels, chứng minh hệ thống không bị OOM (Out Of Memory) khi producer đẩy dữ liệu nhanh gấp 10 lần consumer.
- **Khái niệm mở rộng (chưa có trong KB):** `tokio-channels-concurrency`, `tokio-backpressure-patterns`, `tokio-stream-framing`

#### M4. Vòng đời Network Service: Graceful Shutdown và Task Cancellation (360 phút)
- **Mô tả:** Xây dựng mô hình kiểm soát vòng đời hoàn chỉnh cho network server: lắng nghe tín hiệu OS (SIGINT/SIGTERM), hủy bỏ tác vụ (cancellation safety), quản lý CancellationToken và chờ đợi các kết nối đang dở dang hoàn tất.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Áp dụng tokio_util::sync::CancellationToken và drop guards để điều phối tắt ứng dụng an toàn
  - `M4-O2`: M4-O2: Đảm bảo cancellation safety cho các biểu thức tokio::select! và các tương tác stateful
- **Tiêu chí hoàn thành Milestone:** Xây dựng TCP server có khả năng đóng kết nối an toàn (dừng nhận kết nối mới, xử lý xong các request dở dang, xả buffer) trong vòng timeout xác định khi nhận SIGINT mà không làm drop dữ liệu client.
- **Khái niệm mở rộng (chưa có trong KB):** `tokio-graceful-shutdown`, `rust-cancellation-safety`, `tokio-cancellation-token`

#### M5. Tối ưu Hiệu năng Cao: Lock-Free Concurrency, Atomics và Zero-Copy Network Service (540 phút)
- **Mô tả:** Tối ưu hóa tầng sâu dịch vụ mạng: thay thế Mutex bằng cấu trúc dữ liệu Atomic và Lock-Free (crossbeam/parking_lot), tối ưu phân bổ bộ nhớ (bytes crate, zero-copy buffer pooling) và profiling với Tokio-console.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M5-O1`: M5-O1: Áp dụng Atomic primitives và Lock-free queue vào trạng thái chia sẻ (shared state) trong môi trường async đa luồng
  - `M5-O2`: M5-O2: Sử dụng Bytes crate và Tokio-console để loại bỏ cấp phát bộ nhớ thừa và chẩn đoán điểm nghẽn task contention
- **Tiêu chí hoàn thành Milestone:** Hoàn thiện một TCP Network Service hoàn chỉnh đạt chuẩn production, áp dụng zero-copy, lock-free state, graceful shutdown và profile bằng tokio-console chứng minh không có lock contention hay task starvation.
- **Khái niệm mở rộng (chưa có trong KB):** `rust-lock-free-atomics`, `rust-zero-copy-bytes`, `tokio-console-profiling`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Nghiên cứu nguyên lý Future Trait, Context và Waker trong Async Rust | M1 | `THEORY` | 90 phút | 2026-11-17 19:00–20:30 (90p) | M1-O1 | Không |
| **T2**: Nghiên cứu cơ chế Pinning, Pin và Unpin cho Self-referential Structs | M1 | `THEORY` | 90 phút | 2026-11-18 19:00–20:30 (90p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Thực hành triển khai Custom Future và Waker registration | M1 | `PRACTICE` | 90 phút | 2026-11-19 19:00–20:30 (90p) | M1-O1 | T1 (bắt buộc) |
| **T4**: Thực hành và Đánh giá Self-referential Struct an toàn với Pin projection | M1 | `REVIEW` | 90 phút | 2026-11-20 19:00–20:30 (90p) | M1-O2 | T2 (bắt buộc), T3 (bắt buộc) |
| **T5**: Kiến trúc Tokio Multi-threaded Runtime & Work-Stealing Algorithm | M2 | `THEORY` | 90 phút | 2026-11-21 19:00–20:30 (90p) | M2-O1 | T4 (bắt buộc) |
| **T6**: Cơ chế I/O Reactor Mio và Vấn đề Blocking trong Event Loop | M2 | `THEORY` | 90 phút | 2026-11-22 19:00–20:30 (90p) | M2-O2 | T5 (bắt buộc) |
| **T7**: Thực hành cấu hình Tokio Runtime và Tách biệt Blocking I/O | M2 | `PRACTICE` | 90 phút | 2026-11-23 19:00–20:30 (90p) | M2-O2 | T6 (bắt buộc) |
| **T8**: Đo lường Latency & Tránh Starvation trên Tokio Worker Threads | M2 | `REVIEW` | 90 phút | 2026-11-24 19:00–20:30 (90p) | M2-O1, M2-O2 | T7 (bắt buộc) |
| **T9**: Nguyên lý Tokio Channels & Chiến lược Kiểm soát Backpressure | M3 | `THEORY` | 90 phút | 2026-11-25 19:00–20:30 (90p) | M3-O1 | T8 (bắt buộc) |
| **T10**: Thiết kế Stream Processing và Framing Giao thức Nhị phân | M3 | `THEORY` | 90 phút | 2026-11-26 19:00–20:30 (90p) | M3-O2 | T9 (bắt buộc) |
| **T11**: Thực hành Xây dựng Producer-Consumer Pipeline có Giới hạn Tải | M3 | `PRACTICE` | 90 phút | 2026-11-27 19:00–20:30 (90p) | M3-O1 | T9 (bắt buộc) |
| **T12**: Thực hành Xử lý Binary Stream với Decoder & Buffer Pool | M3 | `PRACTICE` | 90 phút | 2026-11-28 19:00–20:30 (90p) | M3-O2 | T10 (bắt buộc) |
| **T13**: Review & Stress Test Pipeline chống Out-Of-Memory (OOM) | M3 | `REVIEW` | 90 phút | 2026-11-29 19:00–20:30 (90p) | M3-O1, M3-O2 | T11 (bắt buộc), T12 (bắt buộc) |
| **T14**: Lý thuyết Vòng đời Service và Cancellation Safety trong Tokio | M4 | `THEORY` | 90 phút | 2026-11-30 19:00–20:30 (90p) | M4-O2 | T13 (bắt buộc) |
| **T15**: Điều phối Tắt Ứng dụng với CancellationToken & Drop Guards | M4 | `THEORY` | 90 phút | 2026-12-01 19:00–20:30 (90p) | M4-O1 | T14 (bắt buộc) |
| **T16**: Thực hành Triển khai Graceful Shutdown cho TCP Server | M4 | `PRACTICE` | 90 phút | 2026-12-02 19:00–20:30 (90p) | M4-O1, M4-O2 | T15 (bắt buộc) |
| **T17**: Kiểm thử Shutdown Timeout và Xử lý Treo Kết nối Client | M4 | `REVIEW` | 90 phút | 2026-12-03 19:00–20:30 (90p) | M4-O1, M4-O2 | T16 (bắt buộc) |
| **T18**: Nguyên lý Lock-Free Concurrency và Memory Ordering trong Rust | M5 | `THEORY` | 90 phút | 2026-12-04 19:00–20:30 (90p) | M5-O1 | T17 (bắt buộc) |
| **T19**: Kỹ thuật Zero-Copy Buffer Management với Crate Bytes | M5 | `THEORY` | 90 phút | 2026-12-05 19:00–20:30 (90p) | M5-O2 | T18 (bắt buộc) |
| **T20**: Thực hành Tối ưu Trạng thái Chia sẻ với Lock-Free Primitives | M5 | `PRACTICE` | 90 phút | 2026-12-06 19:00–20:30 (90p) | M5-O1 | T18 (bắt buộc) |
| **T21**: Thực hành Tích hợp Zero-Copy Pipeline với Tokio I/O | M5 | `PRACTICE` | 90 phút | 2026-12-07 19:00–20:30 (90p) | M5-O2 | T19 (bắt buộc) |
| **T22**: Chẩn đoán Runtime Starvation và Task Latency với Tokio-Console | M5 | `REVIEW` | 90 phút | 2026-12-08 19:00–20:30 (90p) | M5-O2 | T20 (bắt buộc), T21 (bắt buộc) |
| **T23**: Dự án Tổng hợp: Production-Ready High-Performance Async Network Service | M5 | `PROJECT` | 90 phút | 2026-12-09 19:00–20:30 (90p) | M5-O1, M5-O2 | T22 (bắt buộc) |

#### Chi tiết nội dung M1 (4 tasks)

- **T1 — Nghiên cứu nguyên lý Future Trait, Context và Waker trong Async Rust** (`THEORY`, 90 phút)
  - *Mô tả:* Tìm hiểu kiến trúc Polling model của Rust: hàm poll, Wake-up notification mechanism, và cấu trúc std::task::Context.
  - *Mục tiêu học tập:* Hiểu rõ cơ chế poll-based asynchronous execution và vòng đời đánh thức task qua Waker.
  - *Tiêu chí hoàn thành:* Giải thích chi tiết luồng điều khiển giữa Executor, Future và Reactor khi nhận Poll::Pending và Poll::Ready.
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:00–20:30 (90p)
- **T2 — Nghiên cứu cơ chế Pinning, Pin và Unpin cho Self-referential Structs** (`THEORY`, 90 phút)
  - *Mô tả:* Phân tích vì sao async/await tạo ra cấu trúc self-referential trong bộ nhớ và cách Pin đảm bảo con trỏ không bị invalid do di chuyển bộ nhớ.
  - *Mục tiêu học tập:* Nắm vững ngữ nghĩa an toàn của Pin và phân biệt các kiểu dữ liệu Unpin vs !Unpin.
  - *Tiêu chí hoàn thành:* Vẽ và phân tích lược đồ bộ nhớ chứng minh rủi ro undefined behavior nếu move một future chưa được pin.
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-18 19:00–20:30 (90p)
- **T3 — Thực hành triển khai Custom Future và Waker registration** (`PRACTICE`, 90 phút)
  - *Mô tả:* Tự tay viết một TimerFuture hoặc EventFuture từ đầu, triển khai hàm poll và đăng ký Waker trên background thread.
  - *Mục tiêu học tập:* Tự triển khai thủ công một custom Future với hàm poll, quản lý trạng thái chuyển đổi và tái đăng ký Waker chính xác.
  - *Tiêu chí hoàn thành:* Viết mã nguồn custom TimerFuture hoạt động chính xác với một barebone executor mà không dùng thư viện ngoài.
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 19:00–20:30 (90p)
- **T4 — Thực hành và Đánh giá Self-referential Struct an toàn với Pin projection** (`REVIEW`, 90 phút)
  - *Mô tả:* Triển khai pin-projection an toàn bằng tay hoặc qua pin-project-lite, xử lý các trường hợp !Unpin trong cấu trúc dữ liệu async.
  - *Mục tiêu học tập:* Xử lý an toàn cấu trúc self-referential sử dụng std::pin::Pin và kiểm thử tính toàn vẹn bộ nhớ.
  - *Tiêu chí hoàn thành:* Kiểm thử và xác minh đoạn code self-referential biên dịch an toàn, không có unsafe code vi phạm quy tắc drop.
  - *Tiên quyết:* T2 (bắt buộc), T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:00–20:30 (90p)

#### Chi tiết nội dung M2 (4 tasks)

- **T5 — Kiến trúc Tokio Multi-threaded Runtime & Work-Stealing Algorithm** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu sâu về kiến trúc nội tại của Tokio runtime: Global queue, Local run queues, và giải thuật Chase-Lev work-stealing.
  - *Mục tiêu học tập:* Phân tích cơ chế work-stealing scheduler của Tokio và nguyên lý phân phối task giữa các worker threads.
  - *Tiêu chí hoàn thành:* Trình bày được cách thức worker thread cân bằng tải khi xảy ra hiện tượng mất cân bằng số lượng tasks.
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 19:00–20:30 (90p)
- **T6 — Cơ chế I/O Reactor Mio và Vấn đề Blocking trong Event Loop** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu tương tác giữa Tokio Reactor với epoll/kqueue (thông qua Mio) và rủi ro starve worker thread do blocking call.
  - *Mục tiêu học tập:* Hiểu rõ rủi ro thread starvation khi gọi blocking operations và cơ chế cách ly của spawn_blocking.
  - *Tiêu chí hoàn thành:* Giải thích được cơ chế thread pool chuyên dụng của Tokio dành riêng cho các tác vụ blocking I/O/CPU-bound.
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-22 19:00–20:30 (90p)
- **T7 — Thực hành cấu hình Tokio Runtime và Tách biệt Blocking I/O** (`PRACTICE`, 90 phút)
  - *Mô tả:* Xây dựng ứng dụng tải hỗn hợp: xử lý đồng thời HTTP/TCP non-blocking connections và nén file/tính toán băm dùng spawn_blocking.
  - *Mục tiêu học tập:* Phân tách an toàn các tác vụ CPU-bound/blocking I/O bằng spawn_blocking để chống suy thoái event loop.
  - *Tiêu chí hoàn thành:* Ứng dụng duy trì phản hồi I/O non-blocking ổn định kể cả khi khối lượng công việc blocking đạt tải đỉnh.
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:00–20:30 (90p)
- **T8 — Đo lường Latency & Tránh Starvation trên Tokio Worker Threads** (`REVIEW`, 90 phút)
  - *Mô tả:* Sử dụng benchmark và tracing để đo p99 latency của runtime khi có và không có blocking isolation.
  - *Mục tiêu học tập:* Đo lường và đánh giá hiệu năng runtime, chứng minh loại bỏ hoàn toàn worker thread starvation.
  - *Tiêu chí hoàn thành:* Báo cáo số liệu đo đạc cho thấy p99 latency của tác vụ non-blocking giảm ít nhất 80% khi cô lập blocking tasks.
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-24 19:00–20:30 (90p)

#### Chi tiết nội dung M3 (5 tasks)

- **T9 — Nguyên lý Tokio Channels & Chiến lược Kiểm soát Backpressure** (`THEORY`, 90 phút)
  - *Mô tả:* Tìm hiểu sâu mpsc, broadcast, watch, oneshot channels trong Tokio và nguyên lý điều tiết luồng với bounded buffers.
  - *Mục tiêu học tập:* Hiểu rõ cơ chế backpressure và tại sao unbounded channels tiềm ẩn nguy cơ OOM trong hệ thống tải cao.
  - *Tiêu chí hoàn thành:* So sánh được trade-off giữa các loại kênh truyền và mô tả cơ chế await của sender khi bounded buffer đầy.
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:00–20:30 (90p)
- **T10 — Thiết kế Stream Processing và Framing Giao thức Nhị phân** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu Tokio AsyncReadExt/AsyncWriteExt, Stream/Sink trait và triển khai Length-delimited Framing bằng tokio-util::codec.
  - *Mục tiêu học tập:* Nắm vững kỹ thuật framing dòng byte không biên giới thành các frames dữ liệu cấu trúc.
  - *Tiêu chí hoàn thành:* Viết được Encoder và Decoder giải mã gói tin nhị phân có length header chuẩn xác.
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-26 19:00–20:30 (90p)
- **T11 — Thực hành Xây dựng Producer-Consumer Pipeline có Giới hạn Tải** (`PRACTICE`, 90 phút)
  - *Mô tả:* Triển khai pipeline đa tầng với bounded channel, áp dụng permit acquisition để hạn chế số lượng tác vụ xử lý đồng thời.
  - *Mục tiêu học tập:* Thiết kế hệ thống producer-consumer có giới hạn dung lượng (bounded mpsc) xử lý backpressure triệt để.
  - *Tiêu chí hoàn thành:* Chạy thử nghiệm với producer tạo dữ liệu nhanh gấp 10 lần consumer, bộ nhớ RAM duy trì ổn định không tăng phi mã.
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-27 19:00–20:30 (90p)
- **T12 — Thực hành Xử lý Binary Stream với Decoder & Buffer Pool** (`PRACTICE`, 90 phút)
  - *Mô tả:* Kết hợp framed stream đọc nhị phân liên tục và đẩy vào pipeline xử lý dữ liệu với cơ chế xử lý lỗi rớt kết nối.
  - *Mục tiêu học tập:* Xử lý streaming dữ liệu mạng nhị phân hiệu quả bằng tokio::io::{AsyncReadExt, AsyncWriteExt} và Framing pattern.
  - *Tiêu chí hoàn thành:* Mã nguồn parse chính xác 100,000 frames nhị phân truyền liên tục qua TCP mà không xảy ra packet corruption.
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 19:00–20:30 (90p)
- **T13 — Review & Stress Test Pipeline chống Out-Of-Memory (OOM)** (`REVIEW`, 90 phút)
  - *Mô tả:* Chạy benchmark kiểm tra áp lực tải cực đại, đo lường heap memory consumption và throughput của stream pipeline.
  - *Mục tiêu học tập:* Đánh giá khả năng chịu tải và tính bền bỉ của hệ thống backpressure trước các đợt bùng nổ lưu lượng.
  - *Tiêu chí hoàn thành:* Biểu đồ cấp phát bộ nhớ phẳng hoàn toàn dưới áp lực tải nặng, không có dấu hiệu memory leak.
  - *Tiên quyết:* T11 (bắt buộc), T12 (bắt buộc) | *Lịch dự kiến:* 2026-11-29 19:00–20:30 (90p)

#### Chi tiết nội dung M4 (4 tasks)

- **T14 — Lý thuyết Vòng đời Service và Cancellation Safety trong Tokio** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu cách Future bị drop giữa chừng trong tokio::select!, rủi ro mất mát dữ liệu và nguyên tắc viết code Cancellation-safe.
  - *Mục tiêu học tập:* Đảm bảo cancellation safety cho các biểu thức tokio::select! và các tương tác stateful.
  - *Tiêu chí hoàn thành:* Xác định và giải thích được các hàm IO nào trong Tokio là cancellation safe và hàm nào không an toàn.
  - *Tiên quyết:* T13 (bắt buộc) | *Lịch dự kiến:* 2026-11-30 19:00–20:30 (90p)
- **T15 — Điều phối Tắt Ứng dụng với CancellationToken & Drop Guards** (`THEORY`, 90 phút)
  - *Mô tả:* Tìm hiểu mô hình graceful shutdown: lắng nghe POSIX signals (SIGINT/SIGTERM), broadcast shutdown signal qua CancellationToken.
  - *Mục tiêu học tập:* Áp dụng tokio_util::sync::CancellationToken và drop guards để điều phối tắt ứng dụng an toàn.
  - *Tiêu chí hoàn thành:* Thiết kế mô hình phân cấp token cha-con và cơ chế drop guard mpsc channel để chờ tất cả active tasks kết thúc.
  - *Tiên quyết:* T14 (bắt buộc) | *Lịch dự kiến:* 2026-12-01 19:00–20:30 (90p)
- **T16 — Thực hành Triển khai Graceful Shutdown cho TCP Server** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết TCP listener dừng nhận kết nối mới khi nhận signal, chờ các worker xử lý nốt connection hiện có trong khoảng thời gian timeout.
  - *Mục tiêu học tập:* Xây dựng TCP server có khả năng đóng kết nối an toàn không làm rớt dữ liệu client dở dang.
  - *Tiêu chí hoàn thành:* Mã nguồn server ngắt tiếp nhận kết nối mới và hoàn thành tất cả in-flight requests trước khi exit.
  - *Tiên quyết:* T15 (bắt buộc) | *Lịch dự kiến:* 2026-12-02 19:00–20:30 (90p)
- **T17 — Kiểm thử Shutdown Timeout và Xử lý Treo Kết nối Client** (`REVIEW`, 90 phút)
  - *Mô tả:* Viết kịch bản test client cố tình gửi dở dang payload hoặc treo kết nối để kích hoạt timeout shutdown ép buộc.
  - *Mục tiêu học tập:* Kiểm chứng tính toàn vẹn của tiến trình shutdown khi gặp client bất thường hoặc lỗi mạng.
  - *Tiêu chí hoàn thành:* Server tự động force-terminate kết nối vi phạm timeout đúng cấu hình mà không làm sập process đột ngột.
  - *Tiên quyết:* T16 (bắt buộc) | *Lịch dự kiến:* 2026-12-03 19:00–20:30 (90p)

#### Chi tiết nội dung M5 (6 tasks)

- **T18 — Nguyên lý Lock-Free Concurrency và Memory Ordering trong Rust** (`THEORY`, 90 phút)
  - *Mô tả:* Tìm hiểu std::sync::atomic (AtomicBool, AtomicUsize), các cấp độ Ordering (Relaxed, Acquire, Release, SeqCst) trong bối cảnh async.
  - *Mục tiêu học tập:* Nắm vững nguyên lý memory ordering và kỹ thuật thay thế async Mutex bằng Lock-free primitives.
  - *Tiêu chí hoàn thành:* Giải thích chi tiết cơ chế đồng bộ bộ nhớ giữa các CPU cores khi sử dụng Acquire-Release semantics.
  - *Tiên quyết:* T17 (bắt buộc) | *Lịch dự kiến:* 2026-12-04 19:00–20:30 (90p)
- **T19 — Kỹ thuật Zero-Copy Buffer Management với Crate Bytes** (`THEORY`, 90 phút)
  - *Mô tả:* Nghiên cứu cấu trúc Bytes, BytesMut, cơ chế ref-counting nội bộ và kỹ thuật cắt slice (slicing) không phân bổ thêm heap memory.
  - *Mục tiêu học tập:* Sử dụng Bytes crate để loại bỏ cấp phát bộ nhớ thừa trong quá trình chuyển tiếp dữ liệu mạng.
  - *Tiêu chí hoàn thành:* Mô tả cách Bytes::split và BytesMut hoạt động mà không cần gọi malloc/free liên tục.
  - *Tiên quyết:* T18 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 19:00–20:30 (90p)
- **T20 — Thực hành Tối ưu Trạng thái Chia sẻ với Lock-Free Primitives** (`PRACTICE`, 90 phút)
  - *Mô tả:* Áp dụng Atomic counters và lock-free ring buffer vào quản lý connection state và metrics mà không dùng tokio::sync::Mutex.
  - *Mục tiêu học tập:* Áp dụng Atomic primitives vào shared state trong môi trường async đa luồng để triệt tiêu contention.
  - *Tiêu chí hoàn thành:* Benchmark đối chiếu chứng minh loại bỏ mutex contention giúp tăng throughput tối thiểu 30%.
  - *Tiên quyết:* T18 (bắt buộc) | *Lịch dự kiến:* 2026-12-06 19:00–20:30 (90p)
- **T21 — Thực hành Tích hợp Zero-Copy Pipeline với Tokio I/O** (`PRACTICE`, 90 phút)
  - *Mô tả:* Xây dựng đường truyền proxy/forwarding dữ liệu TCP áp dụng BytesMut, socket buffer reuse và zero-copy slicing.
  - *Mục tiêu học tập:* Xây dựng luồng network service không cấp phát lại bộ nhớ cho mỗi packet được nhận và chuyển tiếp.
  - *Tiêu chí hoàn thành:* Kiểm tra memory profiler (Valgrind/DHAT) xác nhận số lượng heap allocations trong hot-path bằng 0.
  - *Tiên quyết:* T19 (bắt buộc) | *Lịch dự kiến:* 2026-12-07 19:00–20:30 (90p)
- **T22 — Chẩn đoán Runtime Starvation và Task Latency với Tokio-Console** (`REVIEW`, 90 phút)
  - *Mô tả:* Cấu hình console-subscriber, kết nối tokio-console trực tiếp tới tiến trình service đang chạy để kiểm tra poll times và task states.
  - *Mục tiêu học tập:* Sử dụng Tokio-console để chẩn đoán điểm nghẽn task contention, busy poll và task starvation.
  - *Tiêu chí hoàn thành:* Chỉ ra chính xác thời gian poll duration của từng task trên giao diện tokio-console trong điều kiện quá tải.
  - *Tiên quyết:* T20 (bắt buộc), T21 (bắt buộc) | *Lịch dự kiến:* 2026-12-08 19:00–20:30 (90p)
- **T23 — Dự án Tổng hợp: Production-Ready High-Performance Async Network Service** (`PROJECT`, 90 phút)
  - *Mô tả:* Tổng hợp toàn bộ kiến thức: Custom Future/Waker, Tokio runtime tuning, Bounded backpressure pipeline, Graceful shutdown và Zero-copy lock-free core.
  - *Mục tiêu học tập:* Hoàn thiện một TCP Network Service hoàn chỉnh đạt chuẩn production, profile chứng minh không có lock contention hay task starvation.
  - *Tiêu chí hoàn thành:* Dịch vụ vượt qua stress test 50,000 connections đồng thời, zero memory leak, shutdown an toàn dưới 5 giây khi nhận tín hiệu.
  - *Tiên quyết:* T22 (bắt buộc) | *Lịch dự kiến:* 2026-12-09 19:00–20:30 (90p)

---

## R-06 — Thiết kế Hệ thống & Distributed Cache với Redis

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Nắm vững các chiến lược caching (Cache-Aside, Write-Through, Write-Behind), consistent hashing, phòng chống cache stampede/avalanche, eviction policies và triển khai cụm Redis phân tán có rate limiting trong 4 tuần.
- **Khung thời gian:** `2026-11-17` → `2026-12-15`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_B — Thứ 3: 19:30–21:30 (120 phút); Thứ 5: 19:30–21:30 (120 phút); Thứ 7: 09:00–12:00 (180 phút)
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE trong 4 tuần bao phủ toàn bộ các khía cạnh cốt lõi của Distributed Caching với Redis: từ các mẫu thiết kế caching (Cache-Aside, Write-Through, Write-Behind), chính sách thu hồi (eviction policies), kỹ thuật xử lý sự cố quy mô lớn (stampede, avalanche, penetration), thuật toán Consistent Hashing đến triển khai thực tế cụm Redis Cluster phân tán tích hợp Rate Limiter bằng Lua Script.
- **Tổng quan cấu trúc:** 4 milestones | 12 tasks (PRACTICE: 5, PROJECT: 4, THEORY: 3) | 11 dependencies | Tổng thời lượng: 1200 phút (20.0 giờ) | Đã xếp lịch: 12/12 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Nền tảng Caching Patterns & Chiến lược Ghi Dữ liệu (240 phút)
- **Mô tả:** Nghiên cứu nguyên lý hoạt động, trade-offs và cài đặt các chiến lược caching cơ bản và nâng cao: Cache-Aside, Read-Through, Write-Through và Write-Behind (Write-Back).
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Phân tích ưu nhược điểm và sự đánh đổi về tính nhất quán giữa Cache-Aside, Write-Through và Write-Behind.
  - `M1-O2`: M1-O2: Cài đặt hoàn chỉnh mẫu Cache-Aside và Write-Through kết hợp TTL để đảm bảo tính tươi mới của dữ liệu.
- **Tiêu chí hoàn thành Milestone:** Viết được mã nguồn mô phỏng 3 chiến lược caching (Cache-Aside, Write-Through, Write-Behind) và vượt qua bài test so sánh độ trễ ghi/đọc.
- **Khái niệm nền tảng:** `sys-caching-redis-queues`
- **Khái niệm mở rộng (chưa có trong KB):** `cache-aside-pattern`, `write-through-pattern`, `write-behind-pattern`

#### M2. Chiến lược Thu hồi (Eviction Policies) & Phòng chống Lỗi Cache Kinh điển (300 phút)
- **Mô tả:** Tìm hiểu các thuật toán thu hồi bộ nhớ (LRU, LFU, FIFO, TTL-based) trong Redis và các giải pháp phòng thủ chống Cache Stampede, Cache Avalanche, Cache Breakdown và Cache Penetration.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Cấu hình và giải thích hành vi của các eviction policies trong Redis (allkeys-lru, volatile-lru, allkeys-lfu).
  - `M2-O2`: M2-O2: Áp dụng cơ chế Mutex lock/Distributed lock, Jittered TTL và Bloom filter để triệt tiêu Cache Stampede, Breakdown và Penetration.
- **Tiêu chí hoàn thành Milestone:** Mô phỏng kịch bản tải cao với k6/wrk để chứng minh hệ thống không bị sập cơ sở dữ liệu khi cache hết hạn đồng loạt (Cache Avalanche mitigation verified).
- **Khái niệm nền tảng:** `sys-caching-redis-queues`
- **Khái niệm mở rộng (chưa có trong KB):** `cache-eviction-policies`, `cache-stampede-mitigation`, `bloom-filter-caching`

#### M3. Phân tán Dữ liệu với Consistent Hashing & Redis Sharding (360 phút)
- **Mô tả:** Tìm hiểu kiến trúc sharding theo cụm, nguyên lý vòng băm nhất quán (Consistent Hashing Ring) kèm Virtual Nodes để phân bố đều tải và hạn chế xáo trộn cache khi thêm/bớt node.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Tự hiện thực thuật toán Consistent Hashing với cơ chế Virtual Nodes bằng ngôn ngữ lập trình tùy chọn.
  - `M3-O2`: M3-O2: Đánh giá tỷ lệ dịch chuyển key (key reassignment rate) khi scale-out hoặc failover cụm Redis.
- **Tiêu chí hoàn thành Milestone:** Hoàn thành thư viện hoặc module Consistent Hash Router với tỷ lệ lệch tải giữa các node dưới 10% khi thử nghiệm với 100,000 keys.
- **Khái niệm mở rộng (chưa có trong KB):** `consistent-hashing-algorithm`, `virtual-nodes-sharding`, `redis-cluster-architecture`

#### M4. Triển khai Cụm Redis Phân tán & Tích hợp Thuật toán Rate Limiting (360 phút)
- **Mô tả:** Thiết lập cụm Redis Cluster phân tán có cơ chế Master-Replica failover và triển khai hệ thống Rate Limiter hiệu năng cao (Sliding Window Log / Token Bucket) sử dụng Redis Lua Scripts.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Dựng cụm Redis Cluster đa node với Docker Compose hỗ trợ replication và automated failover.
  - `M4-O2`: M4-O2: Viết Redis Lua Script thực thi thuật toán Sliding Window Counter hoặc Token Bucket đảm bảo tính nguyên tử (atomic) cho Rate Limiting.
- **Tiêu chí hoàn thành Milestone:** Hệ thống Rate Limiter trên Redis Cluster xử lý chính xác giới hạn request theo IP/User ID dưới tải đồng thời 5000 RPS mà không phát sinh race condition.
- **Khái niệm nền tảng:** `sys-caching-redis-queues`
- **Khái niệm mở rộng (chưa có trong KB):** `redis-lua-scripting`, `distributed-rate-limiting`, `token-bucket-algorithm`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Nghiên cứu lý thuyết Caching Patterns & Chiến lược ghi dữ liệu | M1 | `THEORY` | 60 phút | 2026-11-17 19:30–20:30 (60p) | M1-O1 | Không |
| **T2**: Cài đặt thực hành Cache-Aside và Write-Through với Redis | M1 | `PRACTICE` | 90 phút | 2026-11-17 20:30–21:15 (45p); 2026-11-19 19:30–20:15 (45p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Cài đặt Write-Behind (Write-Back) và kiểm thử đối chuẩn độ trễ | M1 | `PROJECT` | 90 phút | 2026-11-19 20:15–21:00 (45p); 2026-11-21 09:00–09:45 (45p) | M1-O1, M1-O2 | T2 (bắt buộc) |
| **T4**: Cấu hình và kiểm chứng Redis Eviction Policies | M2 | `THEORY` | 60 phút | 2026-11-21 09:45–10:45 (60p) | M2-O1 | T3 (khuyến nghị) |
| **T5**: Cài đặt giải pháp phòng chống Cache Stampede, Breakdown & Penetration | M2 | `PRACTICE` | 120 phút | 2026-11-21 10:45–11:45 (60p); 2026-11-24 19:30–20:30 (60p) | M2-O2 | T4 (bắt buộc) |
| **T6**: Mô phỏng kiểm thử tải cao và đánh giá chống sập Cache Avalanche | M2 | `PROJECT` | 120 phút | 2026-11-24 20:30–21:30 (60p); 2026-11-26 19:30–20:30 (60p) | M2-O1, M2-O2 | T5 (bắt buộc) |
| **T7**: Nghiên cứu nguyên lý Hash Ring và Virtual Nodes trong Consistent Hashing | M3 | `THEORY` | 60 phút | 2026-11-26 20:30–21:30 (60p) | M3-O1 | T6 (khuyến nghị) |
| **T8**: Hiện thực module Consistent Hash Router với Virtual Nodes | M3 | `PRACTICE` | 120 phút | 2026-11-28 09:00–10:00 (60p); 2026-11-28 10:00–11:00 (60p) | M3-O1 | T7 (bắt buộc) |
| **T9**: Đánh giá tỷ lệ dịch chuyển key và kiểm thử cân bằng tải | M3 | `PROJECT` | 120 phút | 2026-11-28 11:00–12:00 (60p); 2026-12-01 19:30–20:30 (60p) | M3-O1, M3-O2 | T8 (bắt buộc) |
| **T10**: Khởi tạo Cụm Redis Cluster đa node với Docker Compose & Failover | M4 | `PRACTICE` | 120 phút | 2026-12-01 20:30–21:30 (60p); 2026-12-03 19:30–20:30 (60p) | M4-O1 | T9 (khuyến nghị) |
| **T11**: Viết Redis Lua Script thực thi thuật toán Sliding Window Counter | M4 | `PRACTICE` | 120 phút | 2026-12-03 20:30–21:30 (60p); 2026-12-05 09:00–10:00 (60p) | M4-O2 | T10 (bắt buộc) |
| **T12**: Kiểm thử chịu tải Rate Limiter phân tán đạt 5000 RPS | M4 | `PROJECT` | 120 phút | 2026-12-05 10:00–11:00 (60p); 2026-12-05 11:00–12:00 (60p) | M4-O1, M4-O2 | T11 (bắt buộc) |

#### Chi tiết nội dung M1 (3 tasks)

- **T1 — Nghiên cứu lý thuyết Caching Patterns & Chiến lược ghi dữ liệu** (`THEORY`, 60 phút)
  - *Mô tả:* Phân tích cơ chế hoạt động, sự đánh đổi tính nhất quán (consistency trade-offs) và độ trễ giữa Cache-Aside, Write-Through và Write-Behind.
  - *Mục tiêu học tập:* Hiểu rõ các mô hình đọc/ghi cache và đánh giá được trường hợp sử dụng phù hợp cho từng chiến lược.
  - *Tiêu chí hoàn thành:* Lập bảng so sánh chi tiết ưu/nhược điểm và độ trễ của 3 chiến lược caching.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:30–20:30 (60p)
- **T2 — Cài đặt thực hành Cache-Aside và Write-Through với Redis** (`PRACTICE`, 90 phút)
  - *Mô tả:* Hiện thực lớp dịch vụ caching cài đặt Cache-Aside và Write-Through kết hợp thiết lập TTL để đảm bảo tính tươi mới của dữ liệu.
  - *Mục tiêu học tập:* Cài đặt hoàn chỉnh luồng xử lý Cache-Aside và Write-Through bằng mã nguồn kết nối Redis.
  - *Tiêu chí hoàn thành:* Mã nguồn xử lý chính xác cache hit/miss và cập nhật dữ liệu đồng thời vào cache cùng cơ sở dữ liệu.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-17 20:30–21:15 (45p); 2026-11-19 19:30–20:15 (45p)
- **T3 — Cài đặt Write-Behind (Write-Back) và kiểm thử đối chuẩn độ trễ** (`PROJECT`, 90 phút)
  - *Mô tả:* Xây dựng cơ chế hàng đợi ghi bất đồng bộ cho Write-Behind và viết kịch bản benchmark đo lường độ trễ ghi/đọc giữa 3 chiến lược.
  - *Mục tiêu học tập:* Hoàn thiện trọn bộ 3 chiến lược caching và đánh giá định lượng hiệu năng thực tế.
  - *Tiêu chí hoàn thành:* Vượt qua bài test benchmark so sánh độ trễ ghi/đọc giữa Cache-Aside, Write-Through và Write-Behind.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 20:15–21:00 (45p); 2026-11-21 09:00–09:45 (45p)

#### Chi tiết nội dung M2 (3 tasks)

- **T4 — Cấu hình và kiểm chứng Redis Eviction Policies** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu nguyên lý và cấu hình thực tế các chính sách thu hồi bộ nhớ trong Redis: allkeys-lru, volatile-lru và allkeys-lfu dưới áp lực bộ nhớ đầy.
  - *Mục tiêu học tập:* Hiểu rõ cơ chế thu hồi bộ nhớ của Redis và lựa chọn chính sách tối ưu theo đặc tính tải.
  - *Tiêu chí hoàn thành:* Ghi nhận và giải thích chính xác hành vi loại bỏ key khi Redis đạt ngưỡng maxmemory với từng policy.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T3 (khuyến nghị) | *Lịch dự kiến:* 2026-11-21 09:45–10:45 (60p)
- **T5 — Cài đặt giải pháp phòng chống Cache Stampede, Breakdown & Penetration** (`PRACTICE`, 120 phút)
  - *Mô tả:* Tích hợp Distributed Mutex Lock (Redlock/SETNX), Jittered TTL và cấu trúc dữ liệu Bloom Filter để bảo vệ hệ thống trước các lỗi cache kinh điển.
  - *Mục tiêu học tập:* Làm chủ các kỹ thuật phòng thủ nâng cao nhằm bảo vệ database backend khỏi lượng truy vấn đột biến.
  - *Tiêu chí hoàn thành:* Mã nguồn triển khai thành công Mutex Lock ngăn chặn Breakdown và Bloom Filter lọc truy vấn không tồn tại.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 10:45–11:45 (60p); 2026-11-24 19:30–20:30 (60p)
- **T6 — Mô phỏng kiểm thử tải cao và đánh giá chống sập Cache Avalanche** (`PROJECT`, 120 phút)
  - *Mô tả:* Sử dụng công cụ k6 hoặc wrk tạo kịch bản tải cao đồng thời kiểm tra cơ chế Jittered TTL khi cache hết hạn hàng loạt.
  - *Mục tiêu học tập:* Chứng minh hệ thống giữ vững tính ổn định và database không bị quá tải khi cache hết hạn đồng loạt.
  - *Tiêu chí hoàn thành:* Báo cáo kiểm thử tải chứng minh 0 lỗi sập database và phân bố thời gian hết hạn key đều qua Jittered TTL.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-24 20:30–21:30 (60p); 2026-11-26 19:30–20:30 (60p)

#### Chi tiết nội dung M3 (3 tasks)

- **T7 — Nghiên cứu nguyên lý Hash Ring và Virtual Nodes trong Consistent Hashing** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu thuật toán phân phối dữ liệu phân tán Consistent Hashing, cấu trúc Hash Ring và vai trò cân bằng tải của Virtual Nodes.
  - *Mục tiêu học tập:* Nắm vững lý thuyết băm nhất quán và cách Virtual Nodes triệt tiêu hiện tượng lệch tải (hotspot).
  - *Tiêu chí hoàn thành:* Vẽ sơ đồ phân bổ key trên Hash Ring và tính toán lý thuyết tỷ lệ key cần di chuyển khi thêm/bớt node.
  - *Tiên quyết:* T6 (khuyến nghị) | *Lịch dự kiến:* 2026-11-26 20:30–21:30 (60p)
- **T8 — Hiện thực module Consistent Hash Router với Virtual Nodes** (`PRACTICE`, 120 phút)
  - *Mô tả:* Tự lập trình thuật toán Consistent Hashing với hỗ trợ cấu hình số lượng Virtual Nodes trên từng server vật lý.
  - *Mục tiêu học tập:* Xây dựng hoàn chỉnh router định tuyến key tới các Redis node phân tán.
  - *Tiêu chí hoàn thành:* Module biên dịch thành công, hỗ trợ các thao tác add_node, remove_node và get_node cho key bất kỳ.
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 09:00–10:00 (60p); 2026-11-28 10:00–11:00 (60p)
- **T9 — Đánh giá tỷ lệ dịch chuyển key và kiểm thử cân bằng tải** (`PROJECT`, 120 phút)
  - *Mô tả:* Thực hiện mô phỏng sharding với 100,000 keys, đo lường độ lệch phân phối tải và tỷ lệ tái phân bổ key khi mở rộng hoặc gặp sự cố node.
  - *Mục tiêu học tập:* Kiểm chứng tính ổn định và hiệu quả phân phối dữ liệu của Consistent Hashing trong môi trường thực nghiệm.
  - *Tiêu chí hoàn thành:* Độ lệch tải giữa các node đạt dưới 10% và tỷ lệ dịch chuyển key tiệm cận mức tối ưu 1/N khi scale.
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 11:00–12:00 (60p); 2026-12-01 19:30–20:30 (60p)

#### Chi tiết nội dung M4 (3 tasks)

- **T10 — Khởi tạo Cụm Redis Cluster đa node với Docker Compose & Failover** (`PRACTICE`, 120 phút)
  - *Mô tả:* Thiết lập cụm Redis Cluster (3 master - 3 replica) qua Docker Compose, cấu hình cluster bus và kiểm tra cơ chế tự động chuyển vùng dự phòng (failover).
  - *Mục tiêu học tập:* Triển khai hoàn chỉnh cụm Redis phân tán có tính sẵn sàng cao và khả năng chịu lỗi.
  - *Tiêu chí hoàn thành:* Cụm Redis Cluster hoạt động ổn định và replica tự động thăng cấp thành master khi master bị dừng.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T9 (khuyến nghị) | *Lịch dự kiến:* 2026-12-01 20:30–21:30 (60p); 2026-12-03 19:30–20:30 (60p)
- **T11 — Viết Redis Lua Script thực thi thuật toán Sliding Window Counter** (`PRACTICE`, 120 phút)
  - *Mô tả:* Xây dựng kịch bản Lua Script thực thi logic Rate Limiting dạng Sliding Window Counter hoặc Token Bucket đảm bảo tính nguyên tử (atomic) trên Redis.
  - *Mục tiêu học tập:* Lập trình kịch bản Lua nguyên tử trên Redis nhằm loại bỏ hoàn toàn race condition trong môi trường phân tán.
  - *Tiêu chí hoàn thành:* Script Lua thực thi thành công lệnh EVAL/EVALSHA, ghi nhận số request chính xác trong cửa sổ trượt thời gian.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-12-03 20:30–21:30 (60p); 2026-12-05 09:00–10:00 (60p)
- **T12 — Kiểm thử chịu tải Rate Limiter phân tán đạt 5000 RPS** (`PROJECT`, 120 phút)
  - *Mô tả:* Tích hợp Rate Limiter vào ứng dụng và chạy kiểm thử tải đồng thời 5000 RPS theo IP/User ID để kiểm tra tính chính xác và hiệu năng.
  - *Mục tiêu học tập:* Xác nhận hệ thống Rate Limiter hoạt động chính xác, ổn định dưới tải cao mà không phát sinh race condition.
  - *Tiêu chí hoàn thành:* Xử lý chuẩn xác 5000 RPS, chặn đúng các request vượt hạn mức với mã HTTP 429 và không có sai lệch dữ liệu.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 10:00–11:00 (60p); 2026-12-05 11:00–12:00 (60p)

---

## R-07 — IELTS Academic Writing Task 1 & Task 2 từ nền tảng

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `BEGINNER`
- **Mô tả mục tiêu:** Người mới bắt đầu luyện viết IELTS Academic mục tiêu 6.5: nắm cấu trúc câu học thuật, mô tả biểu đồ Task 1 (line, bar, table, process) và lập luận Task 2 (opinion, discussion, problem-solution) kèm tự chấm theo 4 tiêu chí.
- **Khung thời gian:** `2026-11-17` → `2026-12-31`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_A — Thứ 2–Thứ 6: 60 phút/ngày; Thứ 7 & CN: 90 phút/ngày
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE bao phủ toàn bộ mục tiêu IELTS Academic Writing cho người mới bắt đầu hướng tới Band 6.5: từ ngữ pháp câu học thuật, phương pháp làm Task 1 (tất cả các dạng biểu đồ số liệu và quy trình/bản đồ), triển khai luận điểm Task 2 (Opinion, Discussion, Problem-Solution), đến thực hành viết hoàn chỉnh 60 phút và kỹ năng tự chấm theo 4 tiêu chí chuẩn khảo thí.
- **Tổng quan cấu trúc:** 6 milestones | 32 tasks (PRACTICE: 14, PROJECT: 2, REVIEW: 6, THEORY: 10) | 31 dependencies | Tổng thời lượng: 1920 phút (32.0 giờ) | Đã xếp lịch: 32/32 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Nền tảng Ngữ pháp Học thuật & Hiểu rõ 4 Tiêu chí Chấm điểm IELTS Writing (300 phút)
- **Mô tả:** Nắm vững các tiêu chí chấm điểm IELTS Writing (Task Achievement/Response, Coherence & Cohesion, Lexical Resource, Grammatical Range & Accuracy) và củng cố các cấu trúc ngữ pháp học thuật nền tảng: câu ghép, câu phức, mệnh đề quan hệ và cách dùng từ nối học thuật.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Phân tích được các yêu cầu cụ thể của 4 tiêu chí chấm điểm theo chuẩn Band Descriptors mục tiêu 6.5
  - `M1-O2`: M1-O2: Sử dụng linh hoạt và chính xác các cấu trúc câu đơn, câu ghép và câu phức (mệnh đề quan hệ, mệnh đề trạng ngữ chỉ nguyên nhân/kết quả/nhượng bộ)
  - `M1-O3`: M1-O3: Vận dụng hệ thống từ nối (linking devices) và kỹ thuật paraphrase cơ bản mà không mắc lỗi chấm câu run-on hay comma splice
- **Tiêu chí hoàn thành Milestone:** Hoàn thành bài kiểm tra viết lại câu (paraphrase) gồm 15 câu học thuật và đạt độ chính xác ngữ pháp từ 80% trở lên, không mắc lỗi câu què hoặc câu chắp vá.
- **Khái niệm mở rộng (chưa có trong KB):** `ielts-band-descriptors-rubric`, `academic-sentence-structures`, `cohesive-devices-transitions`, `academic-paraphrasing-techniques`

#### M2. IELTS Writing Task 1: Báo cáo Biểu đồ Dữ liệu (Line Graph, Bar Chart, Table) (360 phút)
- **Mô tả:** Làm chủ cấu trúc bài viết Task 1 4 phần tiêu chuẩn (Introduction, Overview, 2 Body paragraphs), cách chọn lọc số liệu nổi bật, nhóm thông tin và sử dụng từ vựng miêu tả xu hướng biến động, so sánh số liệu.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Viết mở bài bằng cách paraphrase đề bài và viết đoạn tổng quan (Overview) nêu bật 2-3 đặc điểm chủ chốt
  - `M2-O2`: M2-O2: Phân nhóm thông tin logic vào 2 đoạn thân bài mà không liệt kê số liệu máy móc
  - `M2-O3`: M2-O3: Sử dụng chính xác từ vựng và cấu trúc miêu tả xu hướng (tăng, giảm, ổn định, biến động) và ngôn ngữ so sánh (hơn nhất, gấp đôi, tỉ lệ)
- **Tiêu chí hoàn thành Milestone:** Viết hoàn chỉnh 3 bài Task 1 thuộc 3 dạng Line Graph, Bar Chart và Table (mỗi bài tối thiểu 150 từ trong 25 phút), đảm bảo có đoạn Overview rõ ràng và số liệu được đối chiếu mạch lạc.
- **Khái niệm mở rộng (chưa có trong KB):** `task1-overview-strategy`, `trend-vocabulary-and-collocations`, `data-comparison-language`, `task1-data-grouping`

#### M3. IELTS Writing Task 1: Dạng Quy trình (Process) & Bản đồ (Map) (240 phút)
- **Mô tả:** Làm quen và thuần thục ngôn ngữ miêu tả biểu đồ phi số liệu bao gồm quy trình tự nhiên/nhân tạo và bản đồ thay đổi theo thời gian, tập trung vào thể bị động và từ ngữ chỉ trình tự/phương hướng.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Nhận diện và xác định số bước, giai đoạn đầu/cuối của quy trình hoặc những biến đổi cơ bản trên bản đồ để viết Overview
  - `M3-O2`: M3-O2: Sử dụng nhuần nhuyễn thể bị động (passive voice) và các liên từ chỉ thứ tự các bước trong quy trình
  - `M3-O3`: M3-O3: Vận dụng từ vựng chỉ vị trí địa lý, phương hướng và từ vựng miêu tả sự biến đổi công trình/cảnh quan trong dạng bài Map
- **Tiêu chí hoàn thành Milestone:** Viết hoàn chỉnh 1 bài Process và 1 bài Map với đầy đủ các giai đoạn/thay đổi, dùng đúng ít nhất 5 cấu trúc bị động và từ vựng phương hướng chuẩn xác.
- **Khái niệm mở rộng (chưa có trong KB):** `process-diagram-sequencing`, `passive-voice-in-process`, `map-transformation-vocabulary`, `spatial-prepositions-directions`

#### M4. IELTS Writing Task 2: Cấu trúc Luận điểm & Dạng bài Opinion (Agree/Disagree) (360 phút)
- **Mô tả:** Xây dựng tư duy phát triển ý theo mô hình PEEL (Point, Explanation, Example, Link), lập dàn ý nhanh và thực hành triển khai bài luận nêu quan điểm cá nhân (Opinion Essay).
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Phân tích đề bài Task 2, xác định từ khóa và phát triển ý tưởng đa chiều trong vòng 5 phút lập dàn ý
  - `M4-O2`: M4-O2: Viết mở bài có câu chủ đề (thesis statement) thể hiện rõ lập trường xuyên suốt và kết bài khẳng định lại quan điểm
  - `M4-O3`: M4-O3: Viết đoạn thân bài mạch lạc theo cấu trúc PEEL, phát triển dẫn chứng và giải thích sâu thay vì chỉ liệt kê ý
- **Tiêu chí hoàn thành Milestone:** Hoàn thành 2 bài luận Task 2 dạng Agree/Disagree đạt tối thiểu 250 từ, trong đó mỗi đoạn thân bài có luận điểm rõ ràng kèm giải thích logic và ví dụ minh họa cụ thể.
- **Khái niệm mở rộng (chưa có trong KB):** `task2-peel-paragraphing`, `thesis-statement-formulation`, `opinion-essay-structure`, `idea-brainstorming-framework`

#### M5. IELTS Writing Task 2: Dạng bài Discussion & Problem-Solution / Two-Part Question (360 phút)
- **Mô tả:** Thành thạo kỹ thuật xử lý các dạng đề Task 2 phổ biến còn lại: thảo luận hai quan điểm (Discuss both views) và nguyên nhân - giải pháp (Causes/Problems and Solutions).
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M5-O1`: M5-O1: Viết bài thảo luận hai mặt cân bằng, phân biệt rõ quan điểm khách quan của người khác và ý kiến cá nhân của người viết
  - `M5-O2`: M5-O2: Kết nối nguyên nhân trực tiếp với giải pháp tương ứng một cách logic, tránh đưa ra giải pháp chung chung không giải quyết vấn đề đã nêu
  - `M5-O3`: M5-O3: Kiểm soát độ mạch lạc giữa các đoạn văn bằng các liên từ chuyển tiếp tương phản và hệ quả phù hợp
- **Tiêu chí hoàn thành Milestone:** Viết hoàn chỉnh 1 bài dạng Discussion Both Views và 1 bài dạng Problems & Solutions (tối thiểu 250 từ/bài) với cấu trúc cân đối và lập luận chặt chẽ.
- **Khái niệm mở rộng (chưa có trong KB):** `discussion-essay-structure`, `problem-solution-essay-structure`, `counter-argument-rebuttal`, `academic-topic-collocations`

#### M6. Chiến lược Quản lý Thời gian, Luyện Viết Full Test & Tự Đánh giá theo Rubric 6.5 (300 phút)
- **Mô tả:** Thực hành viết cả 2 phần Task 1 và Task 2 trong khung thời gian chuẩn 60 phút, đồng thời áp dụng quy trình tự kiểm tra lỗi (proofreading) và đánh giá chi tiết theo 4 tiêu chí chấm thi.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M6-O1`: M6-O1: Hoàn thành đồng thời Task 1 (20 phút) và Task 2 (40 phút) đúng yêu cầu dung lượng dưới áp lực thời gian thực tế
  - `M6-O2`: M6-O2: Áp dụng checklist rà soát lỗi chính tả, chia động từ, mạo từ và sự hòa hợp giữa chủ ngữ - vị ngữ trong 3-5 phút cuối
  - `M6-O3`: M6-O3: Tự chấm và ghi nhận lỗi sai định kỳ dựa trên bảng mô tả tiêu chí Band 6.5 để có phương án điều chỉnh phù hợp
- **Tiêu chí hoàn thành Milestone:** Hoàn thành 2 đề thi thử toàn diện (Task 1 + Task 2) trong 60 phút mỗi đề, kèm bản tự chấm và phân tích lỗi sai chi tiết theo từng tiêu chí TR/TA, CC, LR, GRA.
- **Khái niệm mở rộng (chưa có trong KB):** `exam-time-management-strategy`, `self-editing-and-proofreading`, `ielts-band6.5-diagnostic-audit`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Phân tích 4 tiêu chí chấm điểm IELTS Writing theo Rubric Band 6.5 | M1 | `THEORY` | 60 phút | 2026-11-17 19:00–20:00 (60p) | M1-O1 | Không |
| **T2**: Xây dựng các cấu trúc câu phức và câu ghép học thuật | M1 | `THEORY` | 60 phút | 2026-11-18 19:00–20:00 (60p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Thực hành sử dụng từ nối (Linking Devices) và Paraphrasing căn bản | M1 | `PRACTICE` | 60 phút | 2026-11-19 19:00–20:00 (60p) | M1-O2, M1-O3 | T2 (bắt buộc) |
| **T4**: Luyện tập nhận diện và sửa lỗi Run-on, Comma Splice và Fragment | M1 | `PRACTICE` | 60 phút | 2026-11-20 19:00–20:00 (60p) | M1-O3 | T3 (bắt buộc) |
| **T5**: Kiểm tra đánh giá nền tảng ngữ pháp và tiêu chí viết học thuật | M1 | `REVIEW` | 60 phút | 2026-11-21 19:00–20:00 (60p) | M1-O1, M1-O2, M1-O3 | T4 (bắt buộc) |
| **T6**: Kỹ thuật viết Introduction và xác định Overview cho biểu đồ dữ liệu | M2 | `THEORY` | 60 phút | 2026-11-22 19:00–20:00 (60p) | M2-O1 | T5 (bắt buộc) |
| **T7**: Hệ thống từ vựng miêu tả xu hướng và cấu trúc so sánh định lượng | M2 | `THEORY` | 60 phút | 2026-11-23 19:00–20:00 (60p) | M2-O3 | T6 (bắt buộc) |
| **T8**: Chiến lược phân nhóm dữ liệu và triển khai 2 đoạn Thân bài (Body) | M2 | `PRACTICE` | 60 phút | 2026-11-24 19:00–20:00 (60p) | M2-O2 | T7 (bắt buộc) |
| **T9**: Thực hành viết bài hoàn chỉnh dạng Line Graph và Bar Chart | M2 | `PRACTICE` | 60 phút | 2026-11-25 19:00–20:00 (60p) | M2-O1, M2-O2, M2-O3 | T8 (bắt buộc) |
| **T10**: Thực hành phân tích và viết bài báo cáo số liệu dạng Bảng (Table) | M2 | `PRACTICE` | 60 phút | 2026-11-26 19:00–20:00 (60p) | M2-O2, M2-O3 | T9 (bắt buộc) |
| **T11**: Đánh giá, sửa lỗi và tối ưu hóa 3 bài viết biểu đồ dữ liệu Task 1 | M2 | `REVIEW` | 60 phút | 2026-11-27 19:00–20:00 (60p) | M2-O1, M2-O2, M2-O3 | T10 (bắt buộc) |
| **T12**: Chiến lược làm bài và viết Overview cho dạng Quy trình (Process) & Bản đồ (Map) | M3 | `THEORY` | 60 phút | 2026-11-28 19:00–20:00 (60p) | M3-O1 | T11 (bắt buộc) |
| **T13**: Thực hành thể bị động và từ nối tuần tự trong dạng bài Process | M3 | `PRACTICE` | 60 phút | 2026-11-29 19:00–20:00 (60p) | M3-O1, M3-O2 | T12 (bắt buộc) |
| **T14**: Từ vựng phương hướng, vị trí và miêu tả biến đổi trong dạng bài Map | M3 | `PRACTICE` | 60 phút | 2026-11-30 19:00–20:00 (60p) | M3-O1, M3-O3 | T13 (bắt buộc) |
| **T15**: Hoàn thiện và đánh giá cặp bài viết Process & Map theo chuẩn Band 6.5 | M3 | `PROJECT` | 60 phút | 2026-12-01 19:00–20:00 (60p) | M3-O1, M3-O2, M3-O3 | T14 (bắt buộc) |
| **T16**: Kỹ thuật phân tích đề bài Task 2 và Brainstorming dàn ý trong 5 phút | M4 | `THEORY` | 60 phút | 2026-12-02 19:00–20:00 (60p) | M4-O1 | T15 (bắt buộc) |
| **T17**: Xây dựng Mở bài có Thesis Statement rõ ràng và Kết bài khẳng định lập trường | M4 | `THEORY` | 60 phút | 2026-12-03 19:00–20:00 (60p) | M4-O2 | T16 (bắt buộc) |
| **T18**: Phương pháp phát triển đoạn thân bài học thuật theo cấu trúc PEEL | M4 | `PRACTICE` | 60 phút | 2026-12-04 19:00–20:00 (60p) | M4-O3 | T17 (bắt buộc) |
| **T19**: Thực hành viết bài luận hoàn chỉnh dạng To what extent do you agree or disagree (Bài 1) | M4 | `PRACTICE` | 60 phút | 2026-12-05 19:00–20:00 (60p) | M4-O1, M4-O2, M4-O3 | T18 (bắt buộc) |
| **T20**: Thực hành viết bài luận Opinion tiếp cận theo hướng cân bằng/nhượng bộ (Bài 2) | M4 | `PRACTICE` | 60 phút | 2026-12-06 19:00–20:00 (60p) | M4-O2, M4-O3 | T19 (bắt buộc) |
| **T21**: Đánh giá chéo và hiệu đính 2 bài luận Agree/Disagree theo tiêu chí TR & CC | M4 | `REVIEW` | 60 phút | 2026-12-07 19:00–20:00 (60p) | M4-O1, M4-O2, M4-O3 | T20 (bắt buộc) |
| **T22**: Cấu trúc luận điểm dạng bài Discuss Both Views and Give Your Opinion | M5 | `THEORY` | 60 phút | 2026-12-08 19:00–20:00 (60p) | M5-O1, M5-O3 | T21 (bắt buộc) |
| **T23**: Chiến lược ghép nối Nguyên nhân - Giải pháp cho dạng Causes/Problems & Solutions | M5 | `THEORY` | 60 phút | 2026-12-09 19:00–20:00 (60p) | M5-O2, M5-O3 | T22 (bắt buộc) |
| **T24**: Thực hành viết bài luận hoàn chỉnh dạng Discuss Both Views | M5 | `PRACTICE` | 60 phút | 2026-12-10 19:00–20:00 (60p) | M5-O1, M5-O3 | T23 (bắt buộc) |
| **T25**: Thực hành viết bài luận hoàn chỉnh dạng Problems & Solutions | M5 | `PRACTICE` | 60 phút | 2026-12-11 19:00–20:00 (60p) | M5-O2, M5-O3 | T24 (bắt buộc) |
| **T26**: Luyện tập dạng bài Two-Part Question và kiểm soát Cohesion liên đoạn | M5 | `PRACTICE` | 60 phút | 2026-12-12 19:00–20:00 (60p) | M5-O1, M5-O2, M5-O3 | T25 (bắt buộc) |
| **T27**: Hiệu đính, đối chiếu từ vựng học thuật và tính mạch lạc cho Task 2 | M5 | `REVIEW` | 60 phút | 2026-12-13 19:00–20:00 (60p) | M5-O1, M5-O2, M5-O3 | T26 (bắt buộc) |
| **T28**: Chiến lược phân bổ 60 phút phòng thi và Checklist kiểm soát lỗi sai | M6 | `THEORY` | 60 phút | 2026-12-14 19:00–20:00 (60p) | M6-O1, M6-O2 | T27 (bắt buộc) |
| **T29**: Luyện viết Full Test 1 (Task 1 + Task 2) mô phỏng áp lực thời gian thực tế | M6 | `PRACTICE` | 60 phút | 2026-12-15 19:00–20:00 (60p) | M6-O1 | T28 (bắt buộc) |
| **T30**: Áp dụng Checklist rà soát lỗi và tự đánh giá Full Test 1 theo Rubric 6.5 | M6 | `REVIEW` | 60 phút | 2026-12-16 19:00–20:00 (60p) | M6-O2, M6-O3 | T29 (bắt buộc) |
| **T31**: Luyện viết Full Test 2 với dạng đề kết hợp dưới điều kiện phòng thi | M6 | `PROJECT` | 60 phút | 2026-12-17 19:00–20:00 (60p) | M6-O1, M6-O2 | T30 (bắt buộc) |
| **T32**: Chẩn đoán tổng kết lỗi sai định kỳ và xây dựng cẩm nang cá nhân Band 6.5 | M6 | `REVIEW` | 60 phút | 2026-12-18 19:00–20:00 (60p) | M6-O2, M6-O3 | T31 (bắt buộc) |

#### Chi tiết nội dung M1 (5 tasks)

- **T1 — Phân tích 4 tiêu chí chấm điểm IELTS Writing theo Rubric Band 6.5** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu chi tiết 4 tiêu chí chấm điểm chính thức: Task Achievement/Task Response, Coherence and Cohesion, Lexical Resource, và Grammatical Range and Accuracy với các yêu cầu cốt lõi để đạt Band 6.5.
  - *Mục tiêu học tập:* Hiểu rõ các yêu cầu cụ thể của từng tiêu chí chấm điểm và các lỗi phổ biến cần tránh để đạt mục tiêu 6.5.
  - *Tiêu chí hoàn thành:* Lập bảng tóm tắt 4 tiêu chí chấm điểm kèm checklist tiêu chuẩn band 6.5 cho cả Task 1 và Task 2.
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:00–20:00 (60p)
- **T2 — Xây dựng các cấu trúc câu phức và câu ghép học thuật** (`THEORY`, 60 phút)
  - *Mô tả:* Nắm vững nguyên tắc kết hợp mệnh đề độc lập và mệnh đề phụ thuộc (mệnh đề quan hệ, mệnh đề trạng ngữ chỉ kết quả, nguyên nhân, nhượng bộ) nhằm nâng cao tiêu chí Grammatical Range.
  - *Mục tiêu học tập:* Phân biệt và cấu tạo chính xác câu ghép, câu phức trong văn phong học thuật mà không mắc lỗi ngữ pháp cơ bản.
  - *Tiêu chí hoàn thành:* Viết được 10 cặp câu minh họa sử dụng đúng các loại mệnh đề phụ thuộc phổ biến trong IELTS Writing.
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-18 19:00–20:00 (60p)
- **T3 — Thực hành sử dụng từ nối (Linking Devices) và Paraphrasing căn bản** (`PRACTICE`, 60 phút)
  - *Mô tả:* Rèn luyện các phương pháp diễn đạt lại câu (dùng từ đồng nghĩa, đổi dạng từ, chuyển đổi chủ động - bị động) và sử dụng liên từ nối câu/đoạn tự nhiên.
  - *Mục tiêu học tập:* Vận dụng linh hoạt kỹ thuật paraphrase và đặt từ nối đúng vị trí, tránh lạm dụng gây mất tự nhiên.
  - *Tiêu chí hoàn thành:* Hoàn thành bài tập paraphrase 10 câu chủ đề học thuật và chèn đúng từ nối liên kết logic.
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 19:00–20:00 (60p)
- **T4 — Luyện tập nhận diện và sửa lỗi Run-on, Comma Splice và Fragment** (`PRACTICE`, 60 phút)
  - *Mô tả:* Phân tích các đoạn văn mẫu chứa lỗi chấm câu sai ngữ pháp (comma splice, run-on sentence, incomplete sentences) và tiến hành sửa lại thành câu chuẩn xác.
  - *Mục tiêu học tập:* Nhận diện triệt để các lỗi chấm câu làm gián đoạn mạch văn và sửa đúng ngữ pháp theo tiêu chuẩn học thuật.
  - *Tiêu chí hoàn thành:* Sửa chính xác toàn bộ lỗi câu què, câu chắp vá trong bài tập 15 câu mẫu với độ chính xác trên 80%.
  - *Tiên quyết:* T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:00–20:00 (60p)
- **T5 — Kiểm tra đánh giá nền tảng ngữ pháp và tiêu chí viết học thuật** (`REVIEW`, 60 phút)
  - *Mô tả:* Thực hiện bài kiểm tra tổng hợp viết lại 15 câu học thuật hoàn chỉnh, kết hợp các cấu trúc câu phức, từ nối và từ vựng học thuật.
  - *Mục tiêu học tập:* Củng cố kiến thức ngữ pháp và khả năng tự phát hiện lỗi sai câu trước khi bước vào các dạng bài thi cụ thể.
  - *Tiêu chí hoàn thành:* Đạt từ 80% điểm bài kiểm tra viết lại câu 15 câu học thuật và hoàn thành bản tự nhận xét lỗi ngữ pháp cá nhân.
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 19:00–20:00 (60p)

#### Chi tiết nội dung M2 (6 tasks)

- **T6 — Kỹ thuật viết Introduction và xác định Overview cho biểu đồ dữ liệu** (`THEORY`, 60 phút)
  - *Mô tả:* Học công thức viết mở bài nhanh bằng cách paraphrase đề bài và phương pháp quan sát tìm 2-3 điểm nổi bật nhất (xu hướng chung, điểm cao nhất/thấp nhất) để viết đoạn Tổng quan (Overview).
  - *Mục tiêu học tập:* Viết được đoạn Introduction chuẩn chỉnh và đoạn Overview nêu bật đặc trưng cốt lõi mà không bị sa đà vào liệt kê số liệu.
  - *Tiêu chí hoàn thành:* Viết hoàn chỉnh Introduction và Overview cho 3 đề bài mẫu dạng Line Graph, Bar Chart và Table.
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-22 19:00–20:00 (60p)
- **T7 — Hệ thống từ vựng miêu tả xu hướng và cấu trúc so sánh định lượng** (`THEORY`, 60 phút)
  - *Mô tả:* Nắm vững các động từ, danh từ, trạng từ miêu tả sự tăng giảm, dao động, ổn định cùng các cấu trúc so sánh (hơn, nhất, gấp nhiều lần, chiếm tỉ lệ).
  - *Mục tiêu học tập:* Sử dụng chính xác và linh hoạt các cấu trúc mô tả xu hướng và số liệu so sánh tương đối/tuyệt đối.
  - *Tiêu chí hoàn thành:* Lập bảng tổng hợp từ vựng xu hướng và đặt 10 câu so sánh số liệu dựa trên biểu đồ cho trước.
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:00–20:00 (60p)
- **T8 — Chiến lược phân nhóm dữ liệu và triển khai 2 đoạn Thân bài (Body)** (`PRACTICE`, 60 phút)
  - *Mô tả:* Học cách chia nhóm đối tượng/thời gian hợp lý thành 2 đoạn thân bài logic, đối chiếu số liệu mốc thời gian và điểm nổi bật thay vì chép lại dữ liệu thô.
  - *Mục tiêu học tập:* Tổ chức dữ liệu logic vào 2 đoạn thân bài có chọn lọc số liệu trọng tâm.
  - *Tiêu chí hoàn thành:* Hoàn thành dàn ý chi tiết và viết 2 đoạn thân bài cho 1 đề biểu đồ đường (Line Graph).
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-24 19:00–20:00 (60p)
- **T9 — Thực hành viết bài hoàn chỉnh dạng Line Graph và Bar Chart** (`PRACTICE`, 60 phút)
  - *Mô tả:* Áp dụng đầy đủ quy trình 4 bước (Phân tích - Dàn ý - Viết bài - Rà soát) để hoàn thành 2 bài viết hoàn chỉnh cho biểu đồ đường và biểu đồ cột.
  - *Mục tiêu học tập:* Viết hoàn chỉnh bài viết biểu đồ đường và biểu đồ cột đạt chuẩn dung lượng tối thiểu 150 từ.
  - *Tiêu chí hoàn thành:* Hoàn thành 2 bài viết Task 1 (Line Graph và Bar Chart) với đầy đủ 4 đoạn trong thời gian 25 phút mỗi bài.
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:00–20:00 (60p)
- **T10 — Thực hành phân tích và viết bài báo cáo số liệu dạng Bảng (Table)** (`PRACTICE`, 60 phút)
  - *Mô tả:* Luyện tập kỹ năng xử lý dữ liệu phức tạp trong dạng bảng, xác định hàng/cột trọng tâm và viết bài báo cáo hoàn chỉnh.
  - *Mục tiêu học tập:* Xử lý bảng số liệu nhiều đối tượng bằng cách gom nhóm tương đồng và so sánh nổi bật.
  - *Tiêu chí hoàn thành:* Hoàn thành bài viết hoàn chỉnh cho đề bài dạng Table đạt tối thiểu 150 từ.
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-26 19:00–20:00 (60p)
- **T11 — Đánh giá, sửa lỗi và tối ưu hóa 3 bài viết biểu đồ dữ liệu Task 1** (`REVIEW`, 60 phút)
  - *Mô tả:* Soát lại 3 bài viết Task 1 (Line, Bar, Table) theo rubric Band 6.5, đối chiếu việc trích dẫn số liệu, tính chính xác của mạo từ, giới từ chỉ thời gian và số liệu.
  - *Mục tiêu học tập:* Tự phát hiện lỗi diễn đạt, thiếu dẫn chứng số liệu hoặc overview chưa rõ ràng trong các bài báo cáo dữ liệu.
  - *Tiêu chí hoàn thành:* Bản sửa chữa hoàn thiện của 3 bài viết Task 1 kèm danh sách lỗi thường gặp về giới từ và thì của động từ.
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-11-27 19:00–20:00 (60p)

#### Chi tiết nội dung M3 (4 tasks)

- **T12 — Chiến lược làm bài và viết Overview cho dạng Quy trình (Process) & Bản đồ (Map)** (`THEORY`, 60 phút)
  - *Mô tả:* Nắm vững đặc thù của dạng đề hình vẽ: phân loại Natural Process vs Manufacturing Process, dạng Map so sánh mốc thời gian hoặc quy hoạch tương lai; viết Overview tương ứng.
  - *Mục tiêu học tập:* Xác định nhanh số bước của quy trình và các thay đổi chính yếu trên bản đồ để xây dựng Overview chuẩn xác.
  - *Tiêu chí hoàn thành:* Viết được Introduction và Overview cho 1 đề Process sản xuất và 1 đề Map quy hoạch đô thị.
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 19:00–20:00 (60p)
- **T13 — Thực hành thể bị động và từ nối tuần tự trong dạng bài Process** (`PRACTICE`, 60 phút)
  - *Mô tả:* Rèn luyện sử dụng thể bị động (passive voice) theo các thì phù hợp kết hợp hệ thống liên từ chỉ thứ tự (initially, following this, subsequently, once, finally) để mô tả dây chuyền sản xuất.
  - *Mục tiêu học tập:* Sử dụng nhuần nhuyễn thể bị động và từ nối chỉ trình tự để liên kết các bước trong quy trình mượt mà.
  - *Tiêu chí hoàn thành:* Viết hoàn chỉnh bài Task 1 dạng Man-made Process với ít nhất 5 câu sử dụng thể bị động chuẩn ngữ pháp.
  - *Tiên quyết:* T12 (bắt buộc) | *Lịch dự kiến:* 2026-11-29 19:00–20:00 (60p)
- **T14 — Từ vựng phương hướng, vị trí và miêu tả biến đổi trong dạng bài Map** (`PRACTICE`, 60 phút)
  - *Mô tả:* Nắm vững từ vựng chỉ phương hướng (to the north of, in the south-western corner), giới từ chỉ nơi chốn và các động từ biến đổi cảnh quan/công trình (demolish, replace, erect, expand).
  - *Mục tiêu học tập:* Mô tả chính xác vị trí và sự chuyển biến của các công trình qua các năm trong sơ đồ bản đồ.
  - *Tiêu chí hoàn thành:* Viết hoàn chỉnh bài Task 1 dạng Map so sánh sự thay đổi của một khu vực qua 2 thời điểm khác nhau.
  - *Tiên quyết:* T13 (bắt buộc) | *Lịch dự kiến:* 2026-11-30 19:00–20:00 (60p)
- **T15 — Hoàn thiện và đánh giá cặp bài viết Process & Map theo chuẩn Band 6.5** (`PROJECT`, 60 phút)
  - *Mô tả:* Tổng hợp kỹ năng, rà soát lại 2 bài viết hoàn chỉnh (1 Process, 1 Map), kiểm tra việc chia động từ, giới từ phương hướng và mạch liên kết.
  - *Mục tiêu học tập:* Tự hoàn thiện sản phẩm viết Task 1 dạng phi số liệu đạt tiêu chí rõ ràng, chính xác và đầy đủ các bước.
  - *Tiêu chí hoàn thành:* Bộ 2 bài viết hoàn chỉnh (1 Process và 1 Map) đạt tối thiểu 150 từ/bài, đáp ứng đầy đủ tiêu chí completion criteria của cột mốc.
  - *Tiên quyết:* T14 (bắt buộc) | *Lịch dự kiến:* 2026-12-01 19:00–20:00 (60p)

#### Chi tiết nội dung M4 (6 tasks)

- **T16 — Kỹ thuật phân tích đề bài Task 2 và Brainstorming dàn ý trong 5 phút** (`THEORY`, 60 phút)
  - *Mô tả:* Phương pháp bóc tách đề bài: xác định chủ đề lớn (Topic), giới hạn câu hỏi (Scope), từ khóa chỉ định hướng (Micro-keywords) và phương pháp phát triển ý tưởng đa chiều.
  - *Mục tiêu học tập:* Phân tích trúng trọng tâm câu hỏi đề bài và xây dựng dàn ý 2 thân bài logic trong vòng 5 phút.
  - *Tiêu chí hoàn thành:* Lập dàn ý hoàn chỉnh cho 3 đề Task 2 thuộc các chủ đề phổ biến (Education, Technology, Environment).
  - *Tiên quyết:* T15 (bắt buộc) | *Lịch dự kiến:* 2026-12-02 19:00–20:00 (60p)
- **T17 — Xây dựng Mở bài có Thesis Statement rõ ràng và Kết bài khẳng định lập trường** (`THEORY`, 60 phút)
  - *Mô tả:* Học cấu trúc mở bài chuẩn gồm 2 câu (Background sentence + Thesis statement thể hiện rõ quan điểm) và kết bài tổng kết luận điểm nhất quán cho dạng bài Opinion.
  - *Mục tiêu học tập:* Viết mở bài và kết bài chuẩn mực, đảm bảo lập trường của người viết được duy trì xuyên suốt bài luận.
  - *Tiêu chí hoàn thành:* Viết 3 cặp Mở bài - Kết bài thể hiện quan điểm đồng tình/không đồng tình rõ ràng cho các đề bài Agree/Disagree.
  - *Tiên quyết:* T16 (bắt buộc) | *Lịch dự kiến:* 2026-12-03 19:00–20:00 (60p)
- **T18 — Phương pháp phát triển đoạn thân bài học thuật theo cấu trúc PEEL** (`PRACTICE`, 60 phút)
  - *Mô tả:* Nắm vững và thực hành cấu trúc PEEL (Point - Explanation - Example - Link) để viết đoạn thân bài có luận điểm vững chắc, giải thích sâu sắc và dẫn chứng thuyết phục.
  - *Mục tiêu học tập:* Triển khai lập luận mạch lạc, tránh lối liệt kê ý tưởng hời hợt không có diễn giải nguyên nhân - kết quả.
  - *Tiêu chí hoàn thành:* Viết 2 đoạn thân bài chuẩn PEEL cho một đề bài Agree/Disagree với độ dài từ 90-110 từ mỗi đoạn.
  - *Tiên quyết:* T17 (bắt buộc) | *Lịch dự kiến:* 2026-12-04 19:00–20:00 (60p)
- **T19 — Thực hành viết bài luận hoàn chỉnh dạng To what extent do you agree or disagree (Bài 1)** (`PRACTICE`, 60 phút)
  - *Mô tả:* Áp dụng toàn bộ quy trình: lập dàn ý 5 phút, viết mở bài, 2 thân bài PEEL và kết bài theo hướng hoàn toàn đồng ý hoặc hoàn toàn không đồng ý.
  - *Mục tiêu học tập:* Hoàn thành bài luận Task 2 dạng Opinion đạt độ dài tối thiểu 250 từ trong 40 phút.
  - *Tiêu chí hoàn thành:* Bài luận hoàn chỉnh số 1 đạt ít nhất 250 từ, lập luận có chiều sâu và thể hiện quan điểm nhất quán.
  - *Tiên quyết:* T18 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 19:00–20:00 (60p)
- **T20 — Thực hành viết bài luận Opinion tiếp cận theo hướng cân bằng/nhượng bộ (Bài 2)** (`PRACTICE`, 60 phút)
  - *Mô tả:* Rèn luyện cách viết bài dạng Opinion theo hướng cân bằng (Balanced approach) bằng cách sử dụng mệnh đề nhượng bộ (Concession) để tăng tính thuyết phục của lập luận.
  - *Mục tiêu học tập:* Làm chủ cấu trúc bài viết nhượng bộ, làm tăng độ sâu sắc cho tiêu chí Task Response.
  - *Tiêu chí hoàn thành:* Bài luận hoàn chỉnh số 2 đạt trên 250 từ, sử dụng thành thạo cấu trúc nhượng bộ trong đoạn thân bài.
  - *Tiên quyết:* T19 (bắt buộc) | *Lịch dự kiến:* 2026-12-06 19:00–20:00 (60p)
- **T21 — Đánh giá chéo và hiệu đính 2 bài luận Agree/Disagree theo tiêu chí TR & CC** (`REVIEW`, 60 phút)
  - *Mô tả:* Phân tích, rà soát chi tiết 2 bài luận đã viết: kiểm tra tính logic giữa các câu, sự liên kết đoạn văn, vị trí của thesis statement và tính hợp lý của ví dụ minh họa.
  - *Mục tiêu học tập:* Nhận diện lỗi sai lập luận, lạc đề hoặc thiếu liên kết trong các bài viết thể hiện quan điểm.
  - *Tiêu chí hoàn thành:* Bản chỉnh sửa nâng cấp của 2 bài luận Opinion đạt chuẩn rubric Band 6.5 cho tiêu chí TR và CC.
  - *Tiên quyết:* T20 (bắt buộc) | *Lịch dự kiến:* 2026-12-07 19:00–20:00 (60p)

#### Chi tiết nội dung M5 (6 tasks)

- **T22 — Cấu trúc luận điểm dạng bài Discuss Both Views and Give Your Opinion** (`THEORY`, 60 phút)
  - *Mô tả:* Phân tích cách triển khai bài thảo luận 2 quan điểm: kỹ thuật trình bày quan điểm người khác một cách khách quan ở Body 1 và bảo vệ quan điểm cá nhân ở Body 2.
  - *Mục tiêu học tập:* Phân biệt rõ ràng giữa quan điểm khách quan và quan điểm cá nhân, xây dựng bài viết cân đối.
  - *Tiêu chí hoàn thành:* Lập dàn ý chi tiết và viết thử đoạn mở bài kèm Body 1 cho đề bài Discuss Both Views.
  - *Tiên quyết:* T21 (bắt buộc) | *Lịch dự kiến:* 2026-12-08 19:00–20:00 (60p)
- **T23 — Chiến lược ghép nối Nguyên nhân - Giải pháp cho dạng Causes/Problems & Solutions** (`THEORY`, 60 phút)
  - *Mô tả:* Học phương pháp ghép cặp logic 1-1 giữa nguyên nhân/vấn đề ở Body 1 với giải pháp trực tiếp tương ứng ở Body 2, tránh đưa ra giải pháp chung chung thiếu tính khả thi.
  - *Mục tiêu học tập:* Thiết lập liên kết nguyên nhân - giải pháp chặt chẽ và sử dụng ngôn ngữ đề xuất hành động học thuật.
  - *Tiêu chí hoàn thành:* Lập sơ đồ tư duy liên kết nguyên nhân - giải pháp cho 2 vấn đề xã hội phổ biến trong IELTS.
  - *Tiên quyết:* T22 (bắt buộc) | *Lịch dự kiến:* 2026-12-09 19:00–20:00 (60p)
- **T24 — Thực hành viết bài luận hoàn chỉnh dạng Discuss Both Views** (`PRACTICE`, 60 phút)
  - *Mô tả:* Viết bài luận hoàn chỉnh tối thiểu 250 từ cho đề bài thảo luận hai mặt, đảm bảo lập trường cá nhân được nêu rõ ở Introduction, Body 2 và Conclusion.
  - *Mục tiêu học tập:* Hoàn thiện bài viết Discussion cân bằng, mạch lạc với đầy đủ dẫn chứng và giải thích.
  - *Tiêu chí hoàn thành:* Bài viết hoàn chỉnh dạng Discussion Both Views đạt tối thiểu 250 từ với cấu trúc cân đối giữa 2 thân bài.
  - *Tiên quyết:* T23 (bắt buộc) | *Lịch dự kiến:* 2026-12-10 19:00–20:00 (60p)
- **T25 — Thực hành viết bài luận hoàn chỉnh dạng Problems & Solutions** (`PRACTICE`, 60 phút)
  - *Mô tả:* Viết bài luận giải quyết vấn đề xã hội (môi trường, giao thông, lối sống), tập trung vào sự khớp nối giữa các giải pháp của chính phủ, cá nhân với các vấn đề đã nêu.
  - *Mục tiêu học tập:* Viết bài luận Problems & Solutions giải quyết triệt để từng khía cạnh vấn đề mà đề bài đặt ra.
  - *Tiêu chí hoàn thành:* Bài viết hoàn chỉnh dạng Problems & Solutions đạt tối thiểu 250 từ với các cặp giải pháp cụ thể tương ứng.
  - *Tiên quyết:* T24 (bắt buộc) | *Lịch dự kiến:* 2026-12-11 19:00–20:00 (60p)
- **T26 — Luyện tập dạng bài Two-Part Question và kiểm soát Cohesion liên đoạn** (`PRACTICE`, 60 phút)
  - *Mô tả:* Xử lý dạng đề bài gồm 2 câu hỏi trực tiếp: phân bổ mỗi câu hỏi cho 1 đoạn thân bài riêng biệt và rèn luyện kỹ thuật dùng từ nối chuyển đoạn tương phản/hệ quả.
  - *Mục tiêu học tập:* Trả lời đầy đủ cả 2 vế của câu hỏi mà không bỏ sót ý, đảm bảo tính liên kết chặt chẽ giữa các đoạn văn.
  - *Tiêu chí hoàn thành:* Dàn ý chi tiết và 1 bài viết hoàn chỉnh cho đề Two-Part Question đạt chuẩn dung lượng.
  - *Tiên quyết:* T25 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 19:00–20:00 (60p)
- **T27 — Hiệu đính, đối chiếu từ vựng học thuật và tính mạch lạc cho Task 2** (`REVIEW`, 60 phút)
  - *Mô tả:* Rà soát lại toàn bộ các bài viết Task 2 thuộc Milestone 5: kiểm tra collocations học thuật, tính liên kết giữa các câu và tính nhất quán của đại từ thay thế.
  - *Mục tiêu học tập:* Tối ưu hóa tiêu chí Lexical Resource và Coherence & Cohesion cho các dạng bài thảo luận và giải pháp.
  - *Tiêu chí hoàn thành:* Bản tổng kết phân tích lỗi liên kết và danh sách 20 collocations học thuật theo chủ đề đã áp dụng.
  - *Tiên quyết:* T26 (bắt buộc) | *Lịch dự kiến:* 2026-12-13 19:00–20:00 (60p)

#### Chi tiết nội dung M6 (5 tasks)

- **T28 — Chiến lược phân bổ 60 phút phòng thi và Checklist kiểm soát lỗi sai** (`THEORY`, 60 phút)
  - *Mô tả:* Học quy tắc quản lý thời gian thi thực tế: 20 phút cho Task 1 (3p phân tích, 14p viết, 3p soát) và 40 phút cho Task 2 (5p dàn ý, 30p viết, 5p soát); xây dựng checklist rà soát lỗi chính tả, chia động từ, mạo từ.
  - *Mục tiêu học tập:* Làm chủ chiến lược phân bổ thời gian tối ưu cho cả 2 task và thiết lập quy trình kiểm tra lỗi nhanh.
  - *Tiêu chí hoàn thành:* Hoàn thiện bảng kế hoạch 60 phút phòng thi và bảng checklist kiểm tra 5 nhóm lỗi ngữ pháp thường gặp.
  - *Tiên quyết:* T27 (bắt buộc) | *Lịch dự kiến:* 2026-12-14 19:00–20:00 (60p)
- **T29 — Luyện viết Full Test 1 (Task 1 + Task 2) mô phỏng áp lực thời gian thực tế** (`PRACTICE`, 60 phút)
  - *Mô tả:* Thực hiện viết trọn vẹn 1 đề thi IELTS Academic Writing chính thức trong 60 phút liên tục: 1 bài Task 1 dữ liệu (tối thiểu 150 từ) và 1 bài Task 2 Opinion (tối thiểu 250 từ).
  - *Mục tiêu học tập:* Trải nghiệm áp lực thời gian thực tế và rèn luyện phản xạ hoàn thành bài đúng thời hạn quy định.
  - *Tiêu chí hoàn thành:* Bài viết hoàn chỉnh cả Task 1 và Task 2 được hoàn thành trong đúng 60 phút với đầy đủ số từ quy định.
  - *Tiên quyết:* T28 (bắt buộc) | *Lịch dự kiến:* 2026-12-15 19:00–20:00 (60p)
- **T30 — Áp dụng Checklist rà soát lỗi và tự đánh giá Full Test 1 theo Rubric 6.5** (`REVIEW`, 60 phút)
  - *Mô tả:* Dành thời gian rà soát chi tiết từng câu trong Full Test 1 bằng checklist: đối chiếu sự hòa hợp chủ - vị, mạo từ a/an/the, chính tả; tự chấm điểm theo 4 tiêu chí của Band 6.5.
  - *Mục tiêu học tập:* Thực hành tự đánh giá khách quan dựa trên Band Descriptors và phát hiện các lỗi sai ngữ pháp, từ vựng.
  - *Tiêu chí hoàn thành:* Biên bản tự chấm chi tiết kèm phân tích lỗi sai và đề xuất phương án cải thiện cho Full Test 1.
  - *Tiên quyết:* T29 (bắt buộc) | *Lịch dự kiến:* 2026-12-16 19:00–20:00 (60p)
- **T31 — Luyện viết Full Test 2 với dạng đề kết hợp dưới điều kiện phòng thi** (`PROJECT`, 60 phút)
  - *Mô tả:* Thực hiện bài thi thử lần 2 trong 60 phút với đề Task 1 dạng phi số liệu (Map/Process) và Task 2 dạng Discussion/Problem-Solution, áp dụng triệt để kỹ năng phân bổ thời gian.
  - *Mục tiêu học tập:* Kiểm chứng sự tiến bộ về tốc độ viết, tính mạch lạc và độ chuẩn xác ngữ pháp trên bộ đề tổng hợp.
  - *Tiêu chí hoàn thành:* Sản phẩm 2 bài viết Full Test 2 hoàn chỉnh trong 60 phút, không vi phạm lỗi quá giờ hoặc thiếu từ.
  - *Tiên quyết:* T30 (bắt buộc) | *Lịch dự kiến:* 2026-12-17 19:00–20:00 (60p)
- **T32 — Chẩn đoán tổng kết lỗi sai định kỳ và xây dựng cẩm nang cá nhân Band 6.5** (`REVIEW`, 60 phút)
  - *Mô tả:* Tổng kết toàn bộ các lỗi sai ghi nhận từ các bài viết, đánh giá mức độ đạt tiêu chí Band 6.5 trên cả 4 khía cạnh (TR/TA, CC, LR, GRA) và lập sổ tay ghi nhớ lỗi cá nhân.
  - *Mục tiêu học tập:* Hệ thống hóa toàn bộ kinh nghiệm luyện viết và xây dựng chiến lược duy trì phong độ làm bài vững chắc.
  - *Tiêu chí hoàn thành:* Bản cẩm nang cá nhân hoàn chỉnh bao gồm danh sách lỗi cần tránh, template mở/kết bài ưa thích và kế hoạch duy trì phong độ thi thực tế.
  - *Tiên quyết:* T31 (bắt buộc) | *Lịch dự kiến:* 2026-12-18 19:00–20:00 (60p)

---

## R-08 — IELTS Academic Writing Task 1 & Task 2 từ nền tảng

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `BEGINNER`
- **Mô tả mục tiêu:** Người mới bắt đầu luyện viết IELTS Academic mục tiêu 6.5: nắm cấu trúc câu học thuật, mô tả biểu đồ Task 1 (line, bar, table, process) và lập luận Task 2 (opinion, discussion, problem-solution) kèm tự chấm theo 4 tiêu chí.
- **Khung thời gian:** `2026-11-17` → `2026-12-31`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_A — Thứ 2–Thứ 6: 60 phút/ngày; Thứ 7 & CN: 90 phút/ngày
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE bao phủ toàn diện mục tiêu IELTS Academic Writing hướng tới band 6.5 từ nền tảng: bắt đầu từ ngữ pháp câu học thuật và 4 tiêu chí chấm thi, tiến tới kỹ thuật viết Task 1 (biểu đồ Line/Bar/Table và Process), phương pháp triển khai luận điểm PEEL cho Task 2 (Opinion, Discussion, Problem-Solution), và kết thúc bằng việc tích hợp viết đề hoàn chỉnh dưới áp lực 60 phút kèm năng lực tự đánh giá theo rubric.
- **Tổng quan cấu trúc:** 6 milestones | 31 tasks (PRACTICE: 11, PROJECT: 2, REVIEW: 6, THEORY: 12) | 30 dependencies | Tổng thời lượng: 2460 phút (41.0 giờ) | Đã xếp lịch: 31/31 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Nền tảng Ngữ pháp, Cấu trúc câu Học thuật và Bộ tiêu chí Chấm thi IELTS Writing (360 phút)
- **Mô tả:** Hiểu rõ 4 tiêu chí chấm thi IELTS Writing (TR/TA, CC, LR, GRA) và rèn luyện kỹ năng viết câu ghép, câu phức, câu bị động cùng mệnh đề quan hệ chuẩn phong cách học thuật.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Phân tích và giải thích được yêu cầu của 4 tiêu chí chấm thi (TR/TA, CC, LR, GRA) ở mức band 6.5.
  - `M1-O2`: M1-O2: Viết chính xác các mẫu câu phức, câu ghép, mệnh đề quan hệ và cấu trúc bị động không mắc lỗi ngữ pháp cơ bản.
  - `M1-O3`: M1-O3: Sử dụng các liên từ và từ nối học thuật (linking words) để liên kết ý mạch lạc, tránh lặp từ.
- **Tiêu chí hoàn thành Milestone:** Hoàn thành bài tập ngữ pháp viết lại 15 câu đơn thành câu phức học thuật và giải thích đúng yêu cầu đạt band 6.5 theo từng tiêu chí.
- **Khái niệm mở rộng (chưa có trong KB):** `ielts-writing-band-descriptors`, `academic-sentence-structures`, `cohesive-devices-academic`

#### M2. IELTS Writing Task 1: Báo cáo Biểu đồ Biến thiên & So sánh (Line, Bar, Table) (480 phút)
- **Mô tả:** Làm chủ bố cục chuẩn 4 đoạn của Task 1 (Introduction, Overview, Detail 1, Detail 2), kỹ thuật paraphrase mở bài, chọn lọc đặc điểm nổi bật cho Overview và phân tích số liệu biểu đồ Line, Bar, Table.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Paraphrase đề bài mở bài Task 1 chính xác bằng từ đồng nghĩa và biến đổi cấu trúc ngữ pháp.
  - `M2-O2`: M2-O2: Xác định và viết đoạn Tổng quan (Overview) nêu bật 2-3 xu hướng chính hoặc giá trị cực trị mà không đưa số liệu cụ thể.
  - `M2-O3`: M2-O3: Sử dụng chính xác từ vựng xu hướng tăng/giảm/dao động, giới từ chỉ số liệu (to, by, at) và viết hoàn chỉnh 2 đoạn thân bài so sánh số liệu.
- **Tiêu chí hoàn thành Milestone:** Viết hoàn chỉnh ít nhất 3 bài báo cáo Task 1 (1 Line graph, 1 Bar chart, 1 Table) đạt độ dài tối thiểu 150 từ trong vòng 20 phút mỗi bài, có Overview rõ ràng.
- **Khái niệm mở rộng (chưa có trong KB):** `ielts-task1-structure-paraphrase`, `ielts-task1-overview-writing`, `ielts-task1-trend-comparative-language`

#### M3. IELTS Writing Task 1: Dạng bài Quy trình (Process) & Bản đồ (Map) (300 phút)
- **Mô tả:** Nắm vững phương pháp phân tích và mô tả dạng bài quy trình sản xuất/tự nhiên (Process) sử dụng thể bị động, từ nối trình tự thời gian và kỹ năng mô tả sự thay đổi của bản đồ.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Xác định các giai đoạn, điểm bắt đầu và kết thúc của một quy trình tự nhiên hoặc nhân tạo.
  - `M3-O2`: M3-O2: Ứng dụng nhuần nhuyễn thể bị động và từ vựng chỉ thứ tự thời gian (subsequently, prior to, following this) để liên kết các bước.
  - `M3-O3`: M3-O3: Viết bài báo cáo dạng Process hoàn chỉnh đạt cấu trúc chuẩn học thuật.
- **Tiêu chí hoàn thành Milestone:** Viết hoàn chỉnh 2 bài Task 1 dạng Process (1 Man-made process và 1 Natural cycle) đạt từ 150-180 từ đúng cấu trúc và thì ngữ pháp.
- **Khái niệm mở rộng (chưa có trong KB):** `ielts-task1-process-diagrams`, `passive-voice-sequencing`

#### M4. IELTS Writing Task 2: Cấu trúc Đoạn văn, Kỹ thuật Phát triển Luận điểm (PEEL) & Dạng bài Opinion (480 phút)
- **Mô tả:** Làm quen với cấu trúc bài luận Task 2 (4 đoạn), phương pháp tư duy phản biện, kỹ thuật lập luận PEEL (Point, Explanation, Example, Link) và cách xử lý triệt để dạng bài Opinion (Agree or Disagree).
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Viết mở bài Task 2 gồm câu paraphrase đề bài và Thesis Statement nêu quan điểm rõ ràng.
  - `M4-O2`: M4-O2: Triển khai đoạn thân bài chặt chẽ theo mô hình PEEL với luận điểm rõ ràng, giải thích sâu và ví dụ thuyết phục.
  - `M4-O3`: M4-O3: Lập dàn ý và viết bài luận Opinion Essay hoàn chỉnh bảo đảm lập luận nhất quán từ mở bài đến kết bài.
- **Tiêu chí hoàn thành Milestone:** Hoàn thành 2 bài luận hoàn chỉnh dạng Agree/Disagree đạt tối thiểu 250 từ với luận điểm được phát triển đầy đủ theo mô hình PEEL.
- **Khái niệm mở rộng (chưa có trong KB):** `ielts-task2-essay-structure`, `peel-paragraph-development`, `ielts-task2-opinion-essay`

#### M5. IELTS Writing Task 2: Các dạng bài Discussion & Problem - Solution (480 phút)
- **Mô tả:** Phát triển kỹ năng xử lý dạng bài Discuss both views and give your opinion và Dạng bài Causes/Problems & Solutions/Effects; mở rộng vốn từ học thuật theo các chủ đề phổ biến (Education, Environment, Technology).
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M5-O1`: M5-O1: Phân biệt cách lập luận cân bằng giữa hai luồng quan điểm trong bài Discussion mà vẫn duy trì lập trường cá nhân.
  - `M5-O2`: M5-O2: Xây dựng mối liên kết logic trực tiếp giữa nguyên nhân (causes) và giải pháp đề xuất (solutions) trong dạng bài Problem-Solution.
  - `M5-O3`: M5-O3: Áp dụng từ vựng theo chủ đề (collocations/idiomatic expressions học thuật) phù hợp ngữ cảnh.
- **Tiêu chí hoàn thành Milestone:** Viết hoàn chỉnh 1 bài Discussion Essay và 1 bài Problem-Solution Essay đạt từ 250-280 từ, phân bổ thời gian trong vòng 40 phút mỗi bài.
- **Khái niệm mở rộng (chưa có trong KB):** `ielts-task2-discussion-essay`, `ielts-task2-problem-solution-essay`, `topic-related-vocabulary-ielts`

#### M6. Tích hợp Thực chiến Luyện đề Task 1 & 2 Dưới Áp lực Thời gian & Tự đánh giá theo Band Descriptors (360 phút)
- **Mô tả:** Luyện tập viết song song cả Task 1 và Task 2 trong khung thời gian chuẩn 60 phút, thực hành quy trình tự rà soát lỗi ngữ pháp/chính tả và đánh giá bài viết theo 4 tiêu chí của giám khảo.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M6-O1`: M6-O1: Quản lý thời gian hiệu quả: phân bổ chính xác 20 phút cho Task 1 và 40 phút cho Task 2.
  - `M6-O2`: M6-O2: Thực hiện quy trình rà soát và sửa lỗi (proofreading) trong 3-5 phút cuối để khắc phục lỗi ngữ pháp, dấu câu và lỗi chính tả.
  - `M6-O3`: M6-O3: Tự chấm điểm và chỉ ra điểm cần cải thiện của bài viết dựa trên bộ tiêu chí chấm thi IELTS Writing Band Descriptors.
- **Tiêu chí hoàn thành Milestone:** Hoàn thành 2 đề thi thử trọn vẹn (gồm cả Task 1 và Task 2) trong đúng 60 phút mỗi đề kèm bảng tự đánh giá chi tiết theo 4 tiêu chí đạt mức tương đương band 6.5.
- **Khái niệm mở rộng (chưa có trong KB):** `ielts-writing-time-management`, `self-assessment-rubrics-ielts`, `proofreading-strategies`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Nghiên cứu bộ tiêu chí chấm thi IELTS Writing Band Descriptors | M1 | `THEORY` | 60 phút | 2026-11-17 19:00–20:00 (60p) | M1-O1 | Không |
| **T2**: Học ngữ pháp câu phức, câu ghép và mệnh đề quan hệ học thuật | M1 | `THEORY` | 60 phút | 2026-11-18 19:00–20:00 (60p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Lý thuyết từ nối và liên kết câu học thuật (Cohesive Devices) | M1 | `THEORY` | 60 phút | 2026-11-19 19:00–20:00 (60p) | M1-O3 | T2 (bắt buộc) |
| **T4**: Luyện tập chuyển đổi câu đơn thành câu phức và ghép nối mạch lạc | M1 | `PRACTICE` | 90 phút | 2026-11-20 19:00–19:45 (45p); 2026-11-21 19:00–19:45 (45p) | M1-O2, M1-O3 | T3 (bắt buộc) |
| **T5**: Đánh giá và tổng kết nền tảng ngữ pháp câu học thuật | M1 | `REVIEW` | 90 phút | 2026-11-21 19:45–20:30 (45p); 2026-11-22 19:00–19:45 (45p) | M1-O1, M1-O2 | T4 (bắt buộc) |
| **T6**: Kỹ thuật phân tích đề bài và viết mở bài Paraphrase cho Task 1 | M2 | `THEORY` | 60 phút | 2026-11-23 19:00–20:00 (60p) | M2-O1 | T5 (bắt buộc) |
| **T7**: Phương pháp xác định và viết đoạn Tổng quan (Overview) | M2 | `THEORY` | 60 phút | 2026-11-24 19:00–20:00 (60p) | M2-O2 | T6 (bắt buộc) |
| **T8**: Từ vựng mô tả xu hướng, so sánh và giới từ số liệu | M2 | `THEORY` | 60 phút | 2026-11-25 19:00–20:00 (60p) | M2-O3 | T7 (bắt buộc) |
| **T9**: Thực hành viết thân bài phân tích số liệu cho Line Graph và Bar Chart | M2 | `PRACTICE` | 90 phút | 2026-11-26 19:00–19:45 (45p); 2026-11-27 19:00–19:45 (45p) | M2-O3 | T8 (bắt buộc) |
| **T10**: Luyện viết hoàn chỉnh bài báo cáo Table và ôn tập Task 1 | M2 | `PRACTICE` | 90 phút | 2026-11-28 19:00–19:45 (45p); 2026-11-28 19:45–20:30 (45p) | M2-O1, M2-O2, M2-O3 | T9 (bắt buộc) |
| **T11**: Đánh giá và tinh chỉnh bài viết báo cáo biến thiên & so sánh | M2 | `REVIEW` | 120 phút | 2026-11-29 19:00–20:00 (60p); 2026-11-30 19:00–20:00 (60p) | M2-O1, M2-O2, M2-O3 | T10 (bắt buộc) |
| **T12**: Cấu trúc bài viết và từ vựng chỉ trình tự cho dạng Process | M3 | `THEORY` | 60 phút | 2026-12-01 19:00–20:00 (60p) | M3-O1, M3-O2 | T11 (bắt buộc) |
| **T13**: Thực hành viết bài quy trình sản xuất nhân tạo (Man-made Process) | M3 | `PRACTICE` | 90 phút | 2026-12-02 19:00–19:45 (45p); 2026-12-03 19:00–19:45 (45p) | M3-O2, M3-O3 | T12 (bắt buộc) |
| **T14**: Thực hành viết quy trình tự nhiên và tổng kết dạng Process/Map | M3 | `PRACTICE` | 90 phút | 2026-12-04 19:00–19:45 (45p); 2026-12-05 19:00–19:45 (45p) | M3-O1, M3-O3 | T13 (bắt buộc) |
| **T15**: Rà soát và củng cố phương pháp làm bài Task 1 dạng phi số liệu | M3 | `REVIEW` | 60 phút | 2026-12-06 19:00–20:00 (60p) | M3-O1, M3-O2, M3-O3 | T14 (bắt buộc) |
| **T16**: Cấu trúc tổng thể bài luận Task 2 và kỹ thuật viết Mở bài - Kết bài | M4 | `THEORY` | 60 phút | 2026-12-07 19:00–20:00 (60p) | M4-O1 | T15 (bắt buộc) |
| **T17**: Kỹ thuật phát triển luận điểm thân bài theo mô hình PEEL | M4 | `THEORY` | 60 phút | 2026-12-08 19:00–20:00 (60p) | M4-O2 | T16 (bắt buộc) |
| **T18**: Thực hành triển khai đoạn văn PEEL hoàn chỉnh cho dạng Opinion | M4 | `PRACTICE` | 90 phút | 2026-12-09 19:00–19:45 (45p); 2026-12-10 19:00–19:45 (45p) | M4-O2 | T17 (bắt buộc) |
| **T19**: Thực hành viết bài luận Opinion Essay hoàn chỉnh (Bài số 1) | M4 | `PRACTICE` | 90 phút | 2026-12-11 19:00–19:45 (45p); 2026-12-12 19:00–19:45 (45p) | M4-O1, M4-O3 | T18 (bắt buộc) |
| **T20**: Luyện viết bài luận Opinion Essay thứ hai và kiểm tra tính nhất quán | M4 | `PRACTICE` | 90 phút | 2026-12-12 19:45–20:30 (45p); 2026-12-13 19:00–19:45 (45p) | M4-O2, M4-O3 | T19 (bắt buộc) |
| **T21**: Đánh giá, sửa lỗi và đúc kết cấu trúc bài luận Opinion | M4 | `REVIEW` | 90 phút | 2026-12-13 19:45–20:30 (45p); 2026-12-14 19:00–19:45 (45p) | M4-O1, M4-O2, M4-O3 | T20 (bắt buộc) |
| **T22**: Phương pháp lập luận dạng bài Discussion Both Views | M5 | `THEORY` | 60 phút | 2026-12-15 19:00–20:00 (60p) | M5-O1 | T21 (bắt buộc) |
| **T23**: Cấu trúc dạng bài Causes/Problems & Solutions và từ vựng chủ đề | M5 | `THEORY` | 60 phút | 2026-12-16 19:00–20:00 (60p) | M5-O2, M5-O3 | T22 (bắt buộc) |
| **T24**: Thực hành viết bài luận hoàn chỉnh dạng Discussion Both Views | M5 | `PRACTICE` | 90 phút | 2026-12-17 19:00–19:45 (45p); 2026-12-18 19:00–19:45 (45p) | M5-O1, M5-O3 | T23 (bắt buộc) |
| **T25**: Thực hành viết bài luận hoàn chỉnh dạng Problem - Solution | M5 | `PRACTICE` | 90 phút | 2026-12-19 19:00–19:45 (45p); 2026-12-19 19:45–20:30 (45p) | M5-O2, M5-O3 | T24 (bắt buộc) |
| **T26**: Dự án tổng hợp viết luận chuyên sâu đa dạng chủ đề Task 2 | M5 | `PROJECT` | 90 phút | 2026-12-20 19:00–19:45 (45p); 2026-12-20 19:45–20:30 (45p) | M5-O1, M5-O2, M5-O3 | T25 (bắt buộc) |
| **T27**: Rà soát và tổng kết chiến thuật viết các dạng bài Task 2 | M5 | `REVIEW` | 90 phút | 2026-12-21 19:00–19:45 (45p); 2026-12-22 19:00–19:45 (45p) | M5-O1, M5-O2, M5-O3 | T26 (bắt buộc) |
| **T28**: Chiến lược phân bổ thời gian và quy trình rà soát sửa lỗi (Proofreading) | M6 | `THEORY` | 60 phút | 2026-12-23 19:00–20:00 (60p) | M6-O1, M6-O2 | T27 (bắt buộc) |
| **T29**: Thi thử Mock Test 1 trọn vẹn Task 1 & Task 2 trong 60 phút | M6 | `PRACTICE` | 90 phút | 2026-12-24 19:00–19:45 (45p); 2026-12-25 19:00–19:45 (45p) | M6-O1, M6-O2 | T28 (bắt buộc) |
| **T30**: Thi thử Mock Test 2 và tự đánh giá toàn diện theo Band Descriptors | M6 | `PROJECT` | 120 phút | 2026-12-26 19:00–20:00 (60p); 2026-12-27 19:00–20:00 (60p) | M6-O1, M6-O2, M6-O3 | T29 (bắt buộc) |
| **T31**: Tổng kết lộ trình, phân tích điểm mạnh - điểm yếu và kế hoạch duy trì | M6 | `REVIEW` | 90 phút | 2026-12-28 19:00–19:45 (45p); 2026-12-29 19:00–19:45 (45p) | M6-O3 | T30 (bắt buộc) |

#### Chi tiết nội dung M1 (5 tasks)

- **T1 — Nghiên cứu bộ tiêu chí chấm thi IELTS Writing Band Descriptors** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu chi tiết 4 tiêu chí chấm thi: Task Achievement/Task Response (TA/TR), Coherence & Cohesion (CC), Lexical Resource (LR), và Grammatical Range & Accuracy (GRA) ở mức Band 6.5.
  - *Mục tiêu học tập:* Phân tích và hiểu rõ từng tiêu chí chấm điểm và sự khác biệt giữa band 6.0 và 6.5.
  - *Tiêu chí hoàn thành:* Tóm tắt ngắn gọn các đặc điểm cốt lõi cần đạt ở Band 6.5 cho cả 4 tiêu chí.
  - *Concepts:* `ielts-writing-band-descriptors`
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:00–20:00 (60p)
- **T2 — Học ngữ pháp câu phức, câu ghép và mệnh đề quan hệ học thuật** (`THEORY`, 60 phút)
  - *Mô tả:* Nắm vững lý thuyết về cấu trúc câu phức (complex sentences), câu ghép (compound sentences), câu bị động (passive voice) và mệnh đề quan hệ để ứng dụng vào văn phong học thuật.
  - *Mục tiêu học tập:* Nắm vững cách cấu tạo câu phức tạp chuẩn xác, tránh lỗi ngắt câu (run-on) hoặc câu thiếu vị ngữ (fragment).
  - *Tiêu chí hoàn thành:* Ghi chép các cấu trúc câu mẫu ứng dụng trong Writing.
  - *Concepts:* `academic-sentence-structures`
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-18 19:00–20:00 (60p)
- **T3 — Lý thuyết từ nối và liên kết câu học thuật (Cohesive Devices)** (`THEORY`, 60 phút)
  - *Mô tả:* Học cách sử dụng các liên từ chỉ nguyên nhân-kết quả, đối lập, bổ sung và thứ tự thời gian một cách tự nhiên, tránh lạm dụng máy móc.
  - *Mục tiêu học tập:* Phân biệt và sử dụng chính xác các liên từ học thuật phổ biến.
  - *Tiêu chí hoàn thành:* Lập danh mục từ nối học thuật phân loại theo chức năng diễn đạt.
  - *Concepts:* `cohesive-devices-academic`
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 19:00–20:00 (60p)
- **T4 — Luyện tập chuyển đổi câu đơn thành câu phức và ghép nối mạch lạc** (`PRACTICE`, 90 phút)
  - *Mô tả:* Thực hành viết lại 15 câu đơn thành câu phức học thuật sử dụng liên từ và mệnh đề quan hệ phù hợp.
  - *Mục tiêu học tập:* Áp dụng thành thạo cấu trúc câu phức và từ nối vào các câu văn thực tế.
  - *Tiêu chí hoàn thành:* Hoàn thành bài tập viết lại 15 câu đơn thành câu phức không mắc lỗi ngữ pháp cơ bản.
  - *Concepts:* `academic-sentence-structures`, `cohesive-devices-academic`
  - *Tiên quyết:* T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:00–19:45 (45p); 2026-11-21 19:00–19:45 (45p)
- **T5 — Đánh giá và tổng kết nền tảng ngữ pháp câu học thuật** (`REVIEW`, 90 phút)
  - *Mô tả:* Kiểm tra lại toàn bộ bài tập chuyển đổi câu, đối chiếu với tiêu chí GRA và CC của Band 6.5.
  - *Mục tiêu học tập:* Tự nhận diện và sửa lỗi ngữ pháp thường gặp trong câu phức.
  - *Tiêu chí hoàn thành:* Hoàn thiện bảng giải thích yêu cầu Band 6.5 và sửa toàn bộ lỗi ngữ pháp trong bài thực hành.
  - *Concepts:* `ielts-writing-band-descriptors`, `academic-sentence-structures`
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 19:45–20:30 (45p); 2026-11-22 19:00–19:45 (45p)

#### Chi tiết nội dung M2 (6 tasks)

- **T6 — Kỹ thuật phân tích đề bài và viết mở bài Paraphrase cho Task 1** (`THEORY`, 60 phút)
  - *Mô tả:* Học cách phân tích cấu trúc đề bài IELTS Writing Task 1 và phương pháp paraphrase câu đề bằng từ đồng nghĩa và biến đổi cấu trúc ngữ pháp.
  - *Mục tiêu học tập:* Nắm vững công thức viết mở bài cho dạng biểu đồ Line, Bar, Table.
  - *Tiêu chí hoàn thành:* Viết được 3 câu mở bài paraphrase chuẩn xác từ 3 đề mẫu.
  - *Concepts:* `ielts-task1-structure-paraphrase`
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:00–20:00 (60p)
- **T7 — Phương pháp xác định và viết đoạn Tổng quan (Overview)** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu nguyên tắc chọn lọc 2-3 xu hướng chính nổi bật nhất hoặc giá trị cao nhất/thấp nhất để viết Overview mà không nêu số liệu.
  - *Mục tiêu học tập:* Biết cách trích xuất đặc điểm chung lớn nhất của biểu đồ và cấu trúc đoạn Overview.
  - *Tiêu chí hoàn thành:* Viết được 3 đoạn Overview chuẩn mẫu cho 3 biểu đồ khác nhau.
  - *Concepts:* `ielts-task1-overview-writing`
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-24 19:00–20:00 (60p)
- **T8 — Từ vựng mô tả xu hướng, so sánh và giới từ số liệu** (`THEORY`, 60 phút)
  - *Mô tả:* Học hệ thống từ vựng miêu tả xu hướng biến thiên (increase, plunge, fluctuate...), cấu trúc so sánh hơn/nhất, và giới từ số liệu (at, to, by, with).
  - *Mục tiêu học tập:* Làm chủ từ vựng và cấu trúc số liệu chính xác trong thân bài Task 1.
  - *Tiêu chí hoàn thành:* Tổng hợp bảng từ vựng biến thiên số liệu kèm ví dụ minh họa.
  - *Concepts:* `ielts-task1-trend-comparative-language`
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:00–20:00 (60p)
- **T9 — Thực hành viết thân bài phân tích số liệu cho Line Graph và Bar Chart** (`PRACTICE`, 90 phút)
  - *Mô tả:* Áp dụng từ vựng xu hướng và cấu trúc so sánh để viết các đoạn thân bài Body 1 & 2 nhóm thông tin hợp lý.
  - *Mục tiêu học tập:* Viết các đoạn thân bài có chọn lọc số liệu trọng tâm và so sánh logic.
  - *Tiêu chí hoàn thành:* Hoàn thành phần thân bài cho 1 đề Line Graph và 1 đề Bar Chart.
  - *Concepts:* `ielts-task1-trend-comparative-language`
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-26 19:00–19:45 (45p); 2026-11-27 19:00–19:45 (45p)
- **T10 — Luyện viết hoàn chỉnh bài báo cáo Table và ôn tập Task 1** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết bài hoàn chỉnh dạng Table từ mở bài, overview đến 2 thân bài, sau đó rà soát đối chiếu tiêu chuẩn.
  - *Mục tiêu học tập:* Kết hợp nhuần nhuyễn paraphrase, overview và miêu tả số liệu bảng biểu.
  - *Tiêu chí hoàn thành:* Hoàn thành 1 bài viết trọn vẹn dạng Table tối thiểu 150 từ.
  - *Concepts:* `ielts-task1-structure-paraphrase`, `ielts-task1-overview-writing`, `ielts-task1-trend-comparative-language`
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 19:00–19:45 (45p); 2026-11-28 19:45–20:30 (45p)
- **T11 — Đánh giá và tinh chỉnh bài viết báo cáo biến thiên & so sánh** (`REVIEW`, 120 phút)
  - *Mô tả:* Rà soát lại 3 bài viết Task 1 (Line, Bar, Table), sửa lỗi diễn đạt số liệu và cải thiện tính mạch lạc.
  - *Mục tiêu học tập:* Đạt độ hoàn thiện cao cho các dạng bài đồ thị biến thiên và so sánh.
  - *Tiêu chí hoàn thành:* Bài viết đạt đủ yêu cầu độ dài từ 150 từ trở lên và phân bổ thời gian trong 20 phút.
  - *Concepts:* `ielts-task1-overview-writing`, `ielts-task1-trend-comparative-language`
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-11-29 19:00–20:00 (60p); 2026-11-30 19:00–20:00 (60p)

#### Chi tiết nội dung M3 (4 tasks)

- **T12 — Cấu trúc bài viết và từ vựng chỉ trình tự cho dạng Process** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu cấu trúc bài viết quy trình tự nhiên và nhân tạo, phân biệt thể bị động/chủ động và từ nối tuần tự (firstly, subsequently, following this).
  - *Mục tiêu học tập:* Hiểu rõ các bước phân tích sơ đồ quy trình và ngôn ngữ diễn đạt trình tự.
  - *Tiêu chí hoàn thành:* Lập sơ đồ phân tích các bước của 1 quy trình mẫu kèm từ nối tương ứng.
  - *Concepts:* `ielts-task1-process-diagrams`, `passive-voice-sequencing`
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-12-01 19:00–20:00 (60p)
- **T13 — Thực hành viết bài quy trình sản xuất nhân tạo (Man-made Process)** (`PRACTICE`, 90 phút)
  - *Mô tả:* Ứng dụng câu bị động và từ vựng trình tự để viết bài báo cáo hoàn chỉnh cho quy trình sản xuất công nghiệp.
  - *Mục tiêu học tập:* Sử dụng chính xác cấu trúc bị động để miêu tả các công đoạn nhân tạo.
  - *Tiêu chí hoàn thành:* Hoàn thành bài viết Man-made Process tối thiểu 150 từ.
  - *Concepts:* `ielts-task1-process-diagrams`, `passive-voice-sequencing`
  - *Tiên quyết:* T12 (bắt buộc) | *Lịch dự kiến:* 2026-12-02 19:00–19:45 (45p); 2026-12-03 19:00–19:45 (45p)
- **T14 — Thực hành viết quy trình tự nhiên và tổng kết dạng Process/Map** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết bài miêu tả vòng tuần hoàn tự nhiên (Natural Cycle), rà soát thì động từ hiện tại đơn và tính liên kết giữa các giai đoạn.
  - *Mục tiêu học tập:* Phân biệt cách viết quy trình tự nhiên so với nhân tạo và hoàn thiện kỹ năng.
  - *Tiêu chí hoàn thành:* Hoàn thành bài viết Natural Cycle từ 150-180 từ chuẩn cấu trúc.
  - *Concepts:* `ielts-task1-process-diagrams`, `passive-voice-sequencing`
  - *Tiên quyết:* T13 (bắt buộc) | *Lịch dự kiến:* 2026-12-04 19:00–19:45 (45p); 2026-12-05 19:00–19:45 (45p)
- **T15 — Rà soát và củng cố phương pháp làm bài Task 1 dạng phi số liệu** (`REVIEW`, 60 phút)
  - *Mô tả:* Đánh giá lại hai bài Process đã viết, chỉnh sửa liên từ chuyển tiếp và lỗi ngữ pháp thể bị động.
  - *Mục tiêu học tập:* Tự tin nhận diện và xử lý mọi dạng bài Process trong Task 1.
  - *Tiêu chí hoàn thành:* Bản sửa chi tiết của 2 bài viết Process đạt chuẩn Task Achievement.
  - *Concepts:* `ielts-task1-process-diagrams`
  - *Tiên quyết:* T14 (bắt buộc) | *Lịch dự kiến:* 2026-12-06 19:00–20:00 (60p)

#### Chi tiết nội dung M4 (6 tasks)

- **T16 — Cấu trúc tổng thể bài luận Task 2 và kỹ thuật viết Mở bài - Kết bài** (`THEORY`, 60 phút)
  - *Mô tả:* Nắm vững bố cục 4 đoạn chuẩn của Task 2, kỹ thuật paraphrase đề bài và xây dựng Thesis Statement rõ ràng, nhất quán.
  - *Mục tiêu học tập:* Biết cách đặt vấn đề và định hướng lập trường rõ ràng ngay từ mở bài.
  - *Tiêu chí hoàn thành:* Viết được 3 cặp Mở bài - Kết bài cho 3 đề Task 2 dạng Opinion.
  - *Concepts:* `ielts-task2-essay-structure`, `ielts-task2-opinion-essay`
  - *Tiên quyết:* T15 (bắt buộc) | *Lịch dự kiến:* 2026-12-07 19:00–20:00 (60p)
- **T17 — Kỹ thuật phát triển luận điểm thân bài theo mô hình PEEL** (`THEORY`, 60 phút)
  - *Mô tả:* Học cách xây dựng đoạn thân bài chuẩn: Point (Câu chủ đề), Explanation (Giải thích cơ chế), Example (Ví dụ chứng minh), Link (Câu liên kết kết luận).
  - *Mục tiêu học tập:* Làm chủ phương pháp đào sâu luận điểm tránh viết liệt kê hời hợt.
  - *Tiêu chí hoàn thành:* Lập dàn ý chi tiết 2 đoạn thân bài theo khung PEEL cho một chủ đề xã hội.
  - *Concepts:* `peel-paragraph-development`
  - *Tiên quyết:* T16 (bắt buộc) | *Lịch dự kiến:* 2026-12-08 19:00–20:00 (60p)
- **T18 — Thực hành triển khai đoạn văn PEEL hoàn chỉnh cho dạng Opinion** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết 2 đoạn thân bài hoàn chỉnh ứng dụng khung PEEL để bảo vệ quan điểm đồng ý hoặc không đồng ý.
  - *Mục tiêu học tập:* Áp dụng nhuần nhuyễn kỹ thuật PEEL để tạo nên đoạn văn thuyết phục và chặt chẽ.
  - *Tiêu chí hoàn thành:* Hoàn thành 2 đoạn thân bài có độ dài 90-100 từ mỗi đoạn với lập luận chặt chẽ.
  - *Concepts:* `peel-paragraph-development`, `ielts-task2-opinion-essay`
  - *Tiên quyết:* T17 (bắt buộc) | *Lịch dự kiến:* 2026-12-09 19:00–19:45 (45p); 2026-12-10 19:00–19:45 (45p)
- **T19 — Thực hành viết bài luận Opinion Essay hoàn chỉnh (Bài số 1)** (`PRACTICE`, 90 phút)
  - *Mô tả:* Lập dàn ý và viết hoàn chỉnh bài luận dạng Agree/Disagree từ mở bài đến kết bài, duy trì quan điểm rõ ràng.
  - *Mục tiêu học tập:* Tích hợp mở bài, thân bài PEEL và kết bài thành một bài luận hoàn chỉnh tối thiểu 250 từ.
  - *Tiêu chí hoàn thành:* Hoàn thành 1 bài essay Opinion hoàn chỉnh tối thiểu 250 từ.
  - *Concepts:* `ielts-task2-essay-structure`, `ielts-task2-opinion-essay`
  - *Tiên quyết:* T18 (bắt buộc) | *Lịch dự kiến:* 2026-12-11 19:00–19:45 (45p); 2026-12-12 19:00–19:45 (45p)
- **T20 — Luyện viết bài luận Opinion Essay thứ hai và kiểm tra tính nhất quán** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết bài luận Opinion hoàn chỉnh thứ hai với chủ đề mới, rà soát tính logic và lập trường xuyên suốt toàn bài.
  - *Mục tiêu học tập:* Củng cố tốc độ viết và khả năng phát triển lập luận nhất quán từ đầu đến cuối.
  - *Tiêu chí hoàn thành:* Hoàn thành bài essay Opinion thứ hai đạt độ dài tối thiểu 250 từ trong 45 phút.
  - *Concepts:* `peel-paragraph-development`, `ielts-task2-opinion-essay`
  - *Tiên quyết:* T19 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 19:45–20:30 (45p); 2026-12-13 19:00–19:45 (45p)
- **T21 — Đánh giá, sửa lỗi và đúc kết cấu trúc bài luận Opinion** (`REVIEW`, 90 phút)
  - *Mô tả:* So sánh 2 bài viết Opinion với tiêu chí Band Descriptors 6.5, rút kinh nghiệm về lỗi phát triển luận điểm.
  - *Mục tiêu học tập:* Nhận thức rõ các bẫy thường gặp trong dạng Opinion (thiếu lập trường, thiếu ví dụ).
  - *Tiêu chí hoàn thành:* Bài chữa hoàn thiện của 2 bài luận kèm ghi chú các cấu trúc cần cải thiện.
  - *Concepts:* `ielts-task2-essay-structure`, `peel-paragraph-development`
  - *Tiên quyết:* T20 (bắt buộc) | *Lịch dự kiến:* 2026-12-13 19:45–20:30 (45p); 2026-12-14 19:00–19:45 (45p)

#### Chi tiết nội dung M5 (6 tasks)

- **T22 — Phương pháp lập luận dạng bài Discussion Both Views** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu cấu trúc bài Discussion: cách trình bày khách quan cả hai mặt của vấn đề và lồng ghép ý kiến cá nhân hợp lý.
  - *Mục tiêu học tập:* Hiểu rõ sự khác biệt giữa Discussion và Opinion, cách duy trì tính cân bằng trong lập luận.
  - *Tiêu chí hoàn thành:* Lập dàn ý chi tiết cho 1 đề Discussion phân tích cả 2 góc nhìn.
  - *Concepts:* `ielts-task2-discussion-essay`
  - *Tiên quyết:* T21 (bắt buộc) | *Lịch dự kiến:* 2026-12-15 19:00–20:00 (60p)
- **T23 — Cấu trúc dạng bài Causes/Problems & Solutions và từ vựng chủ đề** (`THEORY`, 60 phút)
  - *Mô tả:* Nắm vững kỹ thuật ghép cặp logic giữa từng nguyên nhân với giải pháp xử lý tương ứng và học từ vựng/collocations theo chủ đề môi trường/giáo dục.
  - *Mục tiêu học tập:* Biết cách liên kết trực tiếp giải pháp với nguyên nhân đã nêu và nạp từ vựng chuyên sâu.
  - *Tiêu chí hoàn thành:* Lập bảng ghép cặp 2 nguyên nhân - 2 giải pháp kèm danh sách collocations học thuật liên quan.
  - *Concepts:* `ielts-task2-problem-solution-essay`, `topic-related-vocabulary-ielts`
  - *Tiên quyết:* T22 (bắt buộc) | *Lịch dự kiến:* 2026-12-16 19:00–20:00 (60p)
- **T24 — Thực hành viết bài luận hoàn chỉnh dạng Discussion Both Views** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết bài Discussion hoàn chỉnh trong vòng 40 phút, chú trọng phân tích công bằng cả 2 quan điểm và kết luận rõ quan điểm bản thân.
  - *Mục tiêu học tập:* Vận dụng kỹ năng phân tích đa chiều và áp dụng từ vựng học thuật theo ngữ cảnh.
  - *Tiêu chí hoàn thành:* Hoàn thành 1 bài Discussion Essay đạt 250-280 từ.
  - *Concepts:* `ielts-task2-discussion-essay`, `topic-related-vocabulary-ielts`
  - *Tiên quyết:* T23 (bắt buộc) | *Lịch dự kiến:* 2026-12-17 19:00–19:45 (45p); 2026-12-18 19:00–19:45 (45p)
- **T25 — Thực hành viết bài luận hoàn chỉnh dạng Problem - Solution** (`PRACTICE`, 90 phút)
  - *Mô tả:* Viết bài Problem - Solution hoàn chỉnh, bảo đảm mỗi giải pháp đưa ra giải quyết triệt để nguyên nhân đề cập trước đó.
  - *Mục tiêu học tập:* Xây dựng tính logic nhân - quả trực tiếp và làm giàu vốn từ vựng học thuật.
  - *Tiêu chí hoàn thành:* Hoàn thành 1 bài Problem-Solution Essay đạt 250-280 từ trong 40 phút.
  - *Concepts:* `ielts-task2-problem-solution-essay`, `topic-related-vocabulary-ielts`
  - *Tiên quyết:* T24 (bắt buộc) | *Lịch dự kiến:* 2026-12-19 19:00–19:45 (45p); 2026-12-19 19:45–20:30 (45p)
- **T26 — Dự án tổng hợp viết luận chuyên sâu đa dạng chủ đề Task 2** (`PROJECT`, 90 phút)
  - *Mô tả:* Thực hiện dự án phân tích đề, lập dàn ý nhanh và viết hoàn chỉnh bài luận tổng hợp vận dụng từ vựng nâng cao.
  - *Mục tiêu học tập:* Tự động hóa phản xạ lập dàn ý và viết luận cho các dạng bài Task 2 phức tạp.
  - *Tiêu chí hoàn thành:* Hoàn thành bài luận tổng hợp hoàn chỉnh kèm bảng từ vựng collocations đã sử dụng.
  - *Concepts:* `ielts-task2-discussion-essay`, `ielts-task2-problem-solution-essay`, `topic-related-vocabulary-ielts`
  - *Tiên quyết:* T25 (bắt buộc) | *Lịch dự kiến:* 2026-12-20 19:00–19:45 (45p); 2026-12-20 19:45–20:30 (45p)
- **T27 — Rà soát và tổng kết chiến thuật viết các dạng bài Task 2** (`REVIEW`, 90 phút)
  - *Mô tả:* So sánh các bài viết đã hoàn thành của Milestone 5, đánh giá độ mượt của từ nối và mức độ chính xác của từ vựng chủ đề.
  - *Mục tiêu học tập:* Cố định chiến lược làm bài Task 2 cho từng dạng câu hỏi cụ thể.
  - *Tiêu chí hoàn thành:* Bản tổng hợp các lỗi từ vựng/ngữ pháp cần tránh và checklist viết Task 2.
  - *Concepts:* `topic-related-vocabulary-ielts`
  - *Tiên quyết:* T26 (bắt buộc) | *Lịch dự kiến:* 2026-12-21 19:00–19:45 (45p); 2026-12-22 19:00–19:45 (45p)

#### Chi tiết nội dung M6 (4 tasks)

- **T28 — Chiến lược phân bổ thời gian và quy trình rà soát sửa lỗi (Proofreading)** (`THEORY`, 60 phút)
  - *Mô tả:* Học kỹ năng quản lý 60 phút thi viết (20m Task 1, 40m Task 2) và quy trình 3-5 phút cuối để rà soát lỗi ngữ pháp, chính tả, dấu câu.
  - *Mục tiêu học tập:* Nắm vững kỹ năng phân chia thời gian làm bài thi và checklist rà soát lỗi nhanh.
  - *Tiêu chí hoàn thành:* Bảng checklist proofreading 10 điểm cần kiểm tra trước khi nộp bài.
  - *Concepts:* `ielts-writing-time-management`, `proofreading-strategies`
  - *Tiên quyết:* T27 (bắt buộc) | *Lịch dự kiến:* 2026-12-23 19:00–20:00 (60p)
- **T29 — Thi thử Mock Test 1 trọn vẹn Task 1 & Task 2 trong 60 phút** (`PRACTICE`, 90 phút)
  - *Mô tả:* Mô phỏng điều kiện phòng thi thực tế: làm 1 đề Task 1 và 1 đề Task 2 liên tục trong đúng 60 phút, dành 3 phút cuối proofreading.
  - *Mục tiêu học tập:* Rèn luyện khả năng kiểm soát áp lực thời gian và độ dài bài viết thực tế.
  - *Tiêu chí hoàn thành:* Hoàn thành đủ 2 bài Task 1 và Task 2 đúng mốc thời gian 60 phút quy định.
  - *Concepts:* `ielts-writing-time-management`, `proofreading-strategies`
  - *Tiên quyết:* T28 (bắt buộc) | *Lịch dự kiến:* 2026-12-24 19:00–19:45 (45p); 2026-12-25 19:00–19:45 (45p)
- **T30 — Thi thử Mock Test 2 và tự đánh giá toàn diện theo Band Descriptors** (`PROJECT`, 120 phút)
  - *Mô tả:* Làm bài thi thử trọn vẹn lần 2 trong 60 phút, sau đó sử dụng bộ tiêu chí Band Descriptors chấm điểm chi tiết và chỉ ra điểm cần cải thiện.
  - *Mục tiêu học tập:* Đạt độ ổn định về thời gian thi và thành thạo năng lực tự đánh giá bài viết đạt chuẩn 6.5.
  - *Tiêu chí hoàn thành:* Hoàn thành 2 bài thi Task 1 và Task 2 kèm bảng đánh giá tự chấm 4 tiêu chí đạt mức tương đương 6.5.
  - *Concepts:* `ielts-writing-time-management`, `self-assessment-rubrics-ielts`, `proofreading-strategies`
  - *Tiên quyết:* T29 (bắt buộc) | *Lịch dự kiến:* 2026-12-26 19:00–20:00 (60p); 2026-12-27 19:00–20:00 (60p)
- **T31 — Tổng kết lộ trình, phân tích điểm mạnh - điểm yếu và kế hoạch duy trì** (`REVIEW`, 90 phút)
  - *Mô tả:* Phân tích kết quả của cả hai bài thi thử, tổng hợp các điểm số theo từng tiêu chí chấm thi và hoàn thiện hồ sơ tự đánh giá.
  - *Mục tiêu học tập:* Hệ thống hóa toàn bộ kiến thức và kỹ năng viết đã tích lũy trong toàn bộ lộ trình.
  - *Tiêu chí hoàn thành:* Báo cáo tổng kết năng lực hoàn thiện xác nhận đạt mục tiêu đầu ra Band 6.5.
  - *Concepts:* `self-assessment-rubrics-ielts`
  - *Tiên quyết:* T30 (bắt buộc) | *Lịch dự kiến:* 2026-12-28 19:00–19:45 (45p); 2026-12-29 19:00–19:45 (45p)

---

## R-09 — Data Engineering thực chiến với Apache Airflow & dbt

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Xây dựng pipeline ELT hiện đại: thiết kế DAG Airflow idempotent (XCom, TaskFlow API, retry/SLA), mô hình hóa dữ liệu staging/mart với dbt (tests, snapshots, incremental models) và kiểm soát chất lượng dữ liệu.
- **Khung thời gian:** `2026-11-17` → `2026-12-22`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_B — Thứ 2, Thứ 4, Thứ 6: 19:30–21:00 (90 phút); Thứ 7: 09:00–12:00 (180 phút)
- **Tóm tắt phạm vi lộ trình:** Lộ trình bao phủ toàn diện toàn bộ mục tiêu Data Engineering thực chiến với Apache Airflow và dbt theo chiến lược FULL_SCOPE. Lộ trình gồm 5 cột mốc tuần tự: từ kiến trúc ELT/TaskFlow API/idempotency trên Airflow, phân tầng mô hình hóa dữ liệu (Staging/Marts) trên dbt, đến các kỹ thuật nâng cao (Incremental, Snapshots SCD2, Data Quality Testing), và hợp nhất điều phối toàn diện qua Astronomer Cosmos kèm hệ thống Quality Gates.
- **Tổng quan cấu trúc:** 5 milestones | 26 tasks (PRACTICE: 15, PROJECT: 5, THEORY: 6) | 25 dependencies | Tổng thời lượng: 1560 phút (26.0 giờ) | Đã xếp lịch: 26/26 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Kiến trúc ELT & Thiết kế DAG Airflow Hiện Đại với TaskFlow API (240 phút)
- **Mô tả:** Nắm vững nguyên lý Data Pipeline ELT, thiết lập Apache Airflow, triển khai DAG bằng TaskFlow API (@task, @dag), trao đổi dữ liệu qua XCom an toàn và cấu hình chiến lược Retry, SLA.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Khởi tạo và thiết lập môi trường phát triển Apache Airflow với Docker/Astronomer CLI
  - `M1-O2`: M1-O2: Xây dựng DAG chuẩn theo cú pháp TaskFlow API (@dag, @task) kết hợp type hinting
  - `M1-O3`: M1-O3: Sử dụng XCom an toàn với backend storage và xử lý metadata trung gian giữa các task
  - `M1-O4`: M1-O4: Thiết lập cơ chế Retry, Execution Timeout, SLA Miss Alerting và Trigger Rules cho pipeline
- **Tiêu chí hoàn thành Milestone:** Triển khai hoàn chỉnh DAG Airflow dùng TaskFlow API thực hiện extract/load dữ liệu mẫu, cấu hình retry logic và kích hoạt cảnh báo SLA thành công.
- **Khái niệm nền tảng:** `sql-relational-modeling`
- **Khái niệm mở rộng (chưa có trong KB):** `airflow-taskflow-api`, `airflow-dag-architecture`, `airflow-xcom-storage`, `airflow-retry-sla-mechanisms`

#### M2. Bảo đảm Tính Lũy Đẳng (Idempotency) & Dynamic Task Mapping trong Airflow (300 phút)
- **Mô tả:** Thiết kế DAG Airflow có tính lũy đẳng (Idempotent), xử lý an toàn với Execution Date, Catchup, Backfilling và mở rộng quy mô xử lý bằng Dynamic Task Mapping.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Áp dụng nguyên lý Idempotency trong pipeline: upsert, partition overwrites và dọn dẹp state trung gian
  - `M2-O2`: M2-O2: Cấu hình và kiểm soát Backfill, catchup parameter cùng Data Interval (logical_date)
  - `M2-O3`: M2-O3: Triển khai Dynamic Task Mapping (.expand(), .partial()) để phân tải xử lý nhiều phân vùng dữ liệu đồng thời
  - `M2-O4`: M2-O4: Vận hành ExternalTaskSensor và Custom Sensors để đồng bộ luồng dữ liệu liên DAG
- **Tiêu chí hoàn thành Milestone:** DAG có khả năng chạy lại (rerun) bất kỳ khoảng thời gian (logical_date) nào mà không gây trùng lặp dữ liệu và tự động sinh task động dựa trên danh sách phân vùng.
- **Khái niệm mở rộng (chưa có trong KB):** `data-pipeline-idempotency`, `airflow-backfill-catchup`, `airflow-dynamic-task-mapping`, `airflow-sensors-interdag-dependencies`

#### M3. Mô Hình Hóa Dữ Liệu Tầng Staging & Data Marts với dbt (300 phút)
- **Mô tả:** Khởi tạo dự án dbt, cấu hình connection tới Data Warehouse, tổ chức phân tầng mô hình (Sources, Staging, Intermediate, Dimension/Fact Marts) và xây dựng tài liệu hóa tự động.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Cấu hình dbt project (dbt_project.yml, profiles.yml) kết nối với Data Warehouse (PostgreSQL/Snowflake/BigQuery)
  - `M3-O2`: M3-O2: Khai báo Sources và xây dựng tầng Staging chuẩn hóa kiểu dữ liệu, alias và làm sạch dữ liệu ban đầu
  - `M3-O3`: M3-O3: Xây dựng các Data Mart theo mô hình chiều Kimball (Fact & Dimension tables) ở tầng intermediate và mart
  - `M3-O4`: M3-O4: Tận dụng Jinja, dbt Macros và Ref function để quản lý phụ thuộc (Lineage DAG) và sinh tài liệu (dbt docs)
- **Tiêu chí hoàn thành Milestone:** Build thành công cây Lineage hoàn chỉnh trên dbt bao gồm sources, staging views và mart tables/mviews; xuất và kiểm tra được dbt docs.
- **Khái niệm nền tảng:** `sql-relational-modeling`
- **Khái niệm mở rộng (chưa có trong KB):** `dbt-project-structure`, `dbt-kimball-dimensional-modeling`, `dbt-staging-mart-design`, `dbt-jinja-macros-lineage`

#### M4. Kỹ Thuật Nâng Cao dbt: Incremental Models, Snapshots & Data Quality Testing (360 phút)
- **Mô tả:** Tối ưu hiệu năng chuyển đổi dữ liệu lớn với Incremental Models, theo dõi lịch sử thay đổi (SCD Type 2) bằng Snapshots, và xây dựng hàng rào kiểm soát chất lượng dữ liệu tự động.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Thiết kế và tối ưu Incremental Models với các chiến lược merge, delete+insert, và microbatch
  - `M4-O2`: M4-O2: Triển khai dbt Snapshots để nắm bắt Slowly Changing Dimension (SCD Type 2) dựa trên timestamp/check strategy
  - `M4-O3`: M4-O3: Cài đặt Generic Tests (unique, not_null, accepted_values, relationships) và Singular Custom SQL Tests
  - `M4-O4`: M4-O4: Tích hợp gói dbt-expectations hoặc elementary để giám sát Data Quality và bất thường schema
- **Tiêu chí hoàn thành Milestone:** Viết và chạy thành công mô hình incremental xử lý delta data, snapshot ghi nhận lịch sử cập nhật bản ghi, và 100% tests kiểm tra tính toàn vẹn dữ liệu vượt qua mà không có cảnh báo nghiêm trọng.
- **Khái niệm nền tảng:** `sql-relational-modeling`
- **Khái niệm mở rộng (chưa có trong KB):** `dbt-incremental-strategies`, `dbt-snapshots-scd2`, `dbt-data-quality-testing`, `dbt-expectations-monitoring`

#### M5. Tích Hợp Orchestration End-to-End: Airflow Điều Phối dbt & Vận Hành Pipeline (360 phút)
- **Mô tả:** Hợp nhất Airflow và dbt thành một hệ thống ELT hoàn chỉnh sử dụng Cosmos/Astronomer, thiết lập Quality Gates, cảnh báo tự động khi lỗi và thực hành triển khai thực tế.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M5-O1`: M5-O1: Tích hợp dbt project vào Airflow DAG thông qua Cosmos (Render dbt models thành các Airflow tasks)
  - `M5-O2`: M5-O2: Xây dựng pipeline ELT khép kín: Ingestion -> Airflow Task -> dbt run -> dbt test -> Cảnh báo Slack/Discord
  - `M5-O3`: M5-O3: Thiết lập Data Quality Gate chặn dữ liệu xấu lan truyền sang báo cáo BI/downstream consumers
  - `M5-O4`: M5-O4: Viết kịch bản kiểm thử End-to-End (Integration test) và đóng gói môi trường triển khai thực tế
- **Tiêu chí hoàn thành Milestone:** Pipeline ELT hoàn chỉnh vận hành tự động: kích hoạt trích xuất dữ liệu, điều phối dbt transform và test tự động, gửi thông báo trạng thái kèm metric chất lượng dữ liệu.
- **Khái niệm mở rộng (chưa có trong KB):** `astronomer-cosmos-integration`, `elt-end-to-end-pipeline`, `data-quality-gates-alerting`, `production-data-ops`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Tổng quan Kiến trúc Airflow & Cú pháp TaskFlow API (@dag, @task) | M1 | `THEORY` | 60 phút | 2026-11-18 19:30–20:30 (60p) | M1-O1, M1-O2 | Không |
| **T2**: Thiết lập Môi trường Docker/Astronomer CLI & Viết DAG Đầu Tiên | M1 | `PRACTICE` | 60 phút | 2026-11-20 19:30–20:30 (60p) | M1-O1, M1-O2 | T1 (bắt buộc) |
| **T3**: Quản lý Dữ liệu Trung gian với XCom Backend | M1 | `PRACTICE` | 60 phút | 2026-11-21 09:00–10:00 (60p) | M1-O3 | T2 (bắt buộc) |
| **T4**: Thiết lập Retry Logic, SLA Alerting & Trigger Rules cho Pipeline | M1 | `PROJECT` | 60 phút | 2026-11-21 10:00–11:00 (60p) | M1-O4 | T3 (bắt buộc) |
| **T5**: Nguyên lý Idempotency, Logical Date & Chiến lược Backfill | M2 | `THEORY` | 60 phút | 2026-11-21 11:00–12:00 (60p) | M2-O1, M2-O2 | T4 (bắt buộc) |
| **T6**: Thực hành Upsert & Partition Overwrites Chống Trùng Lặp | M2 | `PRACTICE` | 60 phút | 2026-11-23 19:30–20:30 (60p) | M2-O1 | T5 (bắt buộc) |
| **T7**: Phân Tải Xử Lý Phân Vùng với Dynamic Task Mapping | M2 | `PRACTICE` | 60 phút | 2026-11-25 19:30–20:30 (60p) | M2-O3 | T6 (bắt buộc) |
| **T8**: Đồng Bộ Pipeline Liên DAG với ExternalTaskSensor | M2 | `PRACTICE` | 60 phút | 2026-11-27 19:30–20:30 (60p) | M2-O4 | T7 (bắt buộc) |
| **T9**: Xây Dựng DAG Idempotent Hoàn Chỉnh với Dynamic Mapping & Backfill | M2 | `PROJECT` | 60 phút | 2026-11-28 09:00–10:00 (60p) | M2-O1, M2-O2, M2-O3, M2-O4 | T8 (bắt buộc) |
| **T10**: Kiến Trúc dbt & Thiết Kế Tầng Staging Chuẩn Hóa | M3 | `THEORY` | 60 phút | 2026-11-28 10:00–11:00 (60p) | M3-O1, M3-O2 | T9 (bắt buộc) |
| **T11**: Khởi Tạo Project dbt & Xây Dựng Staging Models | M3 | `PRACTICE` | 60 phút | 2026-11-28 11:00–12:00 (60p) | M3-O1, M3-O2 | T10 (bắt buộc) |
| **T12**: Thiết Kế Data Mart theo Phương Pháp Kimball (Fact & Dim) | M3 | `THEORY` | 60 phút | 2026-11-30 19:30–20:30 (60p) | M3-O3 | T11 (bắt buộc) |
| **T13**: Xây Dựng Data Marts với Jinja Macros & Ref Function | M3 | `PRACTICE` | 60 phút | 2026-12-02 19:30–20:30 (60p) | M3-O3, M3-O4 | T12 (bắt buộc) |
| **T14**: Kiểm Soát Lineage DAG & Phát Hành Tài Liệu dbt Docs | M3 | `PROJECT` | 60 phút | 2026-12-04 19:30–20:30 (60p) | M3-O4 | T13 (bắt buộc) |
| **T15**: Lý Thuyết Incremental Models & SCD Type 2 Snapshots | M4 | `THEORY` | 60 phút | 2026-12-05 09:00–10:00 (60p) | M4-O1, M4-O2 | T14 (bắt buộc) |
| **T16**: Cấu Hình & Tối Ưu Incremental Models với is_incremental() | M4 | `PRACTICE` | 60 phút | 2026-12-05 10:00–11:00 (60p) | M4-O1 | T15 (bắt buộc) |
| **T17**: Thiết Lập dbt Snapshots Theo Dõi Lịch Sử SCD Type 2 | M4 | `PRACTICE` | 60 phút | 2026-12-05 11:00–12:00 (60p) | M4-O2 | T16 (bắt buộc) |
| **T18**: Cài Đặt Generic & Singular Data Quality Tests | M4 | `PRACTICE` | 60 phút | 2026-12-07 19:30–20:30 (60p) | M4-O3 | T17 (bắt buộc) |
| **T19**: Tích Hợp Gói dbt-expectations Giám Sát Dữ Liệu Nâng Cao | M4 | `PRACTICE` | 60 phút | 2026-12-09 19:30–20:30 (60p) | M4-O4 | T18 (bắt buộc) |
| **T20**: Tổng Hợp Vận Hành Suite Incremental, Snapshots & Data Quality | M4 | `PROJECT` | 60 phút | 2026-12-11 19:30–20:30 (60p) | M4-O1, M4-O2, M4-O3, M4-O4 | T19 (bắt buộc) |
| **T21**: Kiến Trúc Orchestration Airflow - dbt & Tổng Quan Cosmos | M5 | `THEORY` | 60 phút | 2026-12-12 09:00–10:00 (60p) | M5-O1, M5-O2 | T20 (bắt buộc) |
| **T22**: Tích Hợp dbt Project vào Airflow với Astronomer Cosmos | M5 | `PRACTICE` | 60 phút | 2026-12-12 10:00–11:00 (60p) | M5-O1 | T21 (bắt buộc) |
| **T23**: Xây Dựng Pipeline ELT Khép Kín & Alerting Tự Động | M5 | `PRACTICE` | 60 phút | 2026-12-12 11:00–12:00 (60p) | M5-O2 | T22 (bắt buộc) |
| **T24**: Thiết Lập Data Quality Gates Chặn Dữ Liệu Lỗi | M5 | `PRACTICE` | 60 phút | 2026-12-14 19:30–20:30 (60p) | M5-O3 | T23 (bắt buộc) |
| **T25**: Kiểm Thử Tích Hợp End-to-End (Integration Testing) | M5 | `PRACTICE` | 60 phút | 2026-12-16 19:30–20:30 (60p) | M5-O4 | T24 (bắt buộc) |
| **T26**: Đóng Gói & Vận Hành Pipeline ELT Sản Xuất Toàn Diện | M5 | `PROJECT` | 60 phút | 2026-12-18 19:30–20:30 (60p) | M5-O1, M5-O2, M5-O3, M5-O4 | T25 (bắt buộc) |

#### Chi tiết nội dung M1 (4 tasks)

- **T1 — Tổng quan Kiến trúc Airflow & Cú pháp TaskFlow API (@dag, @task)** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu kiến trúc thành phần của Apache Airflow (Webserver, Scheduler, Metadata Database, Executor) và cú pháp TaskFlow API kết hợp Python type hints.
  - *Mục tiêu học tập:* Nắm vững nguyên lý hoạt động của Airflow và cách khai báo DAG/Task bằng TaskFlow decorator.
  - *Tiêu chí hoàn thành:* Giải thích rõ vai trò các thành phần kiến trúc và viết được khung DAG mẫu dùng @dag và @task.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-18 19:30–20:30 (60p)
- **T2 — Thiết lập Môi trường Docker/Astronomer CLI & Viết DAG Đầu Tiên** (`PRACTICE`, 60 phút)
  - *Mô tả:* Khởi tạo môi trường phát triển Airflow cục bộ bằng Astro CLI/Docker Compose, cấu hình connection và triển khai DAG extract/load dữ liệu cơ bản.
  - *Mục tiêu học tập:* Cài đặt thành công cụm Airflow local và chạy thành công DAG TaskFlow API đầu tiên.
  - *Tiêu chí hoàn thành:* Giao diện Airflow UI chạy bình thường trên trình duyệt, DAG unpause và chạy thành công (state SUCCESS).
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-20 19:30–20:30 (60p)
- **T3 — Quản lý Dữ liệu Trung gian với XCom Backend** (`PRACTICE`, 60 phút)
  - *Mô tả:* Thực hành chia sẻ metadata và dữ liệu an toàn giữa các task bằng XCom, cấu hình Custom XCom Backend (nếu cần) và hạn chế serialize payload lớn.
  - *Mục tiêu học tập:* Làm chủ cơ chế truyền nhận dữ liệu TaskFlow ngầm định và khai thác XCom an toàn.
  - *Tiêu chí hoàn thành:* Task downstream nhận đúng giá trị trả về từ upstream task thông qua XCom mà không gây tràn bộ nhớ metadata db.
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 09:00–10:00 (60p)
- **T4 — Thiết lập Retry Logic, SLA Alerting & Trigger Rules cho Pipeline** (`PROJECT`, 60 phút)
  - *Mô tả:* Tích hợp tham số retries, retry_delay, execution_timeout, cấu hình trigger_rule linh hoạt và kích hoạt cảnh báo SLA miss khi task bị chậm.
  - *Mục tiêu học tập:* Hoàn thiện pipeline ELT mẫu với cơ chế phục hồi lỗi và giám sát thời gian chạy nghiêm ngặt.
  - *Tiêu chí hoàn thành:* Pipeline tự động retry khi task giả lập lỗi và bắn callback/alert khi thời gian chạy vượt ngưỡng SLA quy định.
  - *Tiên quyết:* T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 10:00–11:00 (60p)

#### Chi tiết nội dung M2 (5 tasks)

- **T5 — Nguyên lý Idempotency, Logical Date & Chiến lược Backfill** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu bản chất tính lũy đẳng trong kỹ thuật dữ liệu: khái niệm logical_date (data_interval_start/end), catchup, và nguyên tắc rerun không sinh bản ghi trùng.
  - *Mục tiêu học tập:* Hiểu rõ cơ chế thời gian thực thi của Airflow và cách thiết kế pipeline có khả năng chạy lại an toàn.
  - *Tiêu chí hoàn thành:* Trình bày được sự khác nhau giữa execution_date và start_date, cùng các kịch bản backfill an toàn.
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 11:00–12:00 (60p)
- **T6 — Thực hành Upsert & Partition Overwrites Chống Trùng Lặp** (`PRACTICE`, 60 phút)
  - *Mô tả:* Viết pipeline nạp dữ liệu theo phân vùng thời gian, áp dụng câu lệnh INSERT ON CONFLICT (UPSERT) hoặc ghi đè thư mục phân vùng để bảo đảm idempotency.
  - *Mục tiêu học tập:* Hiện thực hóa logic nạp dữ liệu lũy đẳng trên database đích.
  - *Tiêu chí hoàn thành:* Chạy lại DAG 3 lần liên tiếp cho cùng 1 logical_date, số lượng bản ghi trong database đích không tăng thêm và không trùng lặp.
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-23 19:30–20:30 (60p)
- **T7 — Phân Tải Xử Lý Phân Vùng với Dynamic Task Mapping** (`PRACTICE`, 60 phút)
  - *Mô tả:* Sử dụng cú pháp .expand() và .partial() của TaskFlow API để tự động sinh task instances động theo danh sách file hoặc phân vùng dữ liệu đầu vào.
  - *Mục tiêu học tập:* Làm chủ Dynamic Task Mapping để xử lý dữ liệu quy mô lớn theo lô phân tán.
  - *Tiêu chí hoàn thành:* DAG tự động ánh xạ mảng tham số động thành các task song song hiển thị đầy đủ trên Grid View.
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-25 19:30–20:30 (60p)
- **T8 — Đồng Bộ Pipeline Liên DAG với ExternalTaskSensor** (`PRACTICE`, 60 phút)
  - *Mô tả:* Cấu hình ExternalTaskSensor để theo dõi trạng thái hoàn thành của một DAG/task upstream khác, tránh xung đột phụ thuộc giữa các luồng dữ liệu.
  - *Mục tiêu học tập:* Thiết lập phụ thuộc liên pipeline (cross-DAG dependencies) bằng cảm biến trong Airflow.
  - *Tiêu chí hoàn thành:* DAG downstream chỉ chạy khi DAG upstream tương ứng kết thúc thành công; xử lý đúng timeout của sensor.
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-27 19:30–20:30 (60p)
- **T9 — Xây Dựng DAG Idempotent Hoàn Chỉnh với Dynamic Mapping & Backfill** (`PROJECT`, 60 phút)
  - *Mô tả:* Tích hợp toàn bộ kỹ thuật: nạp dữ liệu đa phân vùng bằng dynamic task mapping, kiểm soát logical_date và thực thi lệnh backfill lịch sử dữ liệu 30 ngày.
  - *Mục tiêu học tập:* Tạo pipeline hoàn chỉnh đáp ứng đầy đủ tiêu chuẩn bền vững, lũy đẳng và xử lý song song.
  - *Tiêu chí hoàn thành:* Chạy lệnh CLI `airflow dags backfill` cho khoảng thời gian quá khứ thành công 100%, dữ liệu được partition chính xác.
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 09:00–10:00 (60p)

#### Chi tiết nội dung M3 (5 tasks)

- **T10 — Kiến Trúc dbt & Thiết Kế Tầng Staging Chuẩn Hóa** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu triết lý Analytics Engineering với dbt, cấu trúc thư mục tiêu chuẩn, cách khai báo sources.yml và nguyên tắc thiết kế tầng staging (stg_).
  - *Mục tiêu học tập:* Hiểu kiến trúc phân tầng trong dbt và tiêu chuẩn thiết kế staging views.
  - *Tiêu chí hoàn thành:* Xác định rõ vai trò của dbt_project.yml, profiles.yml và quy ước đặt tên (naming conventions) chuẩn.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 10:00–11:00 (60p)
- **T11 — Khởi Tạo Project dbt & Xây Dựng Staging Models** (`PRACTICE`, 60 phút)
  - *Mô tả:* Khởi tạo dự án dbt, cấu hình kết nối DWH trong profiles.yml, định nghĩa sources và viết các staging view chuẩn hóa tên cột, kiểu dữ liệu và làm sạch null.
  - *Mục tiêu học tập:* Triển khai kết nối dbt tới Data Warehouse và tạo các staging view sạch sẽ từ raw tables.
  - *Tiêu chí hoàn thành:* Lệnh `dbt run --select staging` thực thi thành công, tạo các view trong schema staging trên database.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 11:00–12:00 (60p)
- **T12 — Thiết Kế Data Mart theo Phương Pháp Kimball (Fact & Dim)** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu mô hình hình sao (Star Schema), phân biệt Fact Tables và Dimension Tables, surrogate keys và phương thức liên kết dữ liệu nghiệp vụ.
  - *Mục tiêu học tập:* Nắm vững lý thuyết mô hình hóa dữ liệu Kimball để áp dụng vào tầng intermediate và mart trong dbt.
  - *Tiêu chí hoàn thành:* Vẽ được sơ đồ ERD Star Schema cho một nghiệp vụ cụ thể (orders, customers, products).
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-11-30 19:30–20:30 (60p)
- **T13 — Xây Dựng Data Marts với Jinja Macros & Ref Function** (`PRACTICE`, 60 phút)
  - *Mô tả:* Viết các model dim_* và fct_* sử dụng hàm {{ ref() }} để quản lý phụ thuộc, đồng thời viết macro Jinja tái sử dụng logic tính toán tiền tệ hoặc ngày tháng.
  - *Mục tiêu học tập:* Tạo các bảng Data Mart hoàn chỉnh và làm chủ Jinja templating trong dbt.
  - *Tiêu chí hoàn thành:* Lệnh `dbt run --select marts` sinh thành công các table fact và dimension với dữ liệu chính xác.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T12 (bắt buộc) | *Lịch dự kiến:* 2026-12-02 19:30–20:30 (60p)
- **T14 — Kiểm Soát Lineage DAG & Phát Hành Tài Liệu dbt Docs** (`PROJECT`, 60 phút)
  - *Mô tả:* Viết mô tả tài liệu (docs) cho models và columns trong file yml, sinh tài liệu bằng `dbt docs generate` và kiểm tra đồ thị Lineage DAG trực quan.
  - *Mục tiêu học tập:* Hoàn thiện tài liệu hóa dự án dbt và kiểm tra tính toàn vẹn của đồ thị phụ thuộc.
  - *Tiêu chí hoàn thành:* Cổng dbt docs server hiển thị đầy đủ sơ đồ Lineage từ Sources -> Staging -> Intermediate -> Marts.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T13 (bắt buộc) | *Lịch dự kiến:* 2026-12-04 19:30–20:30 (60p)

#### Chi tiết nội dung M4 (6 tasks)

- **T15 — Lý Thuyết Incremental Models & SCD Type 2 Snapshots** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu chiến lược xử lý dữ liệu gia tăng (merge, delete+insert, microbatch) và cơ chế ghi nhận lịch sử thay đổi Slowly Changing Dimension Type 2 bằng snapshots.
  - *Mục tiêu học tập:* Nắm vững nguyên lý tối ưu hóa tài nguyên qua incremental models và theo dõi biến động trạng thái với snapshots.
  - *Tiêu chí hoàn thành:* So sánh được ưu nhược điểm của chiến lược merge vs delete+insert và cơ chế check vs timestamp trong snapshot.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T14 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 09:00–10:00 (60p)
- **T16 — Cấu Hình & Tối Ưu Incremental Models với is_incremental()** (`PRACTICE`, 60 phút)
  - *Mô tả:* Chuyển đổi một mart table lớn thành incremental model bằng khối lệnh `{% if is_incremental() %}`, cấu hình `unique_key` và kiểm thử delta run.
  - *Mục tiêu học tập:* Hiện thực hóa mô hình dữ liệu gia tăng để giảm thời gian xử lý và tải query trên DWH.
  - *Tiêu chí hoàn thành:* Khi chạy lại `dbt run`, câu query chỉ quét các bản ghi mới phát sinh dựa trên cột `updated_at`.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T15 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 10:00–11:00 (60p)
- **T17 — Thiết Lập dbt Snapshots Theo Dõi Lịch Sử SCD Type 2** (`PRACTICE`, 60 phút)
  - *Mô tả:* Tạo snapshot file trong thư mục snapshots/, cấu hình chiến lược check hoặc timestamp trên bảng khách hàng/sản phẩm để ghi vết thay đổi theo thời gian.
  - *Mục tiêu học tập:* Sử dụng dbt snapshot để tự động tạo các cột dbt_valid_from, dbt_valid_to phục vụ phân tích lịch sử.
  - *Tiêu chí hoàn thành:* Lệnh `dbt snapshot` cập nhật đúng bản ghi cũ (đóng dbt_valid_to) và chèn bản ghi mới khi source table có update.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T16 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 11:00–12:00 (60p)
- **T18 — Cài Đặt Generic & Singular Data Quality Tests** (`PRACTICE`, 60 phút)
  - *Mô tả:* Khai báo các bộ kiểm tra tích hợp sẵn (unique, not_null, accepted_values, relationships) trong schema.yml và viết các truy vấn singular test SQL kiểm tra logic biên.
  - *Mục tiêu học tập:* Xây dựng hệ thống bài test tự động bảo vệ tính toàn vẹn dữ liệu ở cấp độ cột và nghiệp vụ.
  - *Tiêu chí hoàn thành:* Lệnh `dbt test` thực thi thành công, bắt được vi phạm dữ liệu giả lập và pass 100% khi dữ liệu sạch.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T17 (bắt buộc) | *Lịch dự kiến:* 2026-12-07 19:30–20:30 (60p)
- **T19 — Tích Hợp Gói dbt-expectations Giám Sát Dữ Liệu Nâng Cao** (`PRACTICE`, 60 phút)
  - *Mô tả:* Cài đặt package `calogica/dbt-expectations` qua packages.yml, triển khai kiểm tra phân phối dữ liệu, độ dài chuỗi, regex và schema drift.
  - *Mục tiêu học tập:* Áp dụng Great Expectations style assertions trực tiếp trong dbt project.
  - *Tiêu chí hoàn thành:* Chạy thành công ít nhất 3 expect tests (ví dụ: expect_column_values_to_match_regex, expect_table_row_count_to_be_between).
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T18 (bắt buộc) | *Lịch dự kiến:* 2026-12-09 19:30–20:30 (60p)
- **T20 — Tổng Hợp Vận Hành Suite Incremental, Snapshots & Data Quality** (`PROJECT`, 60 phút)
  - *Mô tả:* Tổ chức quy trình kiểm thử và cập nhật gia tăng hoàn chỉnh: chạy seed -> snapshot -> run incremental -> test toàn bộ pipeline.
  - *Mục tiêu học tập:* Tích hợp và kiểm chứng toàn diện các kỹ thuật dbt nâng cao trong một kịch bản dữ liệu thực tế.
  - *Tiêu chí hoàn thành:* Bộ test và run thực thi trơn tru mà không có lỗi nghiêm trọng; delta update phản ánh chính xác trên Data Mart.
  - *Concepts:* `sql-relational-modeling`
  - *Tiên quyết:* T19 (bắt buộc) | *Lịch dự kiến:* 2026-12-11 19:30–20:30 (60p)

#### Chi tiết nội dung M5 (6 tasks)

- **T21 — Kiến Trúc Orchestration Airflow - dbt & Tổng Quan Cosmos** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu kiến trúc tích hợp giữa Orchestrator (Airflow) và Transformation Engine (dbt). Tìm hiểu thư viện Astronomer Cosmos để render dbt models thành Airflow tasks tự nhiên.
  - *Mục tiêu học tập:* Hiểu ưu điểm của việc sử dụng Cosmos thay vì gọi lệnh `bash` hoặc `subprocess` truyền thống trong Airflow.
  - *Tiêu chí hoàn thành:* Phân tích được cách Cosmos parse manifest.json để tạo task group và dependency graph trên giao diện Airflow.
  - *Tiên quyết:* T20 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 09:00–10:00 (60p)
- **T22 — Tích Hợp dbt Project vào Airflow với Astronomer Cosmos** (`PRACTICE`, 60 phút)
  - *Mô tả:* Cài đặt astronomer-cosmos, cấu hình DbtTaskGroup/DbtDag trỏ đến dbt project, thiết lập ExecutionConfig và ProfileConfig trong Airflow environment.
  - *Mục tiêu học tập:* Biến dbt models và tests thành các Airflow task instances độc lập có thể retry từng model riêng lẻ.
  - *Tiêu chí hoàn thành:* Airflow UI hiển thị cây TaskGroup tương ứng với từng dbt model; thực hiện run model đơn lẻ thành công.
  - *Tiên quyết:* T21 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 10:00–11:00 (60p)
- **T23 — Xây Dựng Pipeline ELT Khép Kín & Alerting Tự Động** (`PRACTICE`, 60 phút)
  - *Mô tả:* Kết hợp task Ingestion dữ liệu từ API/File, kích hoạt Cosmos DbtTaskGroup chuyển hóa và gửi thông báo trạng thái (kèm metric) qua Slack/Discord webhook khi thất bại hoặc thành công.
  - *Mục tiêu học tập:* Hoàn thiện luồng ELT từ khâu trích xuất, nạp, chuyển hóa đến cảnh báo vận hành.
  - *Tiêu chí hoàn thành:* Pipeline chạy xuyên suốt từ Ingestion đến Transform; nhận được notification trên kênh chat khi test fail.
  - *Tiên quyết:* T22 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 11:00–12:00 (60p)
- **T24 — Thiết Lập Data Quality Gates Chặn Dữ Liệu Lỗi** (`PRACTICE`, 60 phút)
  - *Mô tả:* Thiết lập cơ chế Data Quality Gate: nếu bước `dbt test` không vượt qua, luồng thực thi lập tức dừng lại, ngăn chặn việc xuất bản bảng mart tới tầng BI/dashboard.
  - *Mục tiêu học tập:* Bảo vệ hệ thống báo cáo hạ nguồn khỏi dữ liệu sai sót hoặc bất thường schema.
  - *Tiêu chí hoàn thành:* Cố tình chèn dữ liệu vi phạm ràng buộc not_null/unique, verify rằng task xuất bản BI bị chặn hoàn toàn (state UPSTREAM_FAILED).
  - *Tiên quyết:* T23 (bắt buộc) | *Lịch dự kiến:* 2026-12-14 19:30–20:30 (60p)
- **T25 — Kiểm Thử Tích Hợp End-to-End (Integration Testing)** (`PRACTICE`, 60 phút)
  - *Mô tả:* Viết kịch bản kiểm thử tích hợp tự động (pytest) kiểm tra sự phối hợp giữa Airflow worker, Cosmos runner và Data Warehouse đích trong môi trường staging.
  - *Mục tiêu học tập:* Tự động hóa kiểm thử tích hợp pipeline trước khi đưa lên môi trường sản xuất.
  - *Tiêu chí hoàn thành:* Bộ test integration chạy qua CI/CD hoặc local script, trả về mã thoát 0 (All passed).
  - *Tiên quyết:* T24 (bắt buộc) | *Lịch dự kiến:* 2026-12-16 19:30–20:30 (60p)
- **T26 — Đóng Gói & Vận Hành Pipeline ELT Sản Xuất Toàn Diện** (`PROJECT`, 60 phút)
  - *Mô tả:* Đóng gói toàn bộ source code DAG, dbt project và cấu hình Docker. Triển khai pipeline ELT sản xuất mẫu, theo dõi log và xác nhận chất lượng dữ liệu cuối cùng.
  - *Mục tiêu học tập:* Làm chủ trọn vẹn vòng đời phát triển, triển khai và vận hành Data Pipeline chuẩn doanh nghiệp.
  - *Tiêu chí hoàn thành:* Pipeline ELT hoàn chỉnh vận hành tự động theo lịch trình, dữ liệu mart cập nhật chuẩn xác và Data Quality test vượt qua 100%.
  - *Tiên quyết:* T25 (bắt buộc) | *Lịch dự kiến:* 2026-12-18 19:30–20:30 (60p)

---

## R-10 — Thiết kế Hệ thống & Distributed Cache với Redis

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Nắm vững các chiến lược caching (Cache-Aside, Write-Through, Write-Behind), consistent hashing, phòng chống cache stampede/avalanche, eviction policies và triển khai cụm Redis phân tán có rate limiting trong 4 tuần.
- **Khung thời gian:** `2026-11-17` → `2026-12-15`
- **Thời lượng phiên học tối ưu:** 60 phút
- **Quỹ thời gian rảnh:** MODE_B — Thứ 3: 19:30–21:30 (120 phút); Thứ 5: 19:30–21:30 (120 phút); Thứ 7: 09:00–12:00 (180 phút)
- **Tóm tắt phạm vi lộ trình:** Lộ trình đầy đủ (FULL_SCOPE) kéo dài 4 tuần bao phủ toàn bộ các nội dung mục tiêu: từ chiến lược caching nâng cao, cơ chế phòng chống sự cố cache quy mô lớn, thuật toán băm nhất quán (Consistent Hashing), đến thiết lập cụm phân tán và xây dựng giải pháp Rate Limiting nguyên tử bằng Redis Lua Script.
- **Tổng quan cấu trúc:** 4 milestones | 16 tasks (PRACTICE: 8, PROJECT: 1, REVIEW: 3, THEORY: 4) | 15 dependencies | Tổng thời lượng: 1440 phút (24.0 giờ) | Đã xếp lịch: 16/16 tasks

### Danh sách Milestones & Learning Outcomes

#### M1. Nền tảng Chiến lược Caching & Thuật toán Thu hồi Dữ liệu (Eviction Policies) (300 phút)
- **Mô tả:** Làm chủ các mẫu kiến trúc đọc/ghi bộ nhớ đệm (Cache-Aside, Write-Through, Write-Behind) và cơ chế giải phóng bộ nhớ khi đạt ngưỡng (LRU, LFU, TTL) trong Redis.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M1-O1`: M1-O1: Phân tích ưu/nhược điểm và trường hợp sử dụng của Cache-Aside, Write-Through, Write-Behind và Write-Around.
  - `M1-O2`: M1-O2: Cấu hình và so sánh hành vi các chính sách thu hồi bộ nhớ (maxmemory-policy: allkeys-lru, volatile-lru, allkeys-lfu, volatile-ttl) trong Redis.
  - `M1-O3`: M1-O3: Triển khai ứng dụng mẫu tích hợp mẫu Cache-Aside và Write-Behind với cơ chế ghi nhận bất đồng bộ xuống cơ sở dữ liệu quan hệ.
- **Tiêu chí hoàn thành Milestone:** Xây dựng thành công ứng dụng demo mô phỏng Cache-Aside và Write-Behind, có bài kiểm tra tự động xác minh tính nhất quán dữ liệu và cơ chế eviction kích hoạt đúng khi bộ nhớ vượt ngưỡng maxmemory.
- **Khái niệm nền tảng:** `sys-caching-redis-queues`
- **Khái niệm mở rộng (chưa có trong KB):** `caching-patterns-write-through-write-behind`, `redis-eviction-policies`

#### M2. Phòng chống Rủi ro Bộ nhớ đệm Phân tán: Stampede, Avalanche và Penetration (360 phút)
- **Mô tả:** Nghiên cứu các mối đe dọa làm sập tầng cơ sở dữ liệu khi dùng cache quy mô lớn và thiết kế các giải pháp phòng vệ tương ứng.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M2-O1`: M2-O1: Nhận diện nguyên nhân và tác động của Cache Avalanche, Cache Stampede (Thundering Herd) và Cache Penetration.
  - `M2-O2`: M2-O2: Áp dụng kỹ thuật phân rã thời gian sống (Jittered TTL) và khóa phân tán (Distributed Mutex Locking) để ngăn chặn stampede.
  - `M2-O3`: M2-O3: Triển khai thuật toán Probabilistic Early Expiration (XFetch) và cấu trúc dữ liệu Bloom Filter trong Redis để lọc truy vấn không tồn tại.
- **Tiêu chí hoàn thành Milestone:** Thực hiện kịch bản kiểm thử tải (load testing) giả lập 5000 concurrent requests khi cache key hết hạn đồng thời, chứng minh cơ chế Mutex/Jitter giữ tỷ lệ DB hit dưới 5% và không xảy ra sụp đổ dây chuyền.
- **Khái niệm nền tảng:** `sys-caching-redis-queues`
- **Khái niệm mở rộng (chưa có trong KB):** `cache-stampede-mitigation`, `bloom-filter-cache-penetration`, `probabilistic-early-expiration`

#### M3. Kỹ thuật Phân vùng Dữ liệu & Băm Nhất quán (Consistent Hashing) (360 phút)
- **Mô tả:** Hiểu sâu lý thuyết phân mảnh dữ liệu phân tán, thuật toán vòng băm nhất quán, nút ảo (virtual nodes) và cơ chế phân phối 16,384 Hash Slots của Redis Cluster.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M3-O1`: M3-O1: Giải thích nguyên lý hoạt động của Consistent Hashing và lý do kỹ thuật chia dư (hash mod N) gây thảm họa tái phân phối dữ liệu.
  - `M3-O2`: M3-O2: Cài đặt cấu trúc vòng băm (Hash Ring) có hỗ trợ Virtual Nodes nhằm phân bổ tải đồng đều giữa các node.
  - `M3-O3`: M3-O3: Phân tích kiến trúc Hash Slots của Redis Cluster, cơ chế MOVED redirection và kỹ thuật Hash Tags để gom nhóm keys.
- **Tiêu chí hoàn thành Milestone:** Viết mã nguồn minh họa thuật toán Consistent Hashing với Virtual Nodes, đo lường tỷ lệ di chuyển keys khi thêm/bớt node đạt độ lệch dưới 10% so với mức phân phối lý thuyết.
- **Khái niệm mở rộng (chưa có trong KB):** `consistent-hashing-algorithm`, `redis-cluster-hash-slots`, `distributed-sharding`

#### M4. Thiết kế Triển khai Cụm Redis Phân tán & Distributed Rate Limiter (420 phút)
- **Mô tả:** Triển khai cụm Redis có tính sẵn sàng cao, kết hợp xây dựng middleware giới hạn tốc độ truy cập phân tán (Rate Limiting) bằng Redis và Lua script.
- **Chuẩn đầu ra (Learning Outcomes):**
  - `M4-O1`: M4-O1: Thiết lập mô hình Redis Cluster (hoặc Sentinel) đa node hỗ trợ sao lưu Master-Replica và cơ chế failover tự động.
  - `M4-O2`: M4-O2: Thiết kế và lập trình giải thuật Token Bucket và Sliding Window Counter sử dụng Redis Lua Script để đảm bảo tính nguyên tử (atomicity).
  - `M4-O3`: M4-O3: Đóng gói Rate Limiting Middleware tích hợp vào API Gateway hoặc dịch vụ backend, đo kiểm hiệu năng chịu tải phân tán.
- **Tiêu chí hoàn thành Milestone:** Triển khai hoàn chỉnh cụm Redis Cluster cục bộ (tối thiểu 3 masters, 3 replicas) kèm Rate Limiter middleware, vượt qua bài kiểm tra tải hạn chế chính xác số lượng request theo cấu hình mà không gây race condition.
- **Khái niệm mở rộng (chưa có trong KB):** `redis-cluster-sentinel-failover`, `distributed-rate-limiting-lua`, `sliding-window-rate-limiter`

### Chi tiết Tasks & Phụ thuộc (Dependencies)

| Task | Milestone | Loại | Thời lượng | Lịch dự kiến | Outcomes | Tiên quyết (Predecessors) |
|---|---|---|---:|---|---|---|
| **T1**: Nghiên cứu nguyên lý các chiến lược ghi/đọc Cache | M1 | `THEORY` | 60 phút | 2026-11-17 19:30–20:30 (60p) | M1-O1 | Không |
| **T2**: Khảo sát và cấu hình các chính sách thu hồi bộ nhớ trong Redis | M1 | `THEORY` | 60 phút | 2026-11-17 20:30–21:30 (60p) | M1-O2 | T1 (bắt buộc) |
| **T3**: Xây dựng ứng dụng tích hợp Cache-Aside và Write-Behind | M1 | `PRACTICE` | 120 phút | 2026-11-19 19:30–20:30 (60p); 2026-11-19 20:30–21:30 (60p) | M1-O3 | T2 (bắt buộc) |
| **T4**: Kiểm thử tự động tính nhất quán dữ liệu và cơ chế Eviction | M1 | `REVIEW` | 60 phút | 2026-11-21 09:00–10:00 (60p) | M1-O1, M1-O2, M1-O3 | T3 (bắt buộc) |
| **T5**: Phân tích các sự cố kinh điển: Avalanche, Stampede và Penetration | M2 | `THEORY` | 60 phút | 2026-11-21 10:00–11:00 (60p) | M2-O1 | T4 (bắt buộc) |
| **T6**: Cài đặt kỹ thuật Jittered TTL và Khóa phân tán phòng chống Stampede | M2 | `PRACTICE` | 100 phút | 2026-11-21 11:00–11:50 (50p); 2026-11-24 19:30–20:20 (50p) | M2-O2 | T5 (bắt buộc) |
| **T7**: Triển khai Bloom Filter và thuật toán Probabilistic Early Expiration | M2 | `PRACTICE` | 100 phút | 2026-11-24 20:20–21:10 (50p); 2026-11-26 19:30–20:20 (50p) | M2-O3 | T6 (bắt buộc) |
| **T8**: Kiểm thử chịu tải mô phỏng 5000 concurrent requests | M2 | `REVIEW` | 100 phút | 2026-11-26 20:20–21:10 (50p); 2026-11-28 09:00–09:50 (50p) | M2-O1, M2-O2, M2-O3 | T7 (bắt buộc) |
| **T9**: Nghiên cứu nguyên lý Consistent Hashing so với Hash Mod N | M3 | `THEORY` | 60 phút | 2026-11-28 09:50–10:50 (60p) | M3-O1 | T8 (bắt buộc) |
| **T10**: Cài đặt thuật toán Hash Ring hỗ trợ Virtual Nodes | M3 | `PRACTICE` | 100 phút | 2026-11-28 10:50–11:40 (50p); 2026-12-01 19:30–20:20 (50p) | M3-O2 | T9 (bắt buộc) |
| **T11**: Tìm hiểu kiến trúc Hash Slots và Redirection trong Redis Cluster | M3 | `PRACTICE` | 100 phút | 2026-12-01 20:20–21:10 (50p); 2026-12-03 19:30–20:20 (50p) | M3-O3 | T10 (bắt buộc) |
| **T12**: Đo kiểm tỷ lệ phân phối và di chuyển keys trên Hash Ring | M3 | `REVIEW` | 100 phút | 2026-12-03 20:20–21:10 (50p); 2026-12-05 09:00–09:50 (50p) | M3-O1, M3-O2, M3-O3 | T11 (bắt buộc) |
| **T13**: Thiết lập cụm Redis Cluster đa node với Master-Replica | M4 | `PRACTICE` | 100 phút | 2026-12-05 09:50–10:40 (50p); 2026-12-05 10:40–11:30 (50p) | M4-O1 | T12 (bắt buộc) |
| **T14**: Cài đặt giải thuật Token Bucket và Sliding Window bằng Redis Lua Script | M4 | `PRACTICE` | 100 phút | 2026-12-08 19:30–20:20 (50p); 2026-12-08 20:20–21:10 (50p) | M4-O2 | T13 (bắt buộc) |
| **T15**: Đóng gói Distributed Rate Limiting Middleware | M4 | `PRACTICE` | 100 phút | 2026-12-10 19:30–20:20 (50p); 2026-12-10 20:20–21:10 (50p) | M4-O3 | T14 (bắt buộc) |
| **T16**: Dự án tổng hợp: Kiểm thử tải và xác thực Rate Limiter trên Redis Cluster | M4 | `PROJECT` | 120 phút | 2026-12-12 09:00–10:00 (60p); 2026-12-12 10:00–11:00 (60p) | M4-O1, M4-O2, M4-O3 | T15 (bắt buộc) |

#### Chi tiết nội dung M1 (4 tasks)

- **T1 — Nghiên cứu nguyên lý các chiến lược ghi/đọc Cache** (`THEORY`, 60 phút)
  - *Mô tả:* Phân tích kiến trúc, luồng dữ liệu, ưu điểm và nhược điểm của các mẫu Cache-Aside, Write-Through, Write-Behind và Write-Around trong hệ thống phân tán.
  - *Mục tiêu học tập:* Hiểu rõ sự đánh đổi giữa tính nhất quán (consistency), độ trễ (latency) và thông lượng (throughput) khi áp dụng từng chiến lược caching.
  - *Tiêu chí hoàn thành:* Lập bảng so sánh chi tiết 4 chiến lược caching kèm sơ đồ tuần tự (sequence diagram) cho từng trường hợp đọc/ghi.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* Không | *Lịch dự kiến:* 2026-11-17 19:30–20:30 (60p)
- **T2 — Khảo sát và cấu hình các chính sách thu hồi bộ nhớ trong Redis** (`THEORY`, 60 phút)
  - *Mô tả:* Tìm hiểu cơ chế giải phóng bộ nhớ khi đạt giới hạn maxmemory và thực hành cấu hình các policy: allkeys-lru, volatile-lru, allkeys-lfu, volatile-ttl trên Redis CLI.
  - *Mục tiêu học tập:* Nắm vững nguyên lý hoạt động của thuật toán LRU/LFU xấp xỉ trong Redis và lựa chọn chính sách phù hợp với đặc thù truy vấn.
  - *Tiêu chí hoàn thành:* Viết tài liệu ghi lại kết quả thử nghiệm mô phỏng việc đẩy dữ liệu vượt maxmemory và quan sát key bị xóa theo từng policy.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T1 (bắt buộc) | *Lịch dự kiến:* 2026-11-17 20:30–21:30 (60p)
- **T3 — Xây dựng ứng dụng tích hợp Cache-Aside và Write-Behind** (`PRACTICE`, 120 phút)
  - *Mô tả:* Lập trình dịch vụ backend mô phỏng truy vấn dữ liệu với Cache-Aside, đồng thời tích hợp hàng đợi Redis để ghi bất đồng bộ dữ liệu xuống cơ sở dữ liệu quan hệ theo mẫu Write-Behind.
  - *Mục tiêu học tập:* Áp dụng thành công Cache-Aside để giảm tải đọc cho CSDL và Write-Behind để tối ưu tốc độ ghi kết hợp xử lý bất đồng bộ.
  - *Tiêu chí hoàn thành:* Mã nguồn dịch vụ backend hoạt động hoàn chỉnh, dữ liệu ghi vào cache được hàng đợi đồng bộ chính xác xuống DB quan hệ mà không làm mất mát bản ghi.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T2 (bắt buộc) | *Lịch dự kiến:* 2026-11-19 19:30–20:30 (60p); 2026-11-19 20:30–21:30 (60p)
- **T4 — Kiểm thử tự động tính nhất quán dữ liệu và cơ chế Eviction** (`REVIEW`, 60 phút)
  - *Mô tả:* Viết bộ kiểm thử tự động (integration tests) kiểm tra sự đồng bộ dữ liệu giữa Redis và DB trong mẫu Write-Behind, đồng thời xác minh cơ chế thu hồi key khi chạm ngưỡng bộ nhớ.
  - *Mục tiêu học tập:* Đánh giá toàn diện độ tin cậy của giải pháp caching và khả năng tự phục hồi khi bộ nhớ cache bị đầy.
  - *Tiêu chí hoàn thành:* Tất cả các bài kiểm thử tự động vượt qua 100%, chứng minh không xảy ra thất thoát dữ liệu và eviction policy hoạt động chính xác theo cấu hình.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T3 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 09:00–10:00 (60p)

#### Chi tiết nội dung M2 (4 tasks)

- **T5 — Phân tích các sự cố kinh điển: Avalanche, Stampede và Penetration** (`THEORY`, 60 phút)
  - *Mô tả:* Nghiên cứu nguyên nhân cốt lõi gây sập hệ thống do Cache Avalanche, Cache Stampede (Thundering Herd) và Cache Penetration, cùng giải pháp khắc phục lý thuyết.
  - *Mục tiêu học tập:* Hiểu rõ các kịch bản lỗi tải nặng trên tầng cache và nắm vững nguyên lý hoạt động của Mutex Lock, Jittered TTL và Bloom Filter.
  - *Tiêu chí hoàn thành:* Hoàn thành tài liệu phân tích rủi ro, chỉ ra rõ cơ chế xảy ra lỗi và biện pháp phòng ngừa tương ứng cho từng loại sự cố.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T4 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 10:00–11:00 (60p)
- **T6 — Cài đặt kỹ thuật Jittered TTL và Khóa phân tán phòng chống Stampede** (`PRACTICE`, 100 phút)
  - *Mô tả:* Lập trình cơ chế phân rã ngẫu nhiên thời gian sống (TTL Jitter) cho cache keys và triển khai Distributed Mutex Locking bằng Redis SETNX nhằm đảm bảo chỉ 1 tiến trình tính toán lại dữ liệu.
  - *Mục tiêu học tập:* Ngăn chặn hiện tượng hàng nghìn truy vấn đồng thời đánh thẳng vào DB khi một hot-key hết hạn.
  - *Tiêu chí hoàn thành:* Code giải thuật Mutex Lock và Jittered TTL hoạt động ổn định, có xử lý trường hợp lock timeout an toàn.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T5 (bắt buộc) | *Lịch dự kiến:* 2026-11-21 11:00–11:50 (50p); 2026-11-24 19:30–20:20 (50p)
- **T7 — Triển khai Bloom Filter và thuật toán Probabilistic Early Expiration** (`PRACTICE`, 100 phút)
  - *Mô tả:* Tích hợp cấu trúc dữ liệu Bloom Filter trong Redis để chặn đứng các truy vấn id ảo (Cache Penetration), kết hợp thuật toán làm mới sớm ngẫu nhiên (XFetch) cho hot keys.
  - *Mục tiêu học tập:* Bảo vệ tầng cơ sở dữ liệu trước các cuộc tấn công quét khóa không tồn tại và loại bỏ độ trễ tính toán lại hot cache.
  - *Tiêu chí hoàn thành:* Triển khai Bloom Filter ngăn chặn thành công 100% truy vấn không hợp lệ và thuật toán XFetch tự động làm mới key trước khi hết hạn chính thức.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T6 (bắt buộc) | *Lịch dự kiến:* 2026-11-24 20:20–21:10 (50p); 2026-11-26 19:30–20:20 (50p)
- **T8 — Kiểm thử chịu tải mô phỏng 5000 concurrent requests** (`REVIEW`, 100 phút)
  - *Mô tả:* Sử dụng công cụ kiểm thử tải (như k6 hoặc wrk) giả lập kịch bản 5000 requests đồng thời truy cập khi hot key hết hạn và các truy vấn khóa ngẫu nhiên không tồn tại.
  - *Mục tiêu học tập:* Đo lường hiệu quả thực tế của các giải pháp phòng chống lỗi cache dưới áp lực tải cao.
  - *Tiêu chí hoàn thành:* Báo cáo kiểm thử tải chứng minh tỷ lệ DB hit luôn được duy trì dưới 5%, không có lỗi sập kết nối hoặc nghẽn cổ chai.
  - *Concepts:* `sys-caching-redis-queues`
  - *Tiên quyết:* T7 (bắt buộc) | *Lịch dự kiến:* 2026-11-26 20:20–21:10 (50p); 2026-11-28 09:00–09:50 (50p)

#### Chi tiết nội dung M3 (4 tasks)

- **T9 — Nghiên cứu nguyên lý Consistent Hashing so với Hash Mod N** (`THEORY`, 60 phút)
  - *Mô tả:* Phân tích bài toán sharding dữ liệu trên nhiều node, tác hại của việc thay đổi số lượng node khi dùng hash(key) mod N và cách Consistent Hashing giải quyết bài toán tái phân bổ dữ liệu.
  - *Mục tiêu học tập:* Nắm vững bản chất toán học của vòng băm nhất quán và lý do cần áp dụng trong hệ thống lưu trữ phân tán.
  - *Tiêu chí hoàn thành:* Viết báo cáo phân tích toán học tính toán tỷ lệ khóa phải di chuyển khi n thay đổi giữa hai phương pháp chia dư và băm nhất quán.
  - *Tiên quyết:* T8 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 09:50–10:50 (60p)
- **T10 — Cài đặt thuật toán Hash Ring hỗ trợ Virtual Nodes** (`PRACTICE`, 100 phút)
  - *Mô tả:* Lập trình cấu trúc dữ liệu Hash Ring bằng một ngôn ngữ lập trình cụ thể, bổ sung cơ chế Virtual Nodes (vnodes) để giải quyết vấn đề phân bố tải không đồng đều giữa các node vật lý.
  - *Mục tiêu học tập:* Tự tay hiện thực thuật toán băm nhất quán và chứng minh hiệu quả cân bằng tải của các node ảo.
  - *Tiêu chí hoàn thành:* Mã nguồn Hash Ring hoàn chỉnh với đầy đủ các hàm add_node, remove_node, get_node và unit test kiểm tra tính đúng đắn.
  - *Tiên quyết:* T9 (bắt buộc) | *Lịch dự kiến:* 2026-11-28 10:50–11:40 (50p); 2026-12-01 19:30–20:20 (50p)
- **T11 — Tìm hiểu kiến trúc Hash Slots và Redirection trong Redis Cluster** (`PRACTICE`, 100 phút)
  - *Mô tả:* Nghiên cứu cách Redis Cluster triển khai 16384 Hash Slots, cơ chế client redirection (MOVED và ASK) và cách sử dụng Hash Tags {tag} để định tuyến các key liên quan về cùng một slot.
  - *Mục tiêu học tập:* Hiểu rõ sự khác biệt giữa Consistent Hashing thuần túy và kiến trúc Hash Slots cố định của Redis Cluster.
  - *Tiêu chí hoàn thành:* Thực hiện thành công các lệnh thử nghiệm gom nhóm key bằng Hash Tags trên Redis và giải thích cơ chế phản hồi MOVED redirection.
  - *Tiên quyết:* T10 (bắt buộc) | *Lịch dự kiến:* 2026-12-01 20:20–21:10 (50p); 2026-12-03 19:30–20:20 (50p)
- **T12 — Đo kiểm tỷ lệ phân phối và di chuyển keys trên Hash Ring** (`REVIEW`, 100 phút)
  - *Mô tả:* Viết kịch bản sinh 100.000 keys ngẫu nhiên vào Hash Ring, đo độ lệch chuẩn phân phối giữa các node khi có vnodes và tỷ lệ key bị di chuyển khi thêm/bớt một node vật lý.
  - *Mục tiêu học tập:* Kiểm chứng bằng thực nghiệm các đặc tính lý thuyết của Consistent Hashing với Virtual Nodes.
  - *Tiêu chí hoàn thành:* Biểu đồ và báo cáo đo kiểm cho thấy độ lệch phân phối keys giữa các node dưới 10% và tỷ lệ key di chuyển xấp xỉ mức lý thuyết 1/(N+1).
  - *Tiên quyết:* T11 (bắt buộc) | *Lịch dự kiến:* 2026-12-03 20:20–21:10 (50p); 2026-12-05 09:00–09:50 (50p)

#### Chi tiết nội dung M4 (4 tasks)

- **T13 — Thiết lập cụm Redis Cluster đa node với Master-Replica** (`PRACTICE`, 100 phút)
  - *Mô tả:* Cấu hình và khởi chạy cụm Redis Cluster cục bộ (3 Master nodes và 3 Replica nodes) bằng Docker Compose, kiểm tra cơ chế phân bổ slot và tính năng tự động failover khi 1 master gặp sự cố.
  - *Mục tiêu học tập:* Thành thạo kỹ năng triển khai cụm Redis có khả năng sẵn sàng cao (High Availability) và phân tán dữ liệu thực tế.
  - *Tiêu chí hoàn thành:* Cụm Redis Cluster 6 nodes ở trạng thái cluster_state:ok, mô phỏng tắt 1 master node thì replica tương ứng được tự động thăng cấp thành master.
  - *Tiên quyết:* T12 (bắt buộc) | *Lịch dự kiến:* 2026-12-05 09:50–10:40 (50p); 2026-12-05 10:40–11:30 (50p)
- **T14 — Cài đặt giải thuật Token Bucket và Sliding Window bằng Redis Lua Script** (`PRACTICE`, 100 phút)
  - *Mô tả:* Viết các kịch bản Lua Script chạy trực tiếp trên Redis để cài đặt thuật toán Token Bucket và Sliding Window Log/Counter nhằm đảm bảo tính nguyên tử tuyệt đối (atomicity) trong môi trường phân tán.
  - *Mục tiêu học tập:* Tận dụng Lua Script để loại bỏ race condition khi cập nhật bộ đếm rate limiting mà không cần distributed locks nặng nề.
  - *Tiêu chí hoàn thành:* Hai đoạn mã Lua script (Token Bucket & Sliding Window) chạy thành công trên Redis, vượt qua kiểm thử đơn vị về tính đúng đắn khi đếm.
  - *Tiên quyết:* T13 (bắt buộc) | *Lịch dự kiến:* 2026-12-08 19:30–20:20 (50p); 2026-12-08 20:20–21:10 (50p)
- **T15 — Đóng gói Distributed Rate Limiting Middleware** (`PRACTICE`, 100 phút)
  - *Mô tả:* Tích hợp Lua scripts vào middleware backend (hoặc API Gateway), thiết kế cơ chế lấy client IP/user ID làm key, trả về đúng HTTP headers (X-RateLimit-Limit, Remaining, Reset) và mã lỗi 429.
  - *Mục tiêu học tập:* Hoàn thiện một middleware chuẩn phân tán có thể tái sử dụng cho các microservices backend kết nối với Redis Cluster.
  - *Tiêu chí hoàn thành:* Middleware chặn chính xác các request vượt ngưỡng cấu hình với mã 429 Too Many Requests và trả về đầy đủ rate-limit headers.
  - *Tiên quyết:* T14 (bắt buộc) | *Lịch dự kiến:* 2026-12-10 19:30–20:20 (50p); 2026-12-10 20:20–21:10 (50p)
- **T16 — Dự án tổng hợp: Kiểm thử tải và xác thực Rate Limiter trên Redis Cluster** (`PROJECT`, 120 phút)
  - *Mô tả:* Kết nối API Gateway / backend service vào cụm Redis Cluster 6 nodes, chạy bài kiểm thử tải quy mô lớn với nhiều client đồng thời để kiểm tra tính nhất quán của bộ giới hạn tần suất.
  - *Mục tiêu học tập:* Xác nhận tính chính xác, hiệu năng và độ ổn định của toàn bộ hệ sinh thái Caching & Rate Limiting phân tán.
  - *Tiêu chí hoàn thành:* Hệ thống chịu tải ổn định, số lượng request cho phép và bị từ chối khớp chính xác 100% với cấu hình thuật toán mà không có sai lệch race condition.
  - *Tiên quyết:* T15 (bắt buộc) | *Lịch dự kiến:* 2026-12-12 09:00–10:00 (60p); 2026-12-12 10:00–11:00 (60p)

---
