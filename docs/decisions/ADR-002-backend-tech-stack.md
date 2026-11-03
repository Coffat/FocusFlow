# ADR-002: Lựa chọn Nền tảng Công nghệ Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 Async & Composition Root DI

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0)
* **Ngày quyết định:** 29/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `ASR-01`, `ASR-02`, `ASR-03`, `NFR-PERF-001`, `NFR-PERF-002`, `NFR-AI-001`, `NFR-SEC-001..004`, `BUSR-10`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Backend của FocusFlow đóng vai trò điều phối trung tâm cho 4 Bounded Contexts (`account`, `planning`, `execution`, `evaluation`), vừa phục vụ REST API độ trễ thấp ($\le 250\text{ms}$ P95), vừa phát luồng Server-Sent Events (SSE) thời gian thực ($\text{TTFT} \le 2.5\text{s}$), vừa chia sẻ cùng bộ Use Cases và Repositories cho tiến trình xử lý tác vụ nền (`Taskiq Worker`).

Trong các dự án FastAPI thông thường, hai sai lầm kiến trúc phổ biến thường xảy ra:
1. **Rò rỉ Framework vào Tầng Nghiệp vụ:** Đưa `fastapi.Depends`, `Request`, hoặc `HTTPException` vào trực tiếp trong các lớp Use Case ở tầng `application`, khiến Use Case bị trói chặt vào HTTP context và không thể tái sử dụng sạch sẽ trong Worker hay CLI.
2. **Quản lý Giao dịch (Transaction) Rời rạc:** Gọi `session.commit()` rải rác trong từng phương thức Repository, làm mất tính nguyên tử (Atomicity) khi một Use Case cần cập nhật đồng thời Aggregate Root, bảng `ai_quota_reservations` và bảng `outbox_events`.

Do đó, nhóm cần chuẩn hóa ngăn xếp công nghệ Backend cùng quy tắc tiêm phụ thuộc (Dependency Injection), quản trị giao dịch (`AsyncUnitOfWork`) và công cụ kiểm soát chất lượng mã nguồn.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Node.js / TypeScript (NestJS + Prisma ORM)
* *Ưu điểm:* Đồng nhất ngôn ngữ TypeScript với Frontend Angular; hỗ trợ DI qua Decorator sẵn có.
* *Nhược điểm:* Hệ sinh thái thư viện AI, công cụ đánh giá mô hình và xử lý dữ liệu khoa học không phong phú bằng Python; Prisma ORM hạn chế khi biểu diễn mô hình Domain-Driven Design với Rich Aggregate Roots và các truy vấn khóa hàng nâng cao (`SELECT ... FOR UPDATE SKIP LOCKED`).

### Phương án B: Python + FastAPI nhưng dùng `Depends` xuyên suốt các tầng & `session.commit()` tại Repository
* *Ưu điểm:* Viết nhanh cho ứng dụng CRUD nhỏ.
* *Nhược điểm:* Vi phạm kiến trúc Hexagonal (`ADR-001`); khó kiểm soát ranh giới giao dịch ACID khi kết hợp ghi dữ liệu nghiệp vụ và ghi `outbox_events`.

### Phương án C: Python 3.12+ + FastAPI + Pydantic v2 + SQLAlchemy 2.0 Async + Composition Root DI & `AsyncUnitOfWork` (Được chọn)
* Sử dụng Python 3.12+, FastAPI (ASGI Uvicorn), Pydantic v2, SQLAlchemy 2.0 Async (`asyncpg`) và Alembic.
* Giới hạn `Depends` (FastAPI) và `TaskiqDepends` (Taskiq) **nghiêm ngặt tại Tầng Presentation (`presentation/deps.py` — Composition Root)**.
* Tầng Application (`Use Cases`) 100% không phụ thuộc framework và quản lý giao dịch tường minh thông qua giao diện `AsyncUnitOfWork` (`async with self.uow:`).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C với các tiêu chuẩn kỹ thuật bắt buộc sau:**

### 3.1. Ngăn xếp Cốt lõi (Core Runtime & Persistence Stack)
1. **Ngôn ngữ & Runtime:** **Python 3.12+** (tận dụng cải tiến hiệu năng asyncio, hệ thống kiểu `type` statement mới và thông báo lỗi chi tiết).
2. **Web & API Framework:** **FastAPI** chạy trên ASGI server **Uvicorn**, tự động xuất đặc tả **OpenAPI 3.1** làm nguồn chân lý sinh kiểu TypeScript cho Frontend.
3. **Thẩm định Dữ liệu & Cấu hình:** **Pydantic v2** (nhân Rust `pydantic-core`) dùng cho Request/Response DTOs tại tầng Presentation, cấu hình `pydantic-settings` tại `shared_kernel/config.py`, và kiểm định Structured Outputs ở Tầng 1 của cổng AI Validation Gate.
4. **Truy cập CSDL Bất đồng bộ & Migration:** **SQLAlchemy 2.0 Async** (`AsyncEngine`, `AsyncSession`, cú pháp truy vấn `select()` chuẩn 2.0) kết hợp driver nhị phân tốc độ cao **`asyncpg`** và công cụ quản lý phiên bản lược đồ **Alembic**.

### 3.2. Quy tắc Tiêm Phụ thuộc tại Composition Root (`presentation/deps.py`)
* **Chỉ dùng `Depends` / `TaskiqDepends` tại Composition Root:** Mỗi Bounded Context có tệp `src/<context>/presentation/deps.py` chịu trách nhiệm khởi tạo `SqlAlchemyUnitOfWork`, các Adapter hạ tầng (`Repository`, `LLMProviderPort`, `PaymentGatewayPort`, `CalendarSyncPort`) và bơm chúng vào hàm khởi tạo `__init__` của Use Case.
* **Use Cases Tinh khiết 100% (Framework-Free Application Layer):** Các lớp Use Case trong `src/<context>/application/use_cases/` chỉ nhận các Python `Protocol` / `ABC` chuẩn và DTO thuần. Chúng không được import `fastapi`, `starlette`, `sqlalchemy` hay `taskiq`. Nhờ đó, cùng một Use Case có thể được gọi từ HTTP Router, Taskiq Worker hoặc bộ kiểm thử `pytest` mà không cần giả lập HTTP context.

### 3.3. Quản lý Giao dịch Nguyên tử qua `AsyncUnitOfWork`
* Mọi thao tác làm thay đổi trạng thái hệ thống (Command Use Cases) phải thực thi bên trong khối ngữ cảnh bất đồng bộ của `AsyncUnitOfWork`:
  ```python
  async with self.uow:
      await self.uow.roadmaps.save(roadmap)
      self.uow.collect_domain_events(roadmap)
      await self.uow.commit()
  ```
* Các phương thức trong Repository **chỉ gọi `session.add()` / `session.flush()`**, tuyệt đối không tự gọi `session.commit()`.
* Khi `await self.uow.commit()` được gọi, `SqlAlchemyUnitOfWork` tự động thu thập toàn bộ Domain Events phát sinh từ các Aggregate Roots, chuyển đổi các sự kiện liên Context thành bản ghi `OutboxEventORM` (`outbox_events`) và commit chung trong **1 giao dịch PostgreSQL ACID duy nhất** (hoặc tự động `rollback()` nếu có ngoại lệ).

### 3.4. Quan sát Hệ thống (Observability) & Cổng Chất lượng Mã nguồn (Quality Tooling)
* **Logging Cấu trúc & Truy vết:** Sử dụng **`structlog`** xuất nhật ký định dạng JSON chuẩn hóa, tự động gắn `correlation_id` (qua ASGI Middleware và truyền sang Taskiq message headers) cùng bộ lọc che giấu thông tin nhạy cảm (`PII & Token Sanitizer`).
* **Kiểm soát Chất lượng & Kiểu Tĩnh:**
  * **`ruff`**: Linter và Formatter tốc độ cao thay thế Flake8/Black/isort.
  * **`mypy --strict`**: Kiểm tra kiểu tĩnh nghiêm ngặt trên toàn bộ mã nguồn `backend/src`.
  * **`import-linter`**: Kiểm chứng tự động ranh giới 4 Bounded Contexts và chiều phụ thuộc Hexagonal (`ADR-001`).
  * **`pytest` + `pytest-asyncio`**: Bộ khung kiểm thử đơn vị, tích hợp và đánh giá AI bất đồng bộ.

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Tái sử dụng Tuyệt đối giữa HTTP API và Taskiq Worker:** Nhờ giữ `Depends` ở `presentation/deps.py` và đóng gói giao dịch trong `AsyncUnitOfWork`, cả FastAPI Router lẫn Taskiq Worker đều khởi tạo và gọi Use Case theo cùng một cách thống nhất.
* **Đảm bảo Toàn vẹn Dữ liệu (`ASR-02`):** Mẫu `AsyncUnitOfWork` kết hợp Transactional Outbox loại bỏ hoàn toàn lỗi lệch trạng thái (Dual-Write Problem) giữa CSDL PostgreSQL và hàng đợi Redis.
* **Đánh đổi:** Lập trình viên cần viết các hàm factory nhỏ trong `presentation/deps.py` để lắp ráp Use Case thay vì gọi trực tiếp ORM trong route handler. Đây là sự đánh đổi hoàn toàn xứng đáng để đạt độ sạch kiến trúc (Rubric TC2.1 & TC2.3 Mức 5).

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Đạt cam kết hiệu năng $\le 250\text{ms}$ (P95) cho REST API và $\le 2.5\text{s}$ TTFT cho luồng SSE (`ASR-03`); mã nguồn đạt chuẩn kiểu tĩnh 100% và dễ dàng bảo trì.
* **Kiểm chứng Tự động:** Pipeline kiểm tra bắt buộc chạy `ruff check`, `mypy --strict`, `lint-imports` và `pytest` trước khi đóng gói image.
