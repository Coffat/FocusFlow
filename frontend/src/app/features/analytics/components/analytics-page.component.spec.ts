import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { AnalyticsPageComponent } from './analytics-page.component';
import { AnalyticsService, getLocalMondayDate } from '../services/analytics.service';

describe('AnalyticsPageComponent', () => {
  let component: AnalyticsPageComponent;
  let fixture: ComponentFixture<AnalyticsPageComponent>;
  let analyticsService: AnalyticsService;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AnalyticsPageComponent],
      providers: [AnalyticsService, provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalyticsPageComponent);
    component = fixture.componentInstance;
    analyticsService = TestBed.inject(AnalyticsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushInitial(summaryOverrides: Record<string, unknown> = {}) {
    fixture.detectChanges();
    httpMock.expectOne('/api/v1/analytics/summary').flush({
      total_focused_hours: 0,
      weekly_study_hours: 0,
      task_completion_rate: 0,
      plan_adherence_rate: 0,
      weekly_recovered_learning_sessions: 0,
      completed_tasks_count: 0,
      total_tasks_count: 0,
      active_streak_days: 0,
      average_focus_score: 0,
      daily_metrics: [],
      ...summaryOverrides,
    });
    const monday = getLocalMondayDate(0);
    httpMock.expectOne(`/api/v1/analytics/weekly?week_start=${monday}`).flush({
      week_start: monday,
      week_end: monday,
      total_focused_hours: 0,
      completed_sessions_count: 0,
      completed_tasks_count: 0,
      total_scheduled_tasks_count: 0,
      task_completion_rate: 0,
      plan_adherence_rate: 0,
      weekly_recovered_learning_sessions: 0,
      daily_breakdown: [],
    });
    httpMock
      .expectOne('/api/v1/evaluation/weekly-reviews/latest')
      .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
    httpMock.expectOne('/api/v1/roadmaps').flush([]);
    fixture.detectChanges();
  }

  it('khởi tạo thành công trang phân tích hiệu suất', () => {
    flushInitial();
    expect(component).toBeTruthy();
  });

  it('hiển thị empty state khi chưa có dữ liệu phân tích', () => {
    flushInitial();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Chưa có đủ dữ liệu phân tích trong tuần này');
    expect(el.textContent).toContain('Vào phòng học ngay');
    expect(el.textContent).toContain('0%');
    expect(el.textContent).toContain('Mục tiêu ≥ 90%');
  });

  it('hiển thị đầy đủ số liệu SRS (Focused Hours, Completion Rate, Adherence, WRLS) và bảng 7 ngày', () => {
    flushInitial({
      total_focused_hours: 24.5,
      weekly_study_hours: 18.5,
      task_completion_rate: 95,
      plan_adherence_rate: 88,
      weekly_recovered_learning_sessions: 4,
      completed_tasks_count: 19,
      total_tasks_count: 20,
      active_streak_days: 6,
      average_focus_score: 4.5,
    });

    analyticsService.weekly.set({
      week_start: '2026-11-16',
      week_end: '2026-11-22',
      total_focused_hours: 18.5,
      completed_sessions_count: 8,
      completed_tasks_count: 9,
      total_scheduled_tasks_count: 10,
      task_completion_rate: 95,
      plan_adherence_rate: 88,
      weekly_recovered_learning_sessions: 4,
      daily_breakdown: [
        {
          date: '2026-11-18',
          day_label: 'T4',
          minutes_studied: 120,
          pomodoros_completed: 4,
          sessions_count: 2,
          is_today: true,
        },
      ],
    });
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('24.5 giờ');
    expect(el.textContent).toContain('95%');
    expect(el.textContent).toContain('Đạt KPI (≥90%)');
    expect(el.textContent).toContain('88%');
    expect(el.textContent).toContain('4');
    expect(el.textContent).toContain('120 phút học');
  });
});
