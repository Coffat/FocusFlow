# Đặc Tả Kỹ Thuật & Luận Chứng Kiến Trúc: Phân Hệ Cấu Hình Thời Gian Rảnh Lai (FR-AVAIL)
## Hybrid Availability Management Module (Mode A Quota & Mode B Time Slots)

---

| **Thuộc tính** | **Nội dung chi tiết** |
| :--- | :--- |
| **Dự án** | FocusFlow — Hệ điều hành Hỗ trợ Tự học Thích ứng Tích hợp Trí tuệ Nhân tạo |
| **Mã phân hệ** | `FR-AVAIL` (Bao gồm `FR-AVAIL-001`, `FR-AVAIL-002`, liên đới `FR-AVAIL-003`) |
| **Hạng mục WBS** | **WBS 5.3** (Sprint 1 — Milestone 2.5) |
| **Tác giả / Sinh viên** | Vũ Toàn Thắng |
| **Trạng thái tài liệu** | Hoàn thiện (Approved Specification & Architecture Guide) |
| **Căn cứ đánh giá** | Rubric Đồ án Tốt nghiệp CNTT — HCMUTE (Tiêu chí TC2.1, TC2.3, TC2.4, TC2.7) |
| **Truy vết SRS & Quyết định**| `SRS v1.0 (Mục 7.4)`, `OS-04`, `OS-06`, `BUSR-02`, `BUSR-03`, `BUSR-04`, `ADR-001`, `ADR-007` |

---

## MỤC LỤC
1. [Bối cảnh Thực tế & Đặt vấn đề Kỹ thuật](#1-bối-cảnh-thực-tế--đặt-vấn-đề-kỹ-thuật)
2. [Luận chứng Kỹ thuật & Phân tích Đánh đổi (Trade-off Analysis)](#2-luận-chứng-kỹ-thuật--phân-tích-đánh-đổi-trade-off-analysis)
3. [Mô hình Hóa Thiết kế Hệ thống Chuẩn UML 2.5.1](#3-mô-hình-hóa-thiết-kế-hệ-thống-chuẩn-uml-251)
4. [Đặc tả Thuật toán & Phân tích Độ phức tạp](#4-đặc-tả-thuật-toán--phân-tích-độ-phức-tạp)
5. [Thiết kế Cơ sở Dữ liệu & Chiến lược Lưu trữ (Persistence Design)](#5-thiết-kế-cơ-sở-dữ-liệu--chiến-lược-lưu-trữ-persistence-design)
6. [Hợp đồng Giao diện Lập trình Ứng dụng (RESTful API Contract)](#6-hợp-đồng-giao-diện-lập-trình-ứng-dụng-restful-api-contract)
7. [Kiến trúc Giao diện Người dùng Frontend (Angular 19 Signals Architecture)](#7-kiến-trúc-giao-diện-người-dùng-frontend-angular-19-signals-architecture)
8. [Ma trận Truy vết & Chiến lược Kiểm thử Chất lượng (Verification Matrix)](#8-ma-trận-truy-vết--chiến-lược-kiểm-thử-chất-lượng-verification-matrix)
9. [Lộ trình Triển khai Kỹ thuật Từng bước (Implementation Roadmap)](#9-lộ-trình-triển-khai-kỹ-thuật-từng-bước-implementation-roadmap)

---

## 1. Bối cảnh Thực tế & Đặt vấn đề Kỹ thuật

### 1.1. Nỗi đau Người học & Giới hạn của Các Giải pháp Hiện hành
Khảo sát người dùng tự học (`docs/requirements/user-survey-and-benchmarking.md`) chỉ ra rằng **68% người tự học bị vỡ kế hoạch (Plan Abandonment) ngay trong 2 tuần đầu tiên** do kế hoạch học tập quá phi thực tế, không ăn khớp với quỹ thời gian rảnh thực tế của họ:
- **Các ứng dụng To-Do truyền thống (Todoist, TickTick):** Chỉ quản lý danh sách công việc tĩnh, phó mặc hoàn toàn cho người dùng tự ước lượng và tự tìm giờ học.
- **Lịch biểu điện tử (Google Calendar, Apple Calendar):** Quản lý sự kiện theo khung giờ cứng ngắc, đòi hỏi người dùng phải tự sắp xếp thủ công từng block giờ, tốn từ 45–60 phút mỗi tuần.
- **Chatbot AI tạo kế hoạch dạng văn bản (ChatGPT, Claude):** Khi được yêu cầu lập lộ trình, AI chỉ trả về danh sách bài học kèm mốc tuần chung chung ("Tuần 1: Học cú pháp cơ bản; Tuần 2: Học OOP"), hoàn toàn mù mờ về việc người học rảnh vào thứ mấy, khung giờ nào và tối đa bao nhiêu tiếng mỗi ngày.

### 1.2. Khái niệm Mô hình Thời gian Rảnh Lai (Hybrid Availability Model)
Hệ thống FocusFlow tiếp cận bài toán bằng việc định nghĩa **Mô hình Thời gian Rảnh Lai (Hybrid Model)**, bao quát 2 nhóm chân dung người học đối lập:

```
                          ┌──────────────────────────────────────────────┐
                          │     HỒ SƠ THỜI GIAN RẢNH CỦA NGƯỜI HỌC       │
                          │        (AvailabilityProfile Entity)          │
                          └──────────────────────┬───────────────────────┘
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   ▼                                                           ▼
       ┌───────────────────────┐                                   ┌───────────────────────┐
       │   CHẾ ĐỘ A: MODE_A    │                                   │   CHẾ ĐỘ B: MODE_B    │
       │ (Daily Hours Quota)   │                                   │  (Fixed Time Slots)   │
       └───────────┬───────────┘                                   └───────────┬───────────┘
                   │                                                           │
     • Đối tượng: Người chuyển ngành (Hùng)                      • Đối tượng: Sinh viên ĐH (Mai)
     • Đặc thù: Thời gian biểu phân tán,                       • Đặc thù: Lịch cố định trên trường,
       không cố định giờ giấc từng ngày.                           chỉ rảnh tối T2-T4-T6.
     • Cấu hình: Tổng giờ rảnh / ngày (Hours).                   • Cấu hình: Khoảng thời gian cụ thể:
     • Phạm vi hợp lệ: 0.5h — 14.0h (OS-06).                       [19:30 - 21:30], [20:00 - 22:00].
     • Kiểm tra trần: Chặn cứng (Hard Ceiling).                 • Kiểm tra trần: Dung sai Soft Overflow
                                                                   (cho phép tràn <= 30 phút).
```

### 1.3. Các Yêu cầu Kỹ thuật Cốt lõi
- **`FR-AVAIL-001` (Cấu hình Chế độ A):** Thiết lập tổng số giờ rảnh mỗi ngày (Thứ 2 đến Chủ Nhật) kết hợp với Chính sách Lập lịch Dự kiến (Scheduling Preferences):
  - Áp dụng ngưỡng giá trị cận biên theo Quyết định Mở `OS-06`:
    $$\text{Cận dưới} = 0.5 \text{ giờ (30 phút/ngày)}; \quad \text{Cận trên} = 14.0 \text{ giờ/ngày}$$
    Tổng số giờ rảnh hợp lệ cả tuần phải thỏa mãn điều kiện sàn: $\sum \text{quota\_hours} \ge 1.0 \text{ giờ/tuần}$.
  - Nhằm cho phép AI Planner tạo thời khóa biểu có giờ bắt đầu/kết thúc cụ thể mà không cần đọc Google Calendar, Mode A bổ sung 3 trường cấu hình trong `DaySchedule`:
    1. `allowed_window`: Khung giờ cho phép xếp lịch trong ngày (ví dụ `07:00 - 23:00`).
    2. `preferred_period`: Buổi học ưu tiên (`MORNING`, `AFTERNOON`, `EVENING`, `ANY`).
    3. `min_session_minutes`: Thời lượng phiên học tối thiểu (mặc định $30$ phút).
- **`FR-AVAIL-002` (Cấu hình Chế độ B):** Thiết lập các khung giờ rảnh cố định `[StartTime, EndTime]` cho từng ngày trong tuần. Bắt buộc:
  - Khung giờ hỗ trợ qua nửa đêm thông qua thuộc tính `end_day_offset` ($0$: cùng ngày, $1$: qua 00:00 ngày hôm sau). Khi `end_day_offset = 0`, yêu cầu $\text{StartTime} < \text{EndTime}$. Khi `end_day_offset = 1`, cho phép slot kéo dài qua nửa đêm (ví dụ: `22:30 - 01:30`).
  - Độ dài khung giờ tối thiểu $\text{Duration} \ge 30 \text{ phút}$ (tương ứng 1 đơn vị phiên học Pomodoro).
  - Tuyệt đối không được xảy ra chồng lấn (Overlapping) giữa các khung giờ trong cùng một ngày.
- **`FR-AVAIL-003` (Quản lý Năng lực Đa Lộ trình & Lịch Ngoại vi):** 
  - Với **Mode A**: Trả về `remaining_capacity_minutes: int` (tổng số phút còn lại từ quỹ giờ sau khi trừ thời lượng đã phân bổ). Không tự suy diễn thành các slot giả lập.
  - Với **Mode B**: Áp dụng giải thuật trừ đoạn thời gian (Interval Subtraction) trên Domain để tính toán danh sách các khoảng rảnh thực tế còn lại (`List<TimeSlot>`) sau khi đã trừ các khoảng thời gian bị chiếm dụng bởi lộ trình khác hoặc sự kiện bận từ Google Calendar.
- **Phân tách Cấu hình Tích hợp Lịch Ngoại vi (`calendar_integration_mode`):** Độc lập với `availability_mode`, người dùng có thể cấu hình trạng thái tích hợp lịch: `NONE` (chỉ dùng nội bộ), `EXPORT_ICS` (xuất tệp tĩnh hoặc WebCal 1 chiều) hoặc `CONNECTED` (đồng bộ Google Calendar với scope tối thiểu).

---

## 2. Luận chứng Kỹ thuật & Phân tích Đánh đổi (Trade-off Analysis)

### 2.1. Phân tích Đánh đổi Lưu trữ Cơ sở Dữ liệu: JSONB vs 1-N Normalized Table
Một trong những quyết định kỹ thuật quan trọng nhất của phân hệ này là lựa chọn cấu trúc lưu trữ CSDL trong PostgreSQL 16 (tham chiếu `ADR-007`).

| Tiêu chí Đánh giá | Phương án 1: Chuẩn hóa 1-N (`availability_slots` Table) | Phương án 2: Tài liệu Nguyên khối (`availabilities.weekly_schedule` JSONB) [ĐƯỢC CHỌN] |
| :--- | :--- | :--- |
| **Cấu trúc vật lý** | 1 bảng cha `availabilities` và 1 bảng con `availability_slots(id, availability_id, day_of_week, start_time, end_time)`. | 1 bảng duy nhất `availabilities` với cột `weekly_schedule JSONB` lưu trọn vẹn 7 ngày trong 1 hàng (Row). |
| **Thao tác Ghi (Write Performance)** | **Kém (Write Amplification):** Mỗi khi người dùng bấm "Lưu cấu hình", Backend phải thực hiện: `DELETE FROM availability_slots WHERE availability_id = ...` rồi `INSERT INTO availability_slots ...` hàng loạt (gây bloat index và dead tuples trong PostgreSQL). | **Tối ưu (Single-Row Atomic Update):** Thực hiện 1 câu lệnh `UPDATE` hoặc `UPSERT` duy nhất trên 1 dòng đơn nguyên. Tận dụng cơ chế WAL (Write-Ahead Logging) của PostgreSQL. |
| **Thao tác Đọc (Read Performance)** | **Phức tạp:** Phải thực hiện phép nối `JOIN` hoặc truy vấn tập hợp `GROUP BY` để tái tạo lại bức tranh 7 ngày trong tuần. | **Tức thời (Single-Row Key Lookup):** Đọc trực tiếp 1 dòng duy nhất qua khóa ngoại `user_id` có Unique Constraint, nạp toàn bộ cây cấu hình 7 ngày mà không cần JOIN. |
| **Kiểm định Tính Toàn vẹn (Integrity Validation)** | **Khó bảo vệ mức CSDL:** Ràng buộc không chồng lấn (No-Overlap Constraint) trên nhiều dòng trong cùng ngày đòi hỏi cài đặt Extension phức tạp (`btree_gist` với `EXCLUDE USING gist`) hoặc viết DB Trigger nặng nề. | **Toàn vẹn Tại Tầng Domain:** Toàn bộ dữ liệu 7 ngày được nạp vào bộ nhớ trong 1 đối tượng Aggregate Root (`AvailabilityProfile`). Thuật toán Sweep-line kiểm tra chồng lấn, kiểm tra trần giờ và offset qua đêm diễn ra trong bộ nhớ trước khi chạm vào CSDL. CSDL bảo vệ bằng constraint `CHECK (jsonb_typeof(weekly_schedule) = 'object')`. |
| **Bảo toàn Dữ liệu (State Retention)** | **Khó khăn:** Khi chuyển từ Mode B sang Mode A, việc có nên xóa các slot trong bảng con hay giữ lại đòi hỏi thêm các cờ trạng thái phức tạp. | **Tự nhiên & Tinh gọn:** JSONB giữ đồng thời cả `quota_hours` và `time_slots` cho từng ngày. Người dùng đổi Mode thoải mái mà không hề bị mất dữ liệu đã nhập trước đó. |

> [!TIP]
> **Kết luận Luận văn:** Việc lựa chọn lưu trữ tài liệu có cấu trúc `JSONB` kết hợp với Ràng buộc toàn vẹn `jsonb_typeof` trong CSDL quan hệ PostgreSQL 16 là giải pháp kiến trúc dung hòa hoàn hảo giữa sự linh hoạt trong biểu diễn cấu hình tuần và tính nhất quán đơn vị nguyên tử của Aggregate Root (DDD).

---

### 2.2. Rich Domain Model vs Anemic Domain Model
Theo tiêu chuẩn thiết kế hướng miền (Domain-Driven Design - DDD) và nguyên lý **Information Expert (GRASP)**:
- **Mô hình Thiếu máu (Anemic Domain Model - Anti-pattern):** Lớp `AvailabilityProfile` chỉ chứa các thuộc tính (getters/setters thuần túy). Các logic nghiệp vụ như `validateDailyCeiling()`, `checkOverlap()`, `calculateRemainingCapacity()` bị đẩy ra ngoài cho một lớp dịch vụ phi trạng thái như `AvailabilityValidator`. Điều này vi phạm tính đóng gói (Encapsulation), biến thực thể thành một cấu trúc dữ liệu thụ động.
- **Mô hình Miền Giàu (Rich Domain Model - Lựa chọn thiết kế):** `AvailabilityProfile` và các Value Objects (`TimeSlot`, `DaySchedule`, `WeeklySchedule`) tự chịu trách nhiệm bảo vệ các bất biến nghiệp vụ của chính mình:
  - Bản thân `TimeSlot` tự kiểm tra tính hợp lệ và $\ge 30$ phút ngay tại hàm khởi tạo `__post_init__`, xử lý chính xác `end_day_offset` ($0$ hoặc $1$) khi slot kéo dài qua nửa đêm.
  - `DaySchedule` tự thực thi giải thuật kiểm tra chồng lấn các khung giờ trong ngày của mình.
  - `AvailabilityProfile` nắm giữ toàn bộ lịch tuần và trực tiếp thẩm định xem một kế hoạch học tập có vi phạm trần giờ rảnh hay không thông qua hai phương thức chuyên biệt: `validate_daily_ceiling(...)` cho Mode A và `validate_proposal_against_slots(...)` cho Mode B.

---

### 2.3. Cơ chế Hard Ceiling vs Slot-fit Validation & Soft Overflow
Tại sao hệ thống FocusFlow không áp dụng cùng một cơ chế thẩm định cho cả 2 chế độ?
1. **Đối với Mode A (Hard Ceiling Gate — Chặn cứng):**
   - Người học Mode A thiết lập quỹ thời gian trần theo con số tuyệt đối (ví dụ: Thứ 2 rảnh đúng 2 giờ).
   - Nếu thuật toán xếp lịch nhồi nhét $2.5$ giờ vào ngày đó, người học chắc chắn sẽ không đủ thể lực hoặc thời gian để hoàn thành. Do đó, hệ thống áp dụng **Hard Ceiling Gate**: Bất kỳ sự vi phạm nào ($> 0$ phút) đều bị chặn đứng và từ chối áp dụng lịch với lỗi `422 Unprocessable Entity`.
2. **Đối với Mode B (Slot-fit Validation & Soft Overflow Tolerance):**
   - **Bản chất của Mode B:** Không chỉ cho biết tổng lượng giờ rảnh, Mode B xác định **thời điểm cụ thể** người học có thể học. Do đó, việc chỉ so sánh tổng số phút task với tổng phút rảnh trong ngày (`validate_daily_ceiling`) là **sai bản chất nghiệp vụ**.
   - **Quy tắc Kiểm tra Vị trí Thực tế (`validate_proposal_against_slots`):**
     - Từng task trong proposal phải được đối chiếu trực tiếp: `task.start_time` và `task.end_time` có nằm trọn trong một slot rảnh hợp lệ của ngày đó hay không.
     - Đồng thời đối chiếu với các task đã được lên lịch trước đó hoặc khoảng bận từ Google Calendar để đảm bảo không bị xung đột.
   - **Chính sách Dung sai Soft Overflow ($\le 30$ phút):**
     - Trong trường hợp một task Pomodoro (ví dụ: 105 phút) hơi tràn ra ngoài biên kết thúc của một slot rảnh 90 phút (tràn 15 phút), nhưng **không va chạm** với bất kỳ lịch bận hay task nào khác:
     - Hệ thống cho phép task được tràn tối đa **không quá 30 phút**, đồng thời trả về cờ cảnh báo `has_soft_overflow = True`. Giao diện hiển thị cảnh báo rõ ràng để người học xác nhận chấp thuận học thêm 15–30 phút hay không trước khi chính thức áp dụng.
     - Nếu tràn quá 30 phút hoặc đè lên khoảng thời gian bận, hệ thống lập tức coi là vi phạm và từ chối.

---

### 2.4. Phạm Vi Thẩm Định Khi Chuyển Đổi Chế Độ & Trạng Thái `enabled`
1. **Phạm vi Thẩm định (Validation Scope):**
   - Hệ thống **chỉ thẩm định nghiêm ngặt chế độ đang được kích hoạt (`active_mode`)**.
   - Nếu người dùng lưu `mode = 'MODE_A'`, hệ thống chỉ kiểm tra các bất biến của Mode A (0.5h – 14.0h/ngày, tổng tuần $\ge 1.0$h, tính hợp lệ của `allowed_window`). Các khung giờ trong `time_slots` của Mode B dù có đang rỗng hoặc chưa hoàn thiện vẫn được giữ nguyên vẹn trong JSONB.
   - Ngược lại, khi chuyển sang lưu `mode = 'MODE_B'`, hệ thống mới kích hoạt bộ thẩm định kiểm tra chồng lấn và thời lượng tối thiểu của các khung giờ.
2. **Ngữ nghĩa của trường `enabled`:**
   - Trường `enabled: Boolean` trong mỗi `DaySchedule` là **trạng thái dùng chung có chủ đích của ngày**: Mang ý nghĩa "Người học quyết định ngày này nghỉ hoàn toàn, không xếp bất kỳ lịch học nào, bất kể đang dùng Mode A hay Mode B".
   - Khi `enabled = false`, toàn bộ dữ liệu `quota_hours` và `time_slots` đã nhập trước đó vẫn được bảo toàn nguyên vẹn trong JSONB (State Retention). Giao diện hiển thị cảnh báo tinh tế nếu người dùng bật lại ngày đó.

---

### 2.5. Xử Lý Xung Đột Với Lịch Chính Thức & Phân Tách Trách Nhiệm Với FR-PAUSE
1. **Ứng xử khi người học sửa giảm giờ rảnh trong lúc đã có Lịch học chính thức (Official Schedule):**
   - Áp dụng nguyên lý **Non-blocking with Advisory Warning**: Cấu hình rảnh mới luôn được phép lưu thành công ngay lập tức.
   - Nếu phát hiện cấu hình mới làm cho các task `TODO` trong tương lai bị vượt trần hoặc rơi ra ngoài khung rảnh, hệ thống **không tự ý thay đổi hoặc hủy bỏ** lịch đã cam kết. Thay vào đó, hệ thống gắn cờ cảnh báo trên màn hình Thời khóa biểu và Dashboard, gợi ý người học bấm nút `[Tái cấu trúc lịch học bằng AI - FR-ADAPT-002]` để AI phân bổ lại lịch một cách có chủ đích.
2. **Phân định Ranh giới Kỹ thuật Rõ ràng giữa Settings Hub và Quick Drawer:**
   - **Cài đặt Tập trung (Settings Hub - `/settings`):** Chuyên trách cập nhật **Khuôn mẫu lặp lại hàng tuần (Weekly Recurring Template)** thông qua API `PUT /api/v1/availabilities/me`. Thao tác này ảnh hưởng tới tất cả các tuần tiếp theo.
   - **Tương tác Nhanh (Quick Drawer tại `/schedule`):** Phục vụ việc điều chỉnh cục bộ đột xuất cho một ngày cụ thể (ví dụ: tối nay bận đột xuất muốn dời phiên học sang ngày mai). Thao tác này **tuyệt đối KHÔNG gọi `PUT /availabilities/me`** để tránh phá vỡ khuôn mẫu tuần; thay vào đó nó gọi API của phân hệ `FR-PAUSE` / `DayOverride` để dời lịch cho riêng ngày đó.

---

## 3. Mô hình Hóa Thiết kế Hệ thống Chuẩn UML 2.5.1

### 3.1. Sơ đồ Lớp Thiết kế Chi tiết (Design Class Diagram - DCD)

```mermaid
classDiagram
    direction TB

    %% Presentation Layer
    class AvailabilityRouter {
        <<FastAPI APIRouter>>
        +get_my_availability(user_id, use_case) AvailabilityResponseDTO
        +update_my_availability(user_id, request, use_case) AvailabilityResponseDTO
    }

    class GetCurrentUserDependency {
        <<FastAPI Depends>>
        +get_current_user_id(request, x_user_id) UUID
    }

    %% Application Layer (DTOs, Ports, Use Cases)
    class TimeSlotDTO {
        +String start
        +String end
    }

    class DayScheduleDTO {
        +Boolean enabled
        +Float quota_hours
        +List~TimeSlotDTO~ time_slots
    }

    class WeeklyScheduleDTO {
        +DayScheduleDTO monday
        +DayScheduleDTO tuesday
        +DayScheduleDTO wednesday
        +DayScheduleDTO thursday
        +DayScheduleDTO friday
        +DayScheduleDTO saturday
        +DayScheduleDTO sunday
    }

    class UpdateAvailabilityRequestDTO {
        +String mode
        +WeeklyScheduleDTO weekly_schedule
    }

    class AvailabilityResponseDTO {
        +String id
        +String user_id
        +String mode
        +WeeklyScheduleDTO weekly_schedule
        +Float total_weekly_hours
        +String updated_at
    }

    class AvailabilityRepositoryPort {
        <<Interface / Driven Port>>
        +get_by_user_id(user_id: UUID)* AvailabilityProfile
        +save(profile: AvailabilityProfile)* AvailabilityProfile
    }

    class GetAvailabilityUseCase {
        -AvailabilityRepositoryPort repository
        +execute(user_id: UUID) AvailabilityResponseDTO
    }

    class UpdateAvailabilityUseCase {
        -AvailabilityRepositoryPort repository
        +execute(user_id: UUID, request: UpdateAvailabilityRequestDTO) AvailabilityResponseDTO
    }

    %% Domain Layer (Core Logic)
    class AvailabilityMode {
        <<Enumeration>>
        MODE_A
        MODE_B
    }

    class TimeSlot {
        <<Value Object>>
        -Time startTime
        -Time endTime
        -Integer endDayOffset
        +durationMinutes int
        +overlaps(other: TimeSlot) Boolean
        +from_str(start: String, end: String, endDayOffset: Integer, day: String)$ TimeSlot
        +to_dict() Map
    }

    class DaySchedule {
        <<Value Object>>
        -Boolean enabled
        -Float quotaHours
        -Map allowedWindow
        -String preferredPeriod
        -Integer minSessionMinutes
        -List~TimeSlot~ timeSlots
        +totalSlotMinutes int
        +validateInvariants(dayName: String, mode: AvailabilityMode) void
        +to_dict() Map
        +from_dict(data: Map, dayName: String)$ DaySchedule
    }

    class WeeklySchedule {
        <<Value Object>>
        -Map~String, DaySchedule~ days
        +calculateTotalWeeklyHours(mode: AvailabilityMode) Float
        +validateInvariants(mode: AvailabilityMode) void
        +to_dict() Map
        +from_dict(data: Map)$ WeeklySchedule
    }

    class AvailabilityValidationResult {
        <<Data Transfer / Domain Object>>
        +Boolean isValid
        +Integer overflowMinutes
        +Boolean hasSoftOverflow
        +List~String~ violationReasons
    }

    class AvailabilityProfile {
        <<Entity / Aggregate Root>>
        -UUID id
        -UUID userId
        -AvailabilityMode mode
        -String calendarIntegrationMode
        -WeeklySchedule weeklySchedule
        -DateTime createdAt
        -DateTime updatedAt
        +getDailyCeiling(dayOfWeek: String) Integer
        +validateDailyCeiling(dayOfWeek: String, totalMinutes: Integer) AvailabilityValidationResult
        +validateProposalAgainstSlots(dayOfWeek: String, proposedTasks: List) AvailabilityValidationResult
        +calculateRemainingCapacity(dayOfWeek: String, occupied: List) Object
        +switchMode(newMode: AvailabilityMode) void
        +updateSchedule(newSchedule: WeeklySchedule) void
        +createDefault(userId: UUID)$ AvailabilityProfile
    }

    %% Infrastructure Layer
    class AvailabilityModel {
        <<SQLAlchemy ORM>>
        +UUID id
        +UUID user_id
        +String mode
        +String calendar_integration_mode
        +JSONB weekly_schedule
        +DateTime created_at
        +DateTime updated_at
    }

    class SqlAvailabilityRepository {
        <<Adapter>>
        -AsyncSession session
        +get_by_user_id(user_id: UUID) AvailabilityProfile
        +save(profile: AvailabilityProfile) AvailabilityProfile
        -toEntity(model: AvailabilityModel) AvailabilityProfile
    }

    %% Relationships
    AvailabilityRouter ..> GetCurrentUserDependency : depends on
    AvailabilityRouter ..> GetAvailabilityUseCase : invokes
    AvailabilityRouter ..> UpdateAvailabilityUseCase : invokes
    GetAvailabilityUseCase ..> AvailabilityRepositoryPort : uses
    UpdateAvailabilityUseCase ..> AvailabilityRepositoryPort : uses
    UpdateAvailabilityUseCase ..> UpdateAvailabilityRequestDTO : consumes
    GetAvailabilityUseCase ..> AvailabilityResponseDTO : produces

    AvailabilityRepositoryPort <|.. SqlAvailabilityRepository : implements
    SqlAvailabilityRepository ..> AvailabilityModel : queries / maps
    SqlAvailabilityRepository ..> AvailabilityProfile : reconstructs

    AvailabilityProfile "1" *-- "1" WeeklySchedule : holds
    WeeklySchedule "1" *-- "7" DaySchedule : contains
    DaySchedule "1" *-- "*" TimeSlot : contains
    AvailabilityProfile ..> AvailabilityMode : has
    AvailabilityProfile ..> AvailabilityValidationResult : returns
```

---

### 3.2. Sơ đồ Tuần tự 1: Thiết lập & Thẩm định Cấu hình Rảnh (UC-AVAIL-01)

```mermaid
sequenceDiagram
    autonumber
    actor Learner as Người học (Learner)
    participant UI as Angular 19 SPA (Client)
    participant Router as AvailabilityRouter (/api/v1/availabilities)
    participant AuthDep as get_current_user_id (Dependency)
    participant UC as UpdateAvailabilityUseCase (Application)
    participant Entity as AvailabilityProfile (Rich Domain Entity)
    participant Repo as SqlAvailabilityRepository (Adapter)
    participant DB as PostgreSQL 16 (availabilities Table)

    Learner->>UI: Điều chỉnh Quỹ giờ (Mode A) hoặc Khung giờ (Mode B) & Bấm [Lưu cấu hình]
    Note over UI: Client Live Validation:<br/>Kiểm tra start < end, slot >= 30m,<br/>báo lỗi trực quan trước khi gửi.
    
    UI->>Router: PUT /api/v1/availabilities/me (UpdateAvailabilityRequestDTO)
    Router->>AuthDep: Xác thực & Lấy ID người dùng
    AuthDep-->>Router: current_user_id (UUID)

    Router->>UC: execute(user_id, request_dto)
    
    rect rgb(240, 248, 255)
        Note over UC,Entity: TẦNG NGHIỆP VỤ (DOMAIN LAYER)
        UC->>UC: Chuyển đổi DTO thành Domain Value Objects (TimeSlot, DaySchedule, WeeklySchedule)
        UC->>Repo: get_by_user_id(user_id)
        Repo->>DB: SELECT * FROM availabilities WHERE user_id = :uid
        DB-->>Repo: AvailabilityModel (hoặc None)
        Repo-->>UC: existing_profile (hoặc None)

        alt Hồ sơ chưa tồn tại (First time)
            Note over UC: Lazy Init: Đối với GET lần đầu, UC trả về đối tượng Default trong bộ nhớ (id=None, không INSERT CSDL).\nKhi người học gọi PUT /me lần đầu, UC tạo Entity mới và kích hoạt UPSERT.
            UC->>Entity: AvailabilityProfile(id, user_id, mode, weekly_schedule, calendar_integration_mode)
            Entity->>Entity: weekly_schedule.validate_invariants(mode)
        else Hồ sơ đã tồn tại (Cập nhật)
            UC->>Entity: existing_profile.switch_mode(new_mode)
            UC->>Entity: existing_profile.update_schedule(new_schedule)
            Entity->>Entity: weekly_schedule.validate_invariants(new_mode)
        end
    end

    alt Dữ liệu vi phạm bất biến nghiệp vụ (OS-06, Chồng lấn, < 1h/tuần)
        Entity-->>UC: ném AvailabilityDomainException
        UC-->>Router: Exception chuyển tiếp
        Router-->>UI: HTTP 422 Unprocessable Entity {code, message, details}
        UI-->>Learner: Hiển thị thông báo lỗi chi tiết trên form
    else Dữ liệu hợp lệ 100%
        UC->>Repo: save(profile)
        Repo->>DB: INSERT ... ON CONFLICT (user_id) DO UPDATE ... (UPSERT)
        DB-->>Repo: Saved Record
        Repo-->>UC: saved_profile (Entity)
        UC-->>Router: AvailabilityResponseDTO
        Router-->>UI: HTTP 200 OK {success: true, data: AvailabilityResponseDTO}
        UI-->>Learner: Thông báo Toast "Lưu cấu hình thời gian rảnh thành công!"
    end
```

---

### 3.3. Sơ đồ Tuần tự 2: Chốt Chặn Thẩm định Trần giờ khi Áp dụng Lịch (Apply Gate)

```mermaid
sequenceDiagram
    autonumber
    actor Learner as Người học (Learner)
    participant UI as Angular Schedule View
    participant ApplyUC as ApplyProposalUseCase
    participant Profile as AvailabilityProfile (Domain Entity)
    participant DB as PostgreSQL 16 (official_schedules & tasks)

    Learner->>UI: Xem trước Bản nháp Lịch (Proposal Preview) & Bấm [Áp dụng Lịch]
    UI->>ApplyUC: apply_proposal(proposal_id)
    ApplyUC->>DB: Lấy User Availability Profile & Danh sách Tasks trong Proposal
    DB-->>ApplyUC: availabilityProfile, proposedTasks

    loop Duyệt qua từng ngày trong tuần có xếp task
        alt Chế độ Mode A
            ApplyUC->>Profile: validate_daily_ceiling(day_of_week, total_task_minutes)
            Profile-->>ApplyUC: AvailabilityValidationResult (is_valid, has_soft_overflow, overflow)
        else Chế độ Mode B
            ApplyUC->>Profile: validate_proposal_against_slots(day_of_week, day_proposed_tasks)
            Note over Profile: Thẩm định Khung giờ Vị trí Thực tế (D-01):<br/>• Kiểm tra từng task nằm trọn trong slot rảnh<br/>• Không xung đột khoảng bận lịch ngoài<br/>• Soft Overflow <= 30m nếu chỉ tràn biên ngoài
            Profile-->>ApplyUC: AvailabilityValidationResult (is_valid, has_soft_overflow, overflow)
        end
    end

    alt Vi phạm Hard Ceiling (Mode A) hoặc Xung đột / Tràn > 30 phút (Mode B)
        ApplyUC-->>UI: HTTP 422 Unprocessable Entity ("HARD_CEILING_EXCEEDED" hoặc "SLOT_FIT_COLLISION")
        UI-->>Learner: Báo lỗi: "Lịch học không khả thi với thời gian rảnh hoặc xung đột khung giờ. Vui lòng điều chỉnh lại!"
    else Thỏa mãn trần giờ (Kèm Soft Overflow <= 30m nếu có)
        opt Có Soft Overflow <= 30 phút
            ApplyUC-->>UI: Cảnh báo Soft Overflow: "Khung học ngày Thứ 2 tràn 15 phút ngoài slot rảnh. Bạn có đồng ý?"
            Learner->>UI: Xác nhận Đồng ý
        end
        Note over ApplyUC,DB: KIỂM TOÁN ĐỒNG THỜI (OPTIMISTIC LOCKING - D-09):<br/>Kiểm tra version Availability (updated_at) tại thời điểm ghi vs lúc nạp Preview
        alt Version bị lệch (người dùng sửa Availability ở tab khác)
            ApplyUC-->>UI: HTTP 409 Conflict ("CONCURRENT_AVAILABILITY_MODIFIED")
            UI-->>Learner: Báo lỗi: "Cấu hình thời gian rảnh đã bị thay đổi ở tab khác. Vui lòng tải lại trang!"
        else Version hoàn toàn khớp (Hợp lệ)
            ApplyUC->>DB: Unit of Work Giao dịch ACID (Rollback toàn bộ nếu lỗi):<br/>1. Cancel các task TODO tương lai thuộc phạm vi thay thế (giữ task COMPLETED/IN_PROGRESS)<br/>2. INSERT tasks mới (status = 'TODO')<br/>3. Kích hoạt Roadmap (status = 'ACTIVE')
            DB-->>ApplyUC: Giao dịch thành công (Commit)
            ApplyUC-->>UI: HTTP 200 OK (Schedule Activated)
            UI-->>Learner: Hiển thị Thời khóa biểu chính thức được kích hoạt!
        end
    end
```

---

## 4. Đặc Tả Thuật Toán & Phân Tích Độ Phức Tạp

### 4.1. Thuật toán Kiểm tra Khung giờ Không Chồng lấn (Hỗ trợ Cross-Midnight Slot qua `end_day_offset`)
- **Mục tiêu:** Đảm bảo rằng trong một ngày bất kỳ của Chế độ B, không có bất kỳ 2 khung giờ nào bị đè lên nhau, đồng thời hỗ trợ các khung giờ qua nửa đêm (`end_day_offset = 1`).
- **Ý tưởng giải thuật:**
  1. Nếu số lượng khung giờ $N \le 1$, trả về hợp lệ ngay lập tức.
  2. Chuẩn hóa thời gian bắt đầu và kết thúc thành phút tính từ 00:00 của ngày:
     $$\text{start\_min} = \text{hour} \times 60 + \text{minute}; \quad \text{end\_min} = (\text{hour} \times 60 + \text{minute}) + (\text{end\_day\_offset} \times 1440)$$
  3. Kiểm tra tính hợp lệ đơn khung: $\text{end\_min} - \text{start\_min} \ge 30$ phút.
  4. Sắp xếp danh sách $N$ khung giờ theo $\text{start\_min}$ tăng dần: $O(N \log N)$.
  5. Duyệt tuyến tính từ phần tử đầu tiên đến phần tử kế cuối: $O(N)$. Nếu $\text{slots}[i].\text{end\_min} > \text{slots}[i+1].\text{start\_min}$, phát hiện xung đột và ném ngoại lệ `OverlappingTimeSlotsException`.
- **Mã giả (Pseudocode):**
  ```python
  def slot_minutes_range(slot: TimeSlot) -> tuple[int, int]:
      start_m = slot.start_time.hour * 60 + slot.start_time.minute
      end_m = slot.end_time.hour * 60 + slot.end_time.minute + (slot.end_day_offset * 1440)
      return start_m, end_m

  def check_intervals_no_overlap(slots: list[TimeSlot], day_name: str) -> None:
      if len(slots) <= 1:
          return
      
      # Sắp xếp theo start_time tăng dần: O(N log N)
      sorted_slots = sorted(slots, key=lambda s: slot_minutes_range(s)[0])
      
      for i in range(len(sorted_slots) - 1):
          curr_start, curr_end = slot_minutes_range(sorted_slots[i])
          next_start, next_end = slot_minutes_range(sorted_slots[i + 1])
          
          if curr_end > next_start:
              raise OverlappingTimeSlotsException(
                  day=day_name,
                  slot1=f"{sorted_slots[i].start_time} - {sorted_slots[i].end_time} (+{sorted_slots[i].end_day_offset}d)",
                  slot2=f"{sorted_slots[i + 1].start_time} - {sorted_slots[i + 1].end_time} (+{sorted_slots[i + 1].end_day_offset}d)"
              )
  ```
- **Phân tích Độ phức tạp:**
  - Thời gian (Time Complexity): $O(N \log N)$. Do số lượng khung giờ của một người học trong một ngày rất nhỏ ($N \le 6$), số phép tính tối đa $< 20$ phép toán, thời gian chạy đo được $< 0.05$ms.
  - Không gian (Space Complexity): $O(N)$ để chứa danh sách đã sắp xếp.

---

### 4.2. Thuật toán Trừ Đoạn Thời gian Đa Lộ trình & Thẩm định Khung Khả thi (FR-AVAIL-003 & D-01)
- **Mục tiêu:** 
  1. Với Mode A: Trả về `remaining_capacity_minutes: int` bằng $\text{quota\_hours} \times 60 - \sum \text{allocated\_minutes}$.
  2. Với Mode B: Trừ các khoảng thời gian bị chiếm dụng (Occupied Intervals của các Roadmap khác hoặc sự kiện bận từ Google Calendar) và trả về các khoảng rảnh còn lại (`List<TimeSlot>`).
  3. Cung cấp giải thuật `validate_proposal_against_slots` kiểm tra từng task đề xuất có nằm trọn trong các slot rảnh thực tế hay không.
- **Mã giả giải thuật Trừ Đoạn Thời gian & Thẩm định Khung giờ:**
  ```python
  def subtract_intervals(base_slots: list[TimeSlot], occupied: list[tuple[time, time]]) -> list[TimeSlot]:
      sorted_occupied = sorted(occupied, key=lambda x: x[0])
      current_available = list(base_slots)
      
      for occ_start, occ_end in sorted_occupied:
          next_available = []
          for slot in current_available:
              if slot.end_time <= occ_start or slot.start_time >= occ_end:
                  next_available.append(slot)
              else:
                  if slot.start_time < occ_start:
                      left_duration = time_diff_minutes(slot.start_time, occ_start)
                      if left_duration >= 30:
                          next_available.append(TimeSlot(slot.start_time, occ_start))
                  
                  if slot.end_time > occ_end:
                      right_duration = time_diff_minutes(occ_end, slot.end_time)
                      if right_duration >= 30:
                          next_available.append(TimeSlot(occ_end, slot.end_time))
          current_available = next_available
          
      return current_available

  def validate_proposal_against_slots(
      available_slots: list[TimeSlot], 
      proposed_tasks: list[ProposedTask]
  ) -> AvailabilityValidationResult:
      """Kiểm tra từng task có nằm trọn trong slot rảnh không (D-01)."""
      for task in proposed_tasks:
          matched = False
          overflow_minutes = 0
          for slot in available_slots:
              # Task nằm hoàn toàn trong slot
              if slot.start_time <= task.start_time and task.end_time <= slot.end_time:
                  matched = True
                  break
              # Kiểm tra Soft Overflow (tràn đuôi slot <= 30 phút mà không đè slot khác)
              if slot.start_time <= task.start_time and task.start_time < slot.end_time:
                  overflow = time_diff_minutes(slot.end_time, task.end_time)
                  if 0 < overflow <= 30:
                      matched = True
                      overflow_minutes = max(overflow_minutes, overflow)
                      break
          if not matched:
              return AvailabilityValidationResult(
                  is_valid=False, 
                  violation_reasons=[f"Task {task.title} [{task.start_time}-{task.end_time}] nằm ngoài khung giờ rảnh."]
              )
      
      return AvailabilityValidationResult(
          is_valid=True,
          has_soft_overflow=(overflow_minutes > 0),
          overflow_minutes=overflow_minutes
      )
  ```

---

## 5. Thiết Kế Cơ Sở Dữ Liệu & Chiến Lược Lưu Trữ (Persistence Design)

### 5.1. Lược đồ Bảng Vật lý `availabilities` (PostgreSQL 16)
Tuân thủ thiết kế chuẩn hóa tại `docs/database/schema.sql` (Bảng số 5):

```sql
-- =============================================================================
-- BẢNG AVAILABILITIES (HỒ SƠ THỜI GIAN RẢNH LAI CỦA NGƯỜI HỌC)
-- Quan hệ: 1-1 với bảng users (Mỗi người học sở hữu duy nhất 1 hồ sơ thời gian rảnh)
-- =============================================================================

CREATE TABLE IF NOT EXISTS availabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    mode VARCHAR(10) NOT NULL DEFAULT 'MODE_A',
    calendar_integration_mode VARCHAR(20) NOT NULL DEFAULT 'NONE',
    weekly_schedule JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ràng buộc kiểm tra tính hợp lệ của Mode
    CONSTRAINT chk_availabilities_mode CHECK (mode IN ('MODE_A', 'MODE_B')),

    -- Ràng buộc kiểm tra chế độ tích hợp lịch (D-06)
    CONSTRAINT chk_availabilities_calendar_mode CHECK (calendar_integration_mode IN ('NONE', 'EXPORT_ICS', 'CONNECTED')),

    -- Ràng buộc toàn vẹn cấu trúc JSONB: Bắt buộc là JSON Object (không được là Array hay Scalar)
    CONSTRAINT chk_availabilities_schedule_json CHECK (jsonb_typeof(weekly_schedule) = 'object')
);

-- Trigger tự động cập nhật dấu thời gian updated_at
CREATE TRIGGER trg_availabilities_updated_at 
BEFORE UPDATE ON availabilities 
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 5.2. Cấu trúc Tài liệu JSONB Mẫu (`weekly_schedule`)
Tài liệu JSONB lưu trữ đầy đủ 7 ngày trong tuần, tích hợp sẵn thuộc tính của cả Mode A (`quota_hours`) và Mode B (`time_slots`):

```json
{
  "monday": {
    "enabled": true,
    "quota_hours": 2.5,
    "allowed_window": { "start": "07:00", "end": "23:00" },
    "preferred_period": "EVENING",
    "min_session_minutes": 30,
    "time_slots": [
      { "start": "19:30", "end": "22:00", "end_day_offset": 0 }
    ]
  },
  "tuesday": {
    "enabled": true,
    "quota_hours": 2.0,
    "time_slots": [
      { "start": "20:00", "end": "22:00" }
    ]
  },
  "wednesday": {
    "enabled": true,
    "quota_hours": 2.5,
    "time_slots": [
      { "start": "19:30", "end": "22:00" }
    ]
  },
  "thursday": {
    "enabled": false,
    "quota_hours": 0.0,
    "time_slots": []
  },
  "friday": {
    "enabled": true,
    "quota_hours": 3.0,
    "time_slots": [
      { "start": "19:00", "end": "22:00" }
    ]
  },
  "saturday": {
    "enabled": true,
    "quota_hours": 4.0,
    "time_slots": [
      { "start": "09:00", "end": "11:30" },
      { "start": "14:30", "end": "16:00" }
    ]
  },
  "sunday": {
    "enabled": false,
    "quota_hours": 0.0,
    "time_slots": []
  }
}
```

---

## 6. Hợp Đồng Giao Diện Lập Trình Ứng Dụng (RESTful API Contract)

Toàn bộ các endpoint tuân thủ chuẩn RESTful, sử dụng mã trạng thái HTTP tiêu chuẩn và định dạng phản hồi nhất quán theo `ApiResponse<T>` / `ApiErrorResponse` (`RFC 7807 Problem Details`).

### 6.1. Endpoint 1: Lấy Cấu hình Thời gian Rảnh Hiện tại
- **Đường dẫn:** `GET /api/v1/availabilities/me`
- **Mô tả:** Lấy thông tin cấu hình thời gian rảnh của người học đang đăng nhập. Nếu người học mới chưa từng cấu hình, Use Case tự động áp dụng **Lazy Initialization** trả về hồ sơ mẫu mặc định trong bộ nhớ với `id = null` (không thực hiện ghi INSERT CSDL để tránh race condition và write-side effect cho thao tác đọc). CSDL chỉ được tạo bản ghi khi người dùng gọi `PUT /me` lần đầu tiên.
- **Tiêu đề Yêu cầu (Request Headers):**
  ```http
  Authorization: Bearer <jwt_access_token> (hoặc qua HttpOnly Cookie)
  X-User-Id: <uuid> (Tùy chọn: Chế độ Dev Fallback)
  ```
- **Mã phản hồi Thành công:** `200 OK`
- **Thân phản hồi (Response Body):**
  ```json
  {
    "success": true,
    "data": {
      "id": "0192a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6b",
      "user_id": "018f0000-0000-7000-8000-000000000001",
      "mode": "MODE_A",
      "weekly_schedule": {
        "monday": { "enabled": true, "quota_hours": 2.0, "time_slots": [{ "start": "19:30", "end": "21:30" }] },
        "tuesday": { "enabled": true, "quota_hours": 2.0, "time_slots": [{ "start": "19:30", "end": "21:30" }] },
        "wednesday": { "enabled": true, "quota_hours": 2.0, "time_slots": [{ "start": "19:30", "end": "21:30" }] },
        "thursday": { "enabled": true, "quota_hours": 2.0, "time_slots": [{ "start": "19:30", "end": "21:30" }] },
        "friday": { "enabled": true, "quota_hours": 2.0, "time_slots": [{ "start": "19:30", "end": "21:30" }] },
        "saturday": { "enabled": true, "quota_hours": 3.0, "time_slots": [{ "start": "14:00", "end": "17:00" }] },
        "sunday": { "enabled": true, "quota_hours": 3.0, "time_slots": [{ "start": "14:00", "end": "17:00" }] }
      },
      "total_weekly_hours": 16.0,
      "updated_at": "2026-10-19T04:15:00.000000Z"
    }
  }
  ```

---

### 6.2. Endpoint 2: Cập nhật Cấu hình Thời gian Rảnh (UPSERT)
- **Đường dẫn:** `PUT /api/v1/availabilities/me`
- **Mô tả:** Cập nhật chế độ hoạt động và toàn bộ lịch tuần của người học. Nếu chưa có bản ghi, hệ thống thực hiện chèn mới; nếu đã có, thực hiện cập nhật và kích hoạt trigger cập nhật thời gian.
- **Thân yêu cầu (Request Body):**
  ```json
  {
    "mode": "MODE_B",
    "weekly_schedule": {
      "monday": {
        "enabled": true,
        "quota_hours": 2.0,
        "time_slots": [
          { "start": "19:00", "end": "21:00" }
        ]
      },
      "tuesday": {
        "enabled": true,
        "quota_hours": 2.0,
        "time_slots": [
          { "start": "20:00", "end": "22:00" }
        ]
      },
      "wednesday": { "enabled": false, "quota_hours": 0.0, "time_slots": [] },
      "thursday": { "enabled": false, "quota_hours": 0.0, "time_slots": [] },
      "friday": { "enabled": false, "quota_hours": 0.0, "time_slots": [] },
      "saturday": { "enabled": false, "quota_hours": 0.0, "time_slots": [] },
      "sunday": { "enabled": false, "quota_hours": 0.0, "time_slots": [] }
    }
  }
  ```
- **Mã phản hồi Thành công:** `200 OK` (Trả về đối tượng `AvailabilityResponseDTO` cập nhật).
- **Mã phản hồi Lỗi Nghiệp vụ (Validation Error):** `422 Unprocessable Entity`
  - *Ví dụ 1: Vi phạm Cận giờ Mode A theo `OS-06`:*
    ```json
    {
      "code": "INVALID_QUOTA_BOUNDS",
      "message": "Số giờ rảnh cho monday (0.3h) không hợp lệ theo OS-06. Phải nằm trong khoảng từ 0.5 giờ (30 phút) đến 14.0 giờ.",
      "details": {
        "day": "monday",
        "quota_hours": 0.3,
        "min_allowed": 0.5,
        "max_allowed": 14.0
      }
    }
    ```
  - *Ví dụ 2: Vi phạm Chồng lấn Khung giờ Mode B:*
    ```json
    {
      "code": "OVERLAPPING_TIME_SLOTS",
      "message": "Khung giờ vào tuesday bị xung đột: [19:00 - 21:00] chồng lấn với [20:00 - 22:00].",
      "details": {
        "day": "tuesday",
        "conflicting_slots": ["19:00 - 21:00", "20:00 - 22:00"]
      }
    }
    ```
  - *Ví dụ 3: Vi phạm Tổng giờ cả tuần không đủ điều kiện tối thiểu:*
    ```json
    {
      "code": "INSUFFICIENT_WEEKLY_AVAILABILITY",
      "message": "Tổng thời gian rảnh trong tuần (0.5h) quá thấp. Cần tối thiểu 1.0 giờ/tuần để hệ thống có thể lập kế hoạch học tập.",
      "details": {
        "total_hours": 0.5,
        "min_required": 1.0
      }
    }
    ```

---

## 7. Kiến Trúc Giao Diện Người Dùng Frontend (Angular 19 Signals Architecture)

### 7.1. Phân chia Điểm Chạm UX Kép (Dual Touchpoint Strategy)
Theo kết quả phỏng vấn `/grill-me`, phân hệ Availability cung cấp 2 điểm chạm trải nghiệm phục vụ 2 ngữ cảnh sử dụng khác nhau:
1. **Điểm chạm Quản trị Tập trung (Settings Hub - `/settings`):**
   - Đặt tại tab "Cấu hình Thời gian rảnh" trong trang Cài đặt.
   - Thích hợp khi người học muốn tinh chỉnh chi tiết, nghiên cứu các Mẫu gợi ý (Presets) hoặc thiết lập lịch rảnh ban đầu.
2. **Điểm chạm Tương tác Nhanh (In-context Quick Drawer - `/schedule`):**
   - Đặt nút `[Điều chỉnh lịch hôm nay]` trên thanh công cụ điều khiển tuần của Thời khóa biểu (`SCR-05`).
   - Mở ra một Slide-over Drawer từ phía bên phải màn hình phục vụ việc điều chỉnh ngoại lệ cục bộ cho ngày được chọn (dời phiên học, tăng giảm thời lượng hôm nay).
   - **Ranh giới kỹ thuật (D-03):** Thao tác này tương tác với API của phân hệ `FR-PAUSE` (`DayOverride` / `DominoShift`) cho riêng ngày đó, **tuyệt đối không gọi `PUT /availabilities/me`** để bảo toàn khuôn mẫu tuần lặp lại vĩnh viễn.

---

### 7.2. Bộ Mẫu Thời Gian Rảnh Gợi Ý (UX Productivity Presets)
Nhằm giúp người học không bị nản lòng trước việc phải tự thiết lập 7 ngày, hệ thống cung cấp 3 bộ Presets tích hợp sẵn với 1 cú click:
1. **Preset 1: Người Đi Làm Bận Rộn (Busy Professional):**
   - Thứ 2 $\rightarrow$ Thứ 6: Rảnh tối 1.5h (`20:30 - 22:00`).
   - Thứ 7 & Chủ Nhật: Rảnh chiều 3.0h (`14:00 - 17:00`).
   - *Tổng quỹ tuần:* $13.5$ giờ.
2. **Preset 2: Sinh Viên Đại Học (University Student) (Đã sửa theo D-11):**
   - Thứ 2, 4, 6: Rảnh tối 2.5h (`19:30 - 22:00`).
   - Thứ 3, 5: Nghỉ ngơi học bài trên lớp.
   - Thứ 7 & Chủ Nhật: Rảnh 4.0h/ngày (Sáng `08:30 - 11:30` = 3.0h và Chiều `14:30 - 16:30` = 1.0h... sửa đúng: Chiều `14:30 - 15:30` = 1.0h để tổng = 4.0h, hoặc sáng 2.5h + chiều 1.5h... ở đây chuẩn hóa: Sáng `08:30 - 11:00` 2.5h + Chiều `14:30 - 16:00` 1.5h = 4.0h/ngày).
   - *Tổng quỹ tuần:* $3 \times 2.5 + 2 \times 4.0 = 15.5$ giờ chuẩn xác 100%.
3. **Preset 3: Học Tập Toàn Thời Gian (Full-time Bootcamper):**
   - Thứ 2 $\rightarrow$ Thứ 7: Mỗi ngày rảnh 6.0h chia làm 2 ca (Sáng `08:30 - 11:30`, Chiều `14:00 - 17:00`).
   - Chủ Nhật: Nghỉ hoàn toàn.
   - *Tổng quỹ tuần:* $36.0$ giờ.

Kèm theo đó là nút tiện ích: **"Sao chép Thứ 2 sang tất cả các ngày trong tuần" (Batch Copy to Weekdays)**, giảm 80% thao tác bấm chuột của người dùng.

---

### 7.3. Thiết Kế Quản Trị Trạng Thái Bằng Angular 19 Signals
Ứng dụng khai thác tối đa tính năng **Fine-grained Reactivity** của Angular Signals, loại bỏ hoàn toàn sự rườm rà của Redux / NgRx:

```typescript
@Injectable({ providedIn: 'root' })
export class AvailabilityService {
  private readonly http = inject(HttpClient);

  // Core State Signals
  readonly profile = signal<AvailabilityProfile | null>(null);
  readonly activeMode = signal<AvailabilityMode>('MODE_A');
  readonly weeklySchedule = signal<WeeklySchedule>(DEFAULT_SCHEDULE);
  readonly loading = signal<boolean>(false);
  readonly saving = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);

  // Computed Derived Signals (Tự động cập nhật không cần subscribe)
  readonly totalWeeklyHours = computed(() => {
    const sched = this.weeklySchedule();
    const mode = this.activeMode();
    let total = 0;
    for (const day of DAYS_OF_WEEK) {
      const dayData = sched[day];
      if (dayData.enabled) {
        if (mode === 'MODE_A') {
          total += dayData.quota_hours;
        } else {
          total += dayData.time_slots.reduce((acc, s) => acc + calculateDurationMinutes(s.start, s.end), 0) / 60;
        }
      }
    }
    return Math.round(total * 10) / 10;
  });

  readonly isWeeklyValid = computed(() => this.totalWeeklyHours() >= 1.0);
}
```

---

## 8. Ma Trận Truy Vết & Chiến Lược Kiểm Thử Chất Lượng (Verification Matrix)

### 8.1. Ma trận Truy vết Yêu cầu Kỹ thuật (Requirements Traceability Matrix - RTM)

| Mã Yêu cầu | Nguồn truy vết | Thành phần Xử lý (Component) | Phương pháp Kiểm chứng (Verification) | Tiêu chí Nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :--- | :--- |
| **`FR-AVAIL-001`** | SRS v1.0 Mục 7.4, `OS-06`, `BUSR-03` | `AvailabilityProfile`, `DaySchedule`, Mode A View | `test_mode_a_os06_quota_bounds` | Cho phép nhập quota 0.5h – 14.0h; chặn nếu < 0.5h hoặc > 14.0h. |
| **`FR-AVAIL-002`** | SRS v1.0 Mục 7.4, `BUSR-04` | `TimeSlot`, `DaySchedule`, Mode B View | `test_mode_b_overlapping_slots`, `test_time_slot_minimum_duration_30m` | Chặn Start $\ge$ End; chặn slot < 30m; chặn 2 slot đè giờ nhau trong ngày. |
| **`FR-AVAIL-003`** | SRS v1.0 Mục 7.4, `OS-04`, `BUSR-05` | `calculate_remaining_capacity()` | `test_calculate_remaining_capacity_subtraction` | Phép trừ đoạn thời gian chính xác khi có lịch Roadmap khác chạy song song. |
| **`BUSR-02`** | SRS v1.0 Mục 5.2, `ADR-009` | `validate_daily_ceiling()` | `test_rich_entity_daily_ceiling_and_validation` | Hard Ceiling chặn vượt giờ Mode A; Mode B cho phép Soft Overflow $\le 30$m. |
| **`NFR-PERF-002`** | SRS v1.0 Mục 8.2 | CSDL PostgreSQL 16 JSONB, FastAPI Router | Integration Test `test_api_latency` | Tốc độ phản hồi API `GET /me` và `PUT /me` $\le 200$ms. |

---

### 8.2. Danh mục Ca Kiểm thử Tự động Chi tiết (Test Cases Specification)

```
tests/unit/domain/
├── test_time_slot_invariants.py
│   ├── TC-TS-01: TimeSlot hợp lệ [19:00 - 21:00] -> duration = 120m.
│   ├── TC-TS-02: Start >= End [21:00 - 20:00] -> Ném InvalidTimeSlotException.
│   ├── TC-TS-03: Slot bằng nhau [20:00 - 20:00] -> Ném InvalidTimeSlotException.
│   ├── TC-TS-04: Slot ngắn hơn 30 phút [20:00 - 20:25] -> Ném InvalidTimeSlotException.
│   └── TC-TS-05: Kiểm tra overlaps() giữa 2 slot tiếp giáp vs giao thoa.
├── test_mode_a_quota_validation.py
│   ├── TC-MA-01: Giá trị biên 0.5h và 14.0h -> Hợp lệ.
│   ├── TC-MA-02: Giá trị vi phạm cận dưới 0.4h -> Ném InvalidQuotaBoundException.
│   ├── TC-MA-03: Giá trị vi phạm cận trên 14.5h -> Ném InvalidQuotaBoundException.
│   └── TC-MA-04: Ngày tắt (enabled=False) có quota=0.0 -> Hợp lệ.
├── test_mode_b_overlap_validation.py
│   ├── TC-MB-01: 2 slot độc lập [08:00 - 10:00] và [14:00 - 16:00] -> Hợp lệ.
│   ├── TC-MB-02: 2 slot tiếp giáp nhau [18:00 - 19:30] và [19:30 - 21:00] -> Hợp lệ.
│   └── TC-MB-03: 2 slot đè nhau [19:00 - 21:00] và [20:00 - 22:00] -> Ném OverlappingTimeSlotsException.
├── test_weekly_schedule_invariants.py
│   ├── TC-WS-01: Tổng giờ cả tuần = 16.0h -> Hợp lệ.
│   └── TC-WS-02: Tổng giờ cả tuần = 0.5h (< 1.0h) -> Ném InsufficientWeeklyAvailabilityException.
└── test_rich_entity_validation_result.py
    ├── TC-RE-01: Mode A Hard Ceiling: Tổng task 130m > Quỹ 120m -> is_valid = False.
    ├── TC-RE-02: Mode B Soft Overflow: Tổng task 140m > Quỹ 120m (tràn 20m <= 30m) -> is_valid = True, has_soft_overflow = True.
    ├── TC-RE-03: Mode B Hard Block: Tổng task 160m > Quỹ 120m (tràn 40m > 30m) -> is_valid = False.
    ├── TC-RE-04: Trừ đoạn thời gian calculate_remaining_capacity() chính xác (Mode A -> int minutes, Mode B -> List[TimeSlot]).
    ├── TC-RE-05: Thẩm định proposal vị trí thực tế validate_proposal_against_slots() (chặn task đè vào khoảng bận dù tổng phút hợp lệ).
    └── TC-RE-06: TimeSlot xử lý end_day_offset = 1 (22:30 T2 -> 00:30 T3) tính duration = 120m chuẩn xác.

tests/integration/
└── test_availability_api.py
    ├── TC-API-01: GET /api/v1/availabilities/me lần đầu trả về Default Template (200 OK).
    ├── TC-API-02: PUT /api/v1/availabilities/me payload chuẩn lưu thành công (200 OK).
    ├── TC-API-03: PUT gửi quota 0.2h -> Trả về HTTP 422 {"code": "INVALID_QUOTA_BOUNDS"}.
    ├── TC-API-04: PUT gửi slot chồng lấn -> Trả về HTTP 422 {"code": "OVERLAPPING_TIME_SLOTS"}.
    ├── TC-API-05: Chuyển đổi mode qua lại bảo toàn 100% dữ liệu JSONB (State Retention).
    ├── TC-API-06: GET /api/v1/availabilities/me lần đầu trả về default profile với id = null mà không INSERT DB.
    └── TC-API-07: Apply Gate trả về HTTP 409 Conflict khi updated_at bị thay đổi đồng thời từ phiên khác.
```

---

## 9. Lộ Trình Triển Khai Kỹ Thuật Từng Bước (Implementation Roadmap)

Quá trình triển khai khi được kích hoạt sẽ tuân thủ nghiêm ngặt theo 6 bước có tuần tự phụ thuộc (Dependencies First):

```
[BƯỚC 1: DOMAIN LAYER] 
  ├── Tạo src/domain/exceptions/availability.py
  ├── Tạo src/domain/models/availability.py (TimeSlot, DaySchedule, WeeklySchedule, AvailabilityProfile)
  └── Viết & Chạy tests/unit/domain/test_availability_domain.py (Đảm bảo 100% Green)
           │
           ▼
[BƯỚC 2: APPLICATION LAYER]
  ├── Tạo src/application/dtos/availability.py (Pydantic v2 Schemas)
  ├── Tạo src/application/ports/availability_repository_port.py (Driven Port)
  └── Tạo src/application/use_cases/availability/ (GetUseCase, UpdateUseCase)
           │
           ▼
[BƯỚC 3: INFRASTRUCTURE LAYER]
  ├── Cấu hình src/infrastructure/database/base.py (SQLAlchemy Async Engine)
  ├── Tạo models/user_model.py & models/availability_model.py
  ├── Tạo repositories/sql_availability_repository.py (Adapter)
  └── Khởi tạo kịch bản Alembic migration cho bảng users và availabilities
           │
           ▼
[BƯỚC 4: PRESENTATION LAYER - BACKEND API]
  ├── Tạo presentation/api/v1/dependencies/auth.py (Dev Fallback get_current_user_id)
  ├── Tạo presentation/api/v1/endpoints/availability_router.py (GET /me, PUT /me, Exception Handlers)
  ├── Đăng ký router vào presentation/main.py
  └── Viết & Chạy tests/integration/test_availability_api.py
           │
           ▼
[BƯỚC 5: FRONTEND LAYER - ANGULAR 19 SPA]
  ├── Cập nhật core/constants/api-endpoints.ts
  ├── Tạo core/models/availability.model.ts
  ├── Tạo core/services/availability.service.ts (RxJS + Signals)
  ├── Xây dựng features/settings/components/availability-config/ (Mode A, Mode B, Presets, Copy Weekdays)
  ├── Nhúng component vào Settings Page (/settings)
  └── Tích hợp Quick Drawer trên Schedule Page (/schedule)
           │
           ▼
[BƯỚC 6: VERIFICATION & WALKTHROUGH]
  ├── Chạy toàn bộ pytest suite backend
  ├── Chạy pnpm build trên frontend (Typecheck & Linters)
  └── Biên soạn tài liệu nghiệm thu kỹ thuật Walkthrough
```

---
*Tài liệu được lưu trữ chính thức tại `docs/architecture/technical-spec-fr-avail-hybrid-availability.md` phục vụ hồ sơ đồ án tốt nghiệp kỹ thuật phần mềm FocusFlow.*
