import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';
import {
  DashboardSummary,
  DashboardDataState,
  DashboardKpi,
  DayStudyDistribution,
  DashboardActiveRoadmap,
  DashboardTodayQueueItem,
  DashboardAiInsight,
  DashboardAdaptationStatus,
  DashboardScheduleBlock
} from '../models/dashboard.model';

export const DEFAULT_KPI: DashboardKpi = {
  monthlyHours: 42.5,
  monthlyTarget: 50.0,
  weeklyCommitment: 10,
  streakDays: 12,
  streakRecord: 18,
  recentStreak: [true, true, true, true, false, false, false],
  adherenceRate: 91.2,
  adherenceChange: 3.4,
  pomodoroCompleted: 68,
  pomodoroDeepWorkHours: 34,
  pomodoroTargetRate: 78
};

export const DEFAULT_STUDY_DISTRIBUTION: DayStudyDistribution[] = [
  { day: 'T2', fullDayName: 'Thứ Hai', hours: 2.5, isToday: false, date: '14/10' },
  { day: 'T3', fullDayName: 'Thứ Ba', hours: 3.5, isToday: false, date: '15/10' },
  { day: 'T4', fullDayName: 'Thứ Tư', hours: 4.5, isToday: true, date: '16/10' },
  { day: 'T5', fullDayName: 'Thứ Năm', hours: 3.0, isToday: false, date: '17/10' },
  { day: 'T6', fullDayName: 'Thứ Sáu', hours: 4.0, isToday: false, date: '18/10' },
  { day: 'T7', fullDayName: 'Thứ Bảy', hours: 1.5, isToday: false, date: '19/10' },
  { day: 'CN', fullDayName: 'Chủ Nhật', hours: 2.0, isToday: false, date: '20/10' }
];

export const DEFAULT_ACTIVE_ROADMAPS: DashboardActiveRoadmap[] = [
  {
    id: 'rm-01',
    title: 'IELTS Academic Band 7.5',
    category: 'Academic English',
    progressPercentage: 48,
    totalTasks: 70,
    completedTasks: 34,
    nextTaskTitle: 'Writing Task 2: Argue & Counter-argue',
    deadline: '25/11/2026',
    updatedAt: '2 giờ trước'
  },
  {
    id: 'rm-02',
    title: 'Go Hexagonal Architecture & Microservices',
    category: 'Backend Engineering',
    progressPercentage: 30,
    totalTasks: 84,
    completedTasks: 25,
    nextTaskTitle: 'Triển khai Outbox Pattern & Kafka Event Streaming',
    deadline: '15/12/2026',
    updatedAt: 'Hôm qua'
  }
];

export const DEFAULT_TODAY_QUEUE: DashboardTodayQueueItem[] = [
  {
    id: 'q-01',
    taskId: 'TSK-05',
    title: 'Cấu hình Redis Cache & Distributed Lock Redlock',
    roadmapTitle: 'Go Hexagonal Architecture & Microservices',
    milestoneTitle: 'Chặng 3: Data Integrity',
    scheduledTime: '10:00 - 11:30',
    durationMinutes: 90,
    pomodoroCount: 3,
    status: 'active',
    urgency: 'high'
  },
  {
    id: 'q-02',
    taskId: 'TSK-03',
    title: 'Luyện đề Line Graph & Viết Introduction Overview',
    roadmapTitle: 'IELTS Academic Band 7.5',
    milestoneTitle: 'Chặng 2: Writing Mastery',
    scheduledTime: '14:00 - 15:30',
    durationMinutes: 90,
    pomodoroCount: 3,
    status: 'pending',
    urgency: 'medium'
  },
  {
    id: 'q-03',
    taskId: 'TSK-08',
    title: 'Triển khai Automated Integration Tests với Testcontainers',
    roadmapTitle: 'Go Hexagonal Architecture & Microservices',
    milestoneTitle: 'Chặng 4: CI/CD & Testing',
    scheduledTime: '16:00 - 17:00',
    durationMinutes: 60,
    pomodoroCount: 2,
    status: 'pending',
    urgency: 'normal'
  }
];

export const DEFAULT_SCHEDULE_BLOCKS: DashboardScheduleBlock[] = [
  {
    id: 'sb-01',
    title: 'Đại số tuyến tính & Tối ưu hóa',
    type: 'university',
    dayOfWeek: 1,
    dayLabel: 'T2',
    startTime: '08:00',
    endTime: '10:00',
    room: 'A2-301',
    code: 'MATH201'
  },
  {
    id: 'sb-02',
    title: 'TSK-01: Thiết kế Schema DB PostgreSQL 16',
    type: 'completed',
    dayOfWeek: 1,
    dayLabel: 'T2',
    startTime: '14:00',
    endTime: '16:00',
    code: 'TSK-01'
  },
  {
    id: 'sb-03',
    title: 'TSK-02: Viết Unit Test Domain Hexagonal',
    type: 'completed',
    dayOfWeek: 2,
    dayLabel: 'T3',
    startTime: '09:00',
    endTime: '11:30',
    code: 'TSK-02'
  },
  {
    id: 'sb-04',
    title: 'Lập trình Hướng đối tượng nâng cao',
    type: 'university',
    dayOfWeek: 2,
    dayLabel: 'T3',
    startTime: '13:30',
    endTime: '15:30',
    room: 'B1-104',
    code: 'CS202'
  },
  {
    id: 'sb-05',
    title: 'Cấu trúc Dữ liệu & Giải thuật',
    type: 'university',
    dayOfWeek: 3,
    dayLabel: 'T4',
    startTime: '07:30',
    endTime: '09:30',
    room: 'C3-205',
    code: 'CS101'
  },
  {
    id: 'sb-06',
    title: 'TSK-05: Redis Cache & Distributed Lock',
    type: 'live',
    dayOfWeek: 3,
    dayLabel: 'T4',
    startTime: '10:00',
    endTime: '11:30',
    code: 'TSK-05',
    isLive: true
  },
  {
    id: 'sb-07',
    title: 'TSK-03: Line Graph & Writing Prep',
    type: 'upcoming',
    dayOfWeek: 3,
    dayLabel: 'T4',
    startTime: '14:00',
    endTime: '15:30',
    code: 'TSK-03'
  },
  {
    id: 'sb-08',
    title: 'TSK-06: Domino Shift - Đề xuất dời phiên học',
    type: 'domino_proposal',
    dayOfWeek: 3,
    dayLabel: 'T4',
    startTime: '16:30',
    endTime: '18:00',
    code: 'TSK-06',
    description: 'AI tự động dịch chuyển tránh xung đột'
  },
  {
    id: 'sb-09',
    title: 'Cơ sở Dữ liệu Nâng cao & Phân tán',
    type: 'university',
    dayOfWeek: 4,
    dayLabel: 'T5',
    startTime: '08:30',
    endTime: '10:30',
    room: 'A1-402',
    code: 'DB301'
  },
  {
    id: 'sb-10',
    title: 'TSK-07: Mock API & Vitest Testing',
    type: 'upcoming',
    dayOfWeek: 4,
    dayLabel: 'T5',
    startTime: '15:00',
    endTime: '17:00',
    code: 'TSK-07'
  },
  {
    id: 'sb-11',
    title: 'TSK-08: CI/CD Workflow & Docker Compose',
    type: 'upcoming',
    dayOfWeek: 5,
    dayLabel: 'T6',
    startTime: '10:00',
    endTime: '12:00',
    code: 'TSK-08'
  },
  {
    id: 'sb-12',
    title: 'Hệ điều hành & Nhân Linux',
    type: 'university',
    dayOfWeek: 5,
    dayLabel: 'T6',
    startTime: '14:00',
    endTime: '16:00',
    room: 'B2-201',
    code: 'OS201'
  },
  {
    id: 'sb-13',
    title: 'TSK-09: IELTS Mock Test Listening Section 1-4',
    type: 'upcoming',
    dayOfWeek: 6,
    dayLabel: 'T7',
    startTime: '09:00',
    endTime: '11:00',
    code: 'TSK-09'
  },
  {
    id: 'sb-14',
    title: 'TSK-10: Tổng kết tuần & Self-Reflection SRL',
    type: 'upcoming',
    dayOfWeek: 7,
    dayLabel: 'CN',
    startTime: '15:00',
    endTime: '17:00',
    code: 'TSK-10'
  }
];

export const DEFAULT_AI_INSIGHT: DashboardAiInsight = {
  peakHourRange: '09:00 - 11:30',
  efficiencyChange: 14.2,
  suggestedBreak: '15 phút sau mỗi 2 phiên Pomodoro',
  summary: 'Khả năng tập trung và tốc độ xử lý logic đạt đỉnh trong khung giờ sáng từ 09:00 đến 11:30. Hiệu suất học tăng 14.2% khi hoàn thành các task Domain trước trưa.',
  recommendations: [
    'Nên xếp các task độ khó cao (Thuật toán, System Design) vào ca sáng 09:00 – 11:00',
    'Đã ghi nhận 3 phiên Pomodoro bị trễ ca chiều do tiết học WebCal kéo dài'
  ]
};

export const DEFAULT_ADAPTATION_STATUS: DashboardAdaptationStatus = {
  hasDominoShift: true,
  affectedTasksCount: 1,
  rescheduleReason: 'Tiết học Cấu trúc dữ liệu kéo dài +20 phút làm trễ phiên học',
  needsAttention: true,
  alertMessage: 'Domino Shift đang kích hoạt: Đã tự động đề xuất dời TSK-06 sang 16:30 mà không làm vỡ các ràng buộc cứng.'
};

export const DEFAULT_DASHBOARD_SUMMARY: DashboardSummary = {
  kpi: DEFAULT_KPI,
  activeRoadmaps: DEFAULT_ACTIVE_ROADMAPS,
  todayQueue: DEFAULT_TODAY_QUEUE,
  studyDistribution: DEFAULT_STUDY_DISTRIBUTION,
  scheduleBlocks: DEFAULT_SCHEDULE_BLOCKS,
  aiInsight: DEFAULT_AI_INSIGHT,
  adaptationStatus: DEFAULT_ADAPTATION_STATUS,
  currentWeek: {
    weekNumber: 42,
    startDate: '14/10',
    endDate: '20/10'
  },
  activeRoadmapTitle: 'IELTS Academic Band 7.5',
  totalMilestones: 8,
  completedMilestones: 4,
  totalStudyHours: 42.5,
  weeklyTargetHours: 15,
  streakDays: 12,
  upcomingTasks: [
    {
      id: 't-01',
      title: 'Thiết kế REST API Endpoints chuẩn OpenAPI 3.1',
      milestoneTitle: 'Chặng 2: Xây dựng Backend FastAPI',
      scheduledDate: 'Hôm nay, 10:00',
      pomodoroEstimate: 3,
      isCompleted: false
    },
    {
      id: 't-02',
      title: 'Luyện đề Line Graph & Viết Introduction Overview',
      milestoneTitle: 'Chặng 2: Writing Mastery',
      scheduledDate: 'Hôm nay, 14:00',
      pomodoroEstimate: 3,
      isCompleted: false
    }
  ]
};

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private readonly http = inject(HttpClient);

  readonly summary = signal<DashboardSummary | null>(DEFAULT_DASHBOARD_SUMMARY);
  readonly currentState = signal<DashboardDataState>('normal');
  readonly isLoading = signal<boolean>(false);
  readonly weekOffset = signal<number>(0);

  loadSummary(): Observable<DashboardSummary> {
    this.isLoading.set(true);
    return this.http.get<DashboardSummary>('/api/v1/evaluation/dashboard-summary').pipe(
      tap({
        next: (data) => {
          if (data && data.kpi) {
            this.summary.set(data);
          } else {
            this.summary.set(DEFAULT_DASHBOARD_SUMMARY);
          }
          this.isLoading.set(false);
        },
        error: () => {
          // Fallback gracefully to the rich default dataset so UI is never blank
          this.summary.set(DEFAULT_DASHBOARD_SUMMARY);
          this.isLoading.set(false);
        }
      }),
      catchError(() => {
        this.summary.set(DEFAULT_DASHBOARD_SUMMARY);
        this.isLoading.set(false);
        return of(DEFAULT_DASHBOARD_SUMMARY);
      })
    );
  }

  setState(state: DashboardDataState): void {
    this.currentState.set(state);
    if (state === 'normal') {
      this.summary.set(DEFAULT_DASHBOARD_SUMMARY);
    } else if (state === 'new-user') {
      this.summary.set({
        ...DEFAULT_DASHBOARD_SUMMARY,
        kpi: {
          ...DEFAULT_KPI,
          monthlyHours: 0,
          streakDays: 0,
          streakRecord: 0,
          recentStreak: [false, false, false, false, false, false, false],
          adherenceRate: 0,
          adherenceChange: 0,
          pomodoroCompleted: 0,
          pomodoroDeepWorkHours: 0,
          pomodoroTargetRate: 0
        },
        activeRoadmaps: [],
        todayQueue: [],
        scheduleBlocks: [],
        studyDistribution: DEFAULT_STUDY_DISTRIBUTION.map(d => ({ ...d, hours: 0 }))
      });
    } else if (state === 'unscheduled') {
      this.summary.set({
        ...DEFAULT_DASHBOARD_SUMMARY,
        scheduleBlocks: [],
        todayQueue: []
      });
    } else if (state === 'empty-week') {
      this.summary.set({
        ...DEFAULT_DASHBOARD_SUMMARY,
        scheduleBlocks: []
      });
    }
  }

  setWeekOffset(offset: number): void {
    this.weekOffset.set(offset);
  }
}
