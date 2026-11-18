import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AnalyticsService } from './analytics.service';

describe('AnalyticsService', () => {
  let service: AnalyticsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AnalyticsService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AnalyticsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('loadSummary() và loadWeekly() gọi API với withCredentials: true', () => {
    service.loadSummary().subscribe();
    const sumReq = httpMock.expectOne('/api/v1/analytics/summary');
    expect(sumReq.request.method).toBe('GET');
    expect(sumReq.request.withCredentials).toBe(true);
    sumReq.flush({
      total_focused_hours: 14.5,
      weekly_study_hours: 6.5,
      task_completion_rate: 92,
      plan_adherence_rate: 85,
      weekly_recovered_learning_sessions: 3,
      completed_tasks_count: 11,
      total_tasks_count: 12,
      active_streak_days: 5,
      average_focus_score: 4.2,
      daily_metrics: [],
    });

    service.loadWeekly('2026-11-16').subscribe();
    const wkReq = httpMock.expectOne('/api/v1/analytics/weekly?week_start=2026-11-16');
    expect(wkReq.request.method).toBe('GET');
    expect(wkReq.request.withCredentials).toBe(true);
    wkReq.flush({
      week_start: '2026-11-16',
      week_end: '2026-11-22',
      total_focused_hours: 6.5,
      completed_sessions_count: 5,
      completed_tasks_count: 4,
      total_scheduled_tasks_count: 5,
      task_completion_rate: 80,
      plan_adherence_rate: 85,
      weekly_recovered_learning_sessions: 3,
      daily_breakdown: [],
    });

    expect(service.summary()?.weekly_recovered_learning_sessions).toBe(3);
    expect(service.weekly()?.completed_sessions_count).toBe(5);
  });

  it('loadLatestWeeklyReview() xử lý 404 êm đẹp mà không báo lỗi', () => {
    service.loadLatestWeeklyReview().subscribe((res) => {
      expect(res).toBeNull();
    });

    const req = httpMock.expectOne('/api/v1/evaluation/weekly-reviews/latest');
    req.flush({ detail: 'Weekly review not found' }, { status: 404, statusText: 'Not Found' });

    expect(service.latestReview()).toBeNull();
    expect(service.reviewError()).toBeNull();
  });

  it('generateWeeklyReview() xử lý 409 duplicate cleanly', () => {
    service
      .generateWeeklyReview({
        roadmap_id: 'rm-1',
        period_start: '2026-11-16',
        period_end: '2026-11-22',
      })
      .subscribe({ error: () => {} });

    const req = httpMock.expectOne('/api/v1/evaluation/weekly-reviews/generate-jobs');
    req.flush({ detail: 'Duplicate review' }, { status: 409, statusText: 'Conflict' });

    expect(service.reviewError()?.code).toBe('DUPLICATE_WEEKLY_REVIEW');
  });
});
