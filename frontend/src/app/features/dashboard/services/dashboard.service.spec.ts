import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { DashboardService, DEFAULT_DASHBOARD_SUMMARY } from './dashboard.service';

describe('DashboardService', () => {
  let service: DashboardService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        DashboardService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(DashboardService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('khởi tạo với dữ liệu mặc định phong phú khớp thiết kế Stitch', () => {
    const summary = service.summary();
    expect(summary).not.toBeNull();
    expect(summary?.kpi.monthlyHours).toBe(42.5);
    expect(summary?.kpi.streakDays).toBe(12);
    expect(summary?.activeRoadmaps.length).toBeGreaterThan(0);
    expect(summary?.scheduleBlocks.length).toBeGreaterThan(0);
    expect(service.currentState()).toBe('normal');
  });

  it('chuyển trạng thái sang new-user cập nhật summary với danh sách rỗng', () => {
    service.setState('new-user');
    expect(service.currentState()).toBe('new-user');
    const summary = service.summary();
    expect(summary?.activeRoadmaps).toEqual([]);
    expect(summary?.scheduleBlocks).toEqual([]);
    expect(summary?.todayQueue).toEqual([]);
    expect(summary?.kpi.monthlyHours).toBe(0);
  });

  it('chuyển trạng thái sang unscheduled giữ nguyên lộ trình nhưng xóa scheduleBlocks', () => {
    service.setState('unscheduled');
    expect(service.currentState()).toBe('unscheduled');
    const summary = service.summary();
    expect(summary?.scheduleBlocks).toEqual([]);
    expect(summary?.todayQueue).toEqual([]);
  });

  it('chuyển trạng thái sang empty-week xóa scheduleBlocks', () => {
    service.setState('empty-week');
    expect(service.currentState()).toBe('empty-week');
    expect(service.summary()?.scheduleBlocks).toEqual([]);
  });

  it('setWeekOffset cập nhật giá trị offset', () => {
    service.setWeekOffset(2);
    expect(service.weekOffset()).toBe(2);
  });

  it('loadSummary tải dữ liệu thành công từ backend', () => {
    service.loadSummary().subscribe((data) => {
      expect(data).toBeDefined();
    });

    const req = httpTesting.expectOne('/api/v1/evaluation/dashboard-summary');
    expect(req.request.method).toBe('GET');
    req.flush(DEFAULT_DASHBOARD_SUMMARY);
  });

  it('loadSummary fallback mượt mà về DEFAULT_DASHBOARD_SUMMARY khi backend gặp lỗi', () => {
    service.loadSummary().subscribe((data) => {
      expect(data).toEqual(DEFAULT_DASHBOARD_SUMMARY);
      expect(service.summary()).toEqual(DEFAULT_DASHBOARD_SUMMARY);
    });

    const req = httpTesting.expectOne('/api/v1/evaluation/dashboard-summary');
    req.error(new ProgressEvent('error'));
  });
});
