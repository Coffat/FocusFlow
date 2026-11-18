from datetime import date

from pydantic import BaseModel, Field


class AnalyticsDailyMetricResponse(BaseModel):
    date: date
    day_label: str
    minutes_studied: int
    pomodoros_completed: int
    sessions_count: int
    is_today: bool = False


class AnalyticsSummaryResponse(BaseModel):
    total_focused_hours: float
    weekly_study_hours: float
    task_completion_rate: float
    plan_adherence_rate: float
    weekly_recovered_learning_sessions: int
    completed_tasks_count: int
    total_tasks_count: int
    active_streak_days: int
    average_focus_score: float
    daily_metrics: list[AnalyticsDailyMetricResponse] = Field(default_factory=list)


class AnalyticsWeeklyResponse(BaseModel):
    week_start: date
    week_end: date
    total_focused_hours: float
    completed_sessions_count: int
    completed_tasks_count: int
    total_scheduled_tasks_count: int
    task_completion_rate: float
    plan_adherence_rate: float
    weekly_recovered_learning_sessions: int
    daily_breakdown: list[AnalyticsDailyMetricResponse] = Field(default_factory=list)
