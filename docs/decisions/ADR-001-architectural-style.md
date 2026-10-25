# ADR-001: Lựa chọn Kiến trúc Context-First Modular Monolith kết hợp Hexagonal Architecture (Ports & Adapters)

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0)
* **Ngày quyết định:** 29/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `ASR-01`, `ASR-02`, `ASR-06`, Toàn bộ SRS v1.1 (`UC-01` đến `UC-19`), `BUSR-01` đến `BUSR-12`, `NFR-MAINT-001`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow là hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI theo mô hình Học tập Tự điều chỉnh của Zimmerman (SRL: Forethought → Performance → Self-Reflection). Hệ thống chứa nhiều quy tắc nghiệp vụ phức tạp thuộc các miền con khác nhau:
* Quản lý tài khoản, hồ sơ năng lực người học (`LearnerProfile`), cấu hình quỹ thời gian rảnh lai Mode A/B (`HybridAvailabilityRuleEngine`), hạn ngạch AI 2 pha (`AIQuota`, `AIQuotaReservation`) và thanh toán nâng cấp gói.
* Phân rã mục tiêu học tập, kiểm duyệt DAG không chu trình (`DagCycleValidator`), cổng kiểm duyệt AI 3 tầng và phát hành lịch học chính thức (`OfficialSchedule`).
* Vận hành không gian học tập tập trung (Pomodoro/Stopwatch), ghi nhận Heartbeat 60s, thu hồi phiên treo và đồng bộ lịch ngoại vi (Google Calendar OAuth2 & WebCal `.ics`).
* Phân tích thống kê định lượng, sinh đánh giá AI định kỳ, tịnh tiến lịch tất định (`DominoShiftEngine`) và ngắt mạch chống lặp quá hạn (`reschedule_count >= 3`).

Trong phiên bản thiết kế ban đầu (v1.0), việc tổ chức thư mục theo kiểu **Layer-First Monolith** (`src/domain/`, `src/application/`, `src/infrastructure/` dùng chung cho toàn hệ thống) dẫn đến nguy cơ các module nghiệp vụ gọi chéo trực tiếp vào Repository và Entity của nhau, làm mờ ranh giới miền (Bounded Context) và khó bảo trì khi mở rộng lên 19 Use Cases và 24 bảng dữ liệu.

Nhóm phát triển cần một phong cách kiến trúc đảm bảo:
1. **Cô lập miền nghiệp vụ ở cấp độ cao nhất (`ASR-01`):** Khi sửa đổi quy tắc trong một Bounded Context, không một file nội bộ nào của các Context khác bị ảnh hưởng.
2. **Bảo vệ sự tinh khiết của Domain (`Hexagonal Purity`):** Các thuật toán cốt lõi (`HybridAvailabilityRuleEngine`, `DagCycleValidator`, `DominoShiftEngine`) hoàn toàn độc lập với FastAPI, SQLAlchemy, Taskiq hay LLM SDK.
3. **Đảm bảo tính nhất quán dữ liệu liên module (`ASR-02`):** Không mất sự kiện khi giao tiếp giữa các Bounded Context ngay cả khi tiến trình worker gặp sự cố.
4. **Chi phí vận hành tối ưu:** Phù hợp với quy mô đồ án tốt nghiệp 2 sinh viên mà không rơi vào bẫy phức tạp phân tán của Microservices.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Layer-First Monolith truyền thống
* Tổ chức mã nguồn ở cấp cao nhất theo tầng kỹ thuật (`src/domain/`, `src/application/`, `src/infrastructure/`, `src/presentation/`), gom chung tất cả các miền nghiệp vụ vào cùng một thư mục tầng.
* *Ưu điểm:* Quen thuộc, dễ khởi tạo lúc dự án còn nhỏ.
* *Nhược điểm:* Độ gắn kết theo chiều ngang (Horizontal Coupling) cao; các Use Case dễ dàng import chéo ORM Model hoặc Repository của miền khác, vi phạm nguyên tắc đóng gói của Domain-Driven Design (DDD).

### Phương án B: Microservices Architecture (4 Services độc lập + Message Broker riêng)
* Tách vật lý thành 4 dịch vụ độc lập (`account-service`, `planning-service`, `execution-service`, `evaluation-service`) với 4 cơ sở dữ liệu riêng biệt.
* *Ưu điểm:* Cô lập vật lý tuyệt đối ở cấp tiến trình.
* *Nhược điểm:* Quá tải vận hành (12+ containers) cho quy mô đồ án tốt nghiệp; mất khả năng kiểm chứng khóa ngoại vật lý 3NF/BCNF trên cùng PostgreSQL; phát sinh bài toán giao dịch phân tán phức tạp không cần thiết ở ngưỡng tải hiện tại.

### Phương án C: Context-First Modular Monolith kết hợp Hexagonal Architecture (Ports & Adapters) (Được chọn)
* Ở **cấp độ 1 (Top-level Package)**, phân rã hệ thống theo **4 Bounded Contexts nghiệp vụ độc lập** (`account`, `planning`, `execution`, `evaluation`) cùng 1 **`shared_kernel`** kỹ thuật:
  * `account`: Quản lý định danh, xác thực, hồ sơ SRL, lịch rảnh Mode A/B, hạn ngạch AI 2 pha và thanh toán (`UC-01..UC-05`, `UC-18`).
  * `planning`: Quản lý mục tiêu, lộ trình, cột mốc, DAG công việc, cổng kiểm duyệt AI 3 tầng và lịch chính thức (`UC-06..UC-09`).
  * `execution`: Quản lý phiên học Pomodoro/Stopwatch, ghi chú, Heartbeat 60s, thu hồi phiên treo và đồng bộ lịch ngoại vi (`UC-10..UC-13`).
  * `evaluation`: Tính toán chỉ số định lượng, đánh giá AI định kỳ, dịch lịch Domino Shift, chống lặp quá hạn và giám sát hệ thống (`UC-14..UC-17`, `UC-19`).
* Ở **cấp độ 2 (Bên trong mỗi Bounded Context)**, áp dụng nghiêm ngặt **Kiến trúc Lục giác (Hexagonal Architecture / Ports & Adapters)** với 4 tầng: `domain` ← `application` ← `infrastructure` ← `presentation`, kèm file giao diện công khai duy nhất `public_api.py`.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Kiến trúc Context-First Modular Monolith kết hợp Hexagonal Architecture (Ports & Adapters)** với 5 quy tắc kiến trúc bắt buộc:

### 3.1. Ranh giới `public_api.py` Nghiêm ngặt cho Truy vấn Đọc Đồng bộ
* Các Bounded Context **tuyệt đối không được phép import** vào bên trong `domain/`, `application/`, `infrastructure/` hoặc `presentation/` của một Context khác.
* Mọi nhu cầu đọc dữ liệu đồng bộ liên Context (ví dụ: `planning` cần đọc cấu hình lịch rảnh Mode A/B hoặc yêu cầu giữ chỗ Quota từ `account`) bắt buộc phải gọi qua các **Read-Only Query Ports / Facade Protocols** và DTO bất biến được xuất bản tại `src/<context>/public_api.py`.

### 3.2. Hai Cơ chế Sự kiện Phân tầng: In-Process Domain Event Bus & Transactional Outbox
1. **Nội bộ Bounded Context (Intra-Context):** Sử dụng **In-Process Domain Event Bus** (`InProcessEventBus`) để xử lý các phản ứng tức thời trong cùng một giao dịch `AsyncUnitOfWork` của một Context.
2. **Liên Bounded Context (Cross-Context Eventual Consistency):** Sử dụng mẫu **Transactional Outbox (`outbox_events`) + Idempotent Consumer (`processed_events`)**:
   * Khi Aggregate Root phát sinh Domain Event liên Context (như `StudySessionCompletedEvent`, `UserUpgradedToPremiumEvent`, `OfficialScheduleAppliedEvent`), `SqlAlchemyUnitOfWork` ghi nhận sự kiện vào bảng `outbox_events` trong **cùng một giao dịch ACID** với thay đổi nghiệp vụ.
   * Tiến trình **Outbox Relay Task** trên **Taskiq Worker** đọc các bản ghi `PENDING` (sử dụng `SELECT ... FOR UPDATE SKIP LOCKED`), đẩy vào **Redis Streams (`RedisStreamBroker`)** để Context đích tiêu thụ bất đồng bộ.
   * Context đích kiểm tra `event_id` trong bảng `processed_events` trước khi thực thi nhằm đảm bảo tính **Idempotency (Thực thi đúng 1 lần về mặt hiệu quả)** ngay cả khi thông điệp được gửi lại (At-least-once delivery).

### 3.3. Mô hình Miền Phong phú (Rich Aggregate Roots) & Pure Domain Services
* **Rich Aggregate Roots:** Các thực thể gốc (`User`, `AvailabilityProfile`, `AIQuota`, `Roadmap`, `OfficialSchedule`, `StudySession`, `AIReview`) tự đóng gói trạng thái và bảo vệ các bất biến nghiệp vụ (Domain Invariants) bên trong phương thức của mình thay vì dùng Anemic Data Model.
* **Pure Domain Services (100% Pure Python, 0 I/O):** Các giải thuật phức tạp liên thực thể được tách thành các Domain Service thuần khiết không phụ thuộc hạ tầng:
  * `HybridAvailabilityRuleEngine` (trong `account.domain`): Tính toán dung lượng rảnh Mode A (Hard Ceiling) và kiểm tra khe thời gian Mode B (bao gồm dung sai Soft Overflow $\le 30$ phút và các khe vắt qua nửa đêm).
  * `DagCycleValidator` (trong `planning.domain`): Kiểm định đồ thị phụ thuộc công việc (DAG) bằng thuật toán sắp xếp tô-pô / DFS phát hiện chu trình.
  * `DominoShiftEngine` (trong `evaluation.domain`): Tính toán tịnh tiến ngày bắt đầu/kết thúc của các Task và Milestone khi tạm dừng lộ trình hoặc xử lý quá hạn.

### 3.4. Kiểm chứng Kiến trúc Tự động bằng `import-linter` (Architectural Fitness Functions)
Cấu hình **`import-linter`** ngay trong `backend/pyproject.toml` làm cổng chặn CI/CD tự động với 2 hợp đồng:
* **Contract 1 — Context Isolation (`forbidden`):** Cấm tuyệt đối mọi import chéo giữa các gói nội bộ của `account`, `planning`, `execution`, `evaluation` (ngoại trừ `src.<context>.public_api` và `src.shared_kernel`).
* **Contract 2 — Hexagonal Layer Purity (`layers`):** Cưỡng chế chiều phụ thuộc một chiều `presentation -> infrastructure -> application -> domain` bên trong từng Bounded Context; tầng `domain` không được import bất kỳ thư viện hạ tầng nào (`fastapi`, `sqlalchemy`, `taskiq`, `redis`, `litellm`).

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Cô lập Mô-đun Tuyệt đối (`ASR-01`):** Tổ chức Context-First giúp cấu trúc thư mục phản ánh trực tiếp kiến trúc miền nghiệp vụ (Screaming Architecture). Nếu trong tương lai cần tách `planning` hoặc `evaluation` thành Microservice độc lập (khi tải vượt ngưỡng $> 500\text{ req/s}$), ranh giới `public_api.py` và `outbox_events` cho phép tách dịch vụ mà không phải viết lại Domain hay Use Case.
* **Khả năng Kiểm thử Đơn vị Tối đa (Testability):** Toàn bộ `HybridAvailabilityRuleEngine`, `DagCycleValidator`, `DominoShiftEngine` và các Aggregate Roots có thể được kiểm thử bằng `pytest` trong vài mili-giây mà không cần khởi tạo PostgreSQL, Redis hay gọi LLM thật.
* **Đánh đổi Chấp nhận được:** Cần định nghĩa các DTO tại `public_api.py` và mapper giữa ORM Model với Domain Entity. Chi phí viết code tăng nhẹ ở giai đoạn đầu nhưng đổi lại sự an toàn kiểu dữ liệu và không bao giờ bị rò rỉ ORM Session chéo module.

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Giải quyết triệt để mâu thuẫn giữa kiến trúc phân tầng cũ và mô hình DDD; đạt chuẩn mực cao nhất của Tiêu chí Rubric TC2.1.
* **Kiểm chứng Tự động:** Lệnh `lint-imports` (`import-linter`) phải trả về `0 broken contracts` trước khi hợp nhất bất kỳ nhánh mã nguồn nào.
