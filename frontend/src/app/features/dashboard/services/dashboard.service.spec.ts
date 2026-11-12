import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { DashboardService, EMPTY_DASHBOARD_SUMMARY, mapDashboardSummary } from './dashboard.service';

describe('DashboardService', () => {
  let service: DashboardService;
  let httpTesting: HttpTestingController;

  const mockBackendResponse = {
    kpi: {
      monthly_hours: 42.5,
      target_hours: 50.0,
      monthly_progress_pct: 85.0,
      streak_days: 12,
      personal_best_streak: 18,
      streak_history_last_7_days: [true, true, true, true, false, false, false],
      adherence_rate_pct: 91.2,
      adherence_delta_pct: 3.4,
      completed_pomodoro_count: 68,
      deep_work_hours: 34.0,
    },
    active_roadmaps: [
      {
        id: 'rm-1',
        code: 'RD-IELTS-75',
        title: 'IELTS Academic 7.5',
        category: 'English',
        commitment_hours_per_week: 10,
        deadline: '2026-12-31',
        completed_tasks: 28,
        total_tasks: 40,
        progress_pct: 70.0,
        next_task_code: 'TSK-1',
        next_task_title: 'Writing Task 2',
      },
    ],
    today_queue: [
      {
        id: 'q-1',
        task_code: 'TSK-05',
        title: 'Redis Cache & Distributed Lock',
        roadmap_title: 'Go Hexagonal',
        scheduled_time: '10:00 - 11:30',
        duration_minutes: 90,
        pomodoro_estimate: 3,
        status: 'READY',
      },
    ],
    study_distribution: [
      { day_label: 'Mon', hours: 2.5, is_today: false },
      { day_label: 'Tue', hours: 3.5, is_today: false },
      { day_label: 'Wed', hours: 4.5, is_today: true },
    ],
    schedule_blocks: [
      {
        id: 'sb-1',
        title: 'MATH201',
        day_of_week: 1,
        day_label: 'T2',
        start_time: '08:00',
        end_time: '10:00',
        status: 'COMPLETED',
        pomodoro_count: 2,
        duration_minutes: 120,
      },
    ],
    ai_insight: {
      model_version: 'FocusFlow AI v2',
      message: 'Khả năng tập trung buổi sáng cao.',
      peak_hours: '09:00 - 11:30',
      efficiency_growth_pct: 14.2,
    },
    adaptation_status: {
      is_balanced: true,
      message: 'Lịch trình cân bằng.',
      domino_shift_ready: true,
    },
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        DashboardService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(DashboardService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('khởi tạo với dữ liệu ban đầu an toàn (không có dữ liệu giả định hardcoded)', () => {
    const summary = service.summary();
    expect(summary).not.toBeNull();
    expect(summary.kpi.monthlyHours).toBe(0);
    expect(summary.kpi.streakDays).toBe(0);
    expect(summary.activeRoadmaps).toEqual([]);
    expect(service.currentState()).toBe('normal');
  });

  it('chuyển trạng thái sang new-user cập nhật summary với danh sách rỗng', () => {
    service.setState('new-user');
    expect(service.currentState()).toBe('new-user');
    const summary = service.summary();
    expect(summary.activeRoadmaps).toEqual([]);
    expect(summary.scheduleBlocks).toEqual([]);
    expect(summary.todayQueue).toEqual([]);
    expect(summary.kpi.monthlyHours).toBe(0);
  });

  it('chuyển trạng thái sang unscheduled giữ nguyên lộ trình nhưng xóa scheduleBlocks', () => {
    service.setState('unscheduled');
    expect(service.currentState()).toBe('unscheduled');
    const summary = service.summary();
    expect(summary.scheduleBlocks).toEqual([]);
    expect(summary.todayQueue).toEqual([]);
  });

  it('chuyển trạng thái sang empty-week xóa scheduleBlocks', () => {
    service.setState('empty-week');
    expect(service.currentState()).toBe('empty-week');
    expect(service.summary().scheduleBlocks).toEqual([]);
  });

  it('setWeekOffset cập nhật giá trị offset', () => {
    service.setWeekOffset(2);
    expect(service.weekOffset()).toBe(2);
  });

  it('loadSummary tải dữ liệu thành công từ backend và ánh xạ snake_case sang camelCase chính xác', () => {
    service.loadSummary().subscribe((data) => {
      expect(data).toBeDefined();
      expect(data.kpi.monthlyHours).toBe(42.5);
      expect(data.kpi.monthlyTarget).toBe(50.0);
      expect(data.kpi.streakDays).toBe(12);
      expect(data.kpi.streakRecord).toBe(18);
      expect(data.kpi.adherenceRate).toBe(91.2);
      expect(data.kpi.adherenceChange).toBe(3.4);
      expect(data.kpi.pomodoroCompleted).toBe(68);
      expect(data.kpi.pomodoroDeepWorkHours).toBe(34.0);
      expect(data.kpi.weeklyCommitment).toBe(10);
      expect(data.activeRoadmaps.length).toBe(1);
      expect(data.activeRoadmaps[0].title).toBe('IELTS Academic 7.5');
      expect(data.activeRoadmaps[0].progressPercentage).toBe(70.0);
      expect(data.todayQueue.length).toBe(1);
      expect(data.todayQueue[0].status).toBe('active');
    });

    const req = httpTesting.expectOne('/api/v1/evaluation/dashboard-summary');
    expect(req.request.method).toBe('GET');
    req.flush(mockBackendResponse);
  });

  it('hàm mapDashboardSummary an toàn tuyệt đối khi DTO rỗng hoặc thiếu trường', () => {
    const emptyResult = mapDashboardSummary({});
    expect(emptyResult.kpi.monthlyHours).toBe(0);
    expect(emptyResult.kpi.monthlyTarget).toBe(0);
    expect(emptyResult.kpi.weeklyCommitment).toBe(0);
    expect(emptyResult.kpi.streakDays).toBe(0);
    expect(emptyResult.kpi.streakRecord).toBe(0);
    expect(emptyResult.kpi.adherenceRate).toBe(0);
    expect(emptyResult.kpi.adherenceChange).toBe(0);
    expect(emptyResult.kpi.pomodoroCompleted).toBe(0);
    expect(emptyResult.kpi.pomodoroDeepWorkHours).toBe(0);
    expect(emptyResult.kpi.pomodoroTargetRate).toBe(0);
    expect(emptyResult.activeRoadmaps).toEqual([]);
    expect(emptyResult.todayQueue).toEqual([]);
  });

  it('loadSummary fallback an toàn về EMPTY_DASHBOARD_SUMMARY khi backend gặp lỗi', () => {
    service.loadSummary().subscribe((data) => {
      expect(data).toEqual(EMPTY_DASHBOARD_SUMMARY);
      expect(service.summary()).toEqual(EMPTY_DASHBOARD_SUMMARY);
    });

    const req = httpTesting.expectOne('/api/v1/evaluation/dashboard-summary');
    req.error(new ProgressEvent('error'));
  });
});
