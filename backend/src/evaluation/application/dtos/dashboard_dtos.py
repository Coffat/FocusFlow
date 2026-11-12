from uuid import UUID

from pydantic import BaseModel, Field


class DashboardKpiDTO(BaseModel):
    monthly_hours: float = Field(..., description="Tổng số giờ học trong tháng")
    target_hours: float = Field(..., description="Mục tiêu số giờ học trong tháng")
    monthly_progress_pct: float = Field(..., description="Phần trăm hoàn thành mục tiêu tháng")
    streak_days: int = Field(..., description="Số ngày chuỗi học tập hiện tại")
    personal_best_streak: int = Field(..., description="Kỷ lục chuỗi ngày học tập cao nhất")
    streak_history_last_7_days: list[bool] = Field(
        ..., description="Lịch sử chuỗi học 7 ngày gần nhất"
    )
    adherence_rate_pct: float = Field(..., description="Tỷ lệ tuân thủ lịch học (%)")
    adherence_delta_pct: float = Field(
        ..., description="Mức tăng trưởng tỷ lệ tuân thủ so với tuần trước (%)"
    )
    completed_pomodoro_count: int = Field(..., description="Tổng số chu kỳ Pomodoro hoàn thành")
    deep_work_hours: float = Field(..., description="Số giờ Deep Work đạt được")


class DayStudyDistributionDTO(BaseModel):
    day_label: str = Field(..., description="Nhãn ngày (Mon, Tue, Wed, Thu, Fri, Sat, Sun)")
    hours: float = Field(..., description="Số giờ học tập trong ngày")
    is_today: bool = Field(..., description="Đánh dấu ngày hôm nay")


class DashboardActiveRoadmapDTO(BaseModel):
    id: UUID = Field(..., description="ID của lộ trình học tập")
    code: str = Field(..., description="Mã định danh lộ trình")
    title: str = Field(..., description="Tên lộ trình học")
    commitment_hours_per_week: float = Field(..., description="Cam kết số giờ học mỗi tuần")
    deadline: str = Field(..., description="Hạn chót hoàn thành lộ trình")
    completed_tasks: int = Field(..., description="Số bài học/nhiệm vụ đã hoàn thành")
    total_tasks: int = Field(..., description="Tổng số bài học/nhiệm vụ")
    progress_pct: float = Field(..., description="Tiến độ hoàn thành lộ trình (%)")
    next_task_code: str = Field(..., description="Mã nhiệm vụ tiếp theo")
    next_task_title: str = Field(..., description="Tiêu đề nhiệm vụ tiếp theo")


class DashboardTodayQueueItemDTO(BaseModel):
    id: UUID = Field(..., description="ID nhiệm vụ trong hàng đợi hôm nay")
    task_code: str = Field(..., description="Mã nhiệm vụ")
    title: str = Field(..., description="Tên nhiệm vụ")
    roadmap_title: str = Field(..., description="Lộ trình học trực thuộc")
    scheduled_time: str = Field(..., description="Khung giờ học dự kiến (VD: 08:30 - 10:00)")
    pomodoro_estimate: int = Field(..., description="Số block Pomodoro ước tính")
    duration_minutes: int = Field(..., description="Thời lượng tính bằng phút")
    status: str = Field(
        ..., description="Trạng thái nhiệm vụ (SCHEDULED, READY, IN_PROGRESS, COMPLETED)"
    )


class DashboardAiInsightDTO(BaseModel):
    model_version: str = Field(..., description="Phiên bản mô hình AI H-SRL")
    message: str = Field(..., description="Thông điệp nhận xét & khuyến nghị cá nhân hóa")
    peak_hours: str = Field(..., description="Khung giờ tập trung cao độ nhất của người học")
    efficiency_growth_pct: float = Field(
        ..., description="Tốc độ tăng trưởng hiệu suất học tập (%)"
    )


class DashboardAdaptationStatusDTO(BaseModel):
    is_balanced: bool = Field(..., description="Lịch học có đang cân bằng và không xung đột")
    message: str = Field(..., description="Mô tả trạng thái cân bằng hoặc cảnh báo rủi ro")
    domino_shift_ready: bool = Field(
        ..., description="Sẵn sàng thực hiện dời lịch tự động Domino Shift nếu quá hạn"
    )


class DashboardScheduleBlockDTO(BaseModel):
    id: UUID = Field(..., description="ID của block lịch học")
    day_of_week: int = Field(..., description="Thứ trong tuần (1 = Thứ 2, 7 = Chủ nhật)")
    day_label: str = Field(..., description="Nhãn thứ (Thứ Hai, Thứ Ba...)")
    start_time: str = Field(..., description="Giờ bắt đầu (HH:MM)")
    end_time: str = Field(..., description="Giờ kết thúc (HH:MM)")
    title: str = Field(..., description="Tiêu đề khối học")
    category: str = Field(..., description="Phân loại môn học / kỹ năng")
    status: str = Field(..., description="Trạng thái khối lịch (SCHEDULED, IN_PROGRESS, COMPLETED)")
    pomodoro_count: int = Field(..., description="Số phiên Pomodoro")
    duration_minutes: int = Field(..., description="Thời lượng khối học theo phút")
    roadmap_code: str = Field(..., description="Mã lộ trình tương ứng")


class DashboardSummaryResponseDTO(BaseModel):
    kpi: DashboardKpiDTO = Field(..., description="Chỉ số hiệu suất học tập cốt lõi")
    study_distribution: list[DayStudyDistributionDTO] = Field(
        ..., description="Biểu đồ phân bổ giờ học theo tuần"
    )
    active_roadmaps: list[DashboardActiveRoadmapDTO] = Field(
        ..., description="Danh sách lộ trình đang học tích cực"
    )
    today_queue: list[DashboardTodayQueueItemDTO] = Field(
        ..., description="Hàng đợi nhiệm vụ cần học hôm nay"
    )
    ai_insight: DashboardAiInsightDTO = Field(
        ..., description="Thông tin chi tiết và khuyến nghị từ AI"
    )
    adaptation_status: DashboardAdaptationStatusDTO = Field(
        ..., description="Trạng thái tự thích ứng và cân bằng lịch học"
    )
    schedule_blocks: list[DashboardScheduleBlockDTO] = Field(
        ..., description="Lịch học trực quan phân bổ theo tuần"
    )
