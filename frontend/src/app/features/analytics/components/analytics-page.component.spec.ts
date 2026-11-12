import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AnalyticsPageComponent } from './analytics-page.component';
import { AnalyticsService } from '../services/analytics.service';

describe('AnalyticsPageComponent', () => {
  let component: AnalyticsPageComponent;
  let fixture: ComponentFixture<AnalyticsPageComponent>;
  let analyticsService: AnalyticsService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AnalyticsPageComponent],
      providers: [AnalyticsService, provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalyticsPageComponent);
    component = fixture.componentInstance;
    analyticsService = TestBed.inject(AnalyticsService);
    fixture.detectChanges();
  });

  it('khởi tạo thành công trang phân tích hiệu suất', () => {
    expect(component).toBeTruthy();
  });

  it('hiển thị empty state khi dailyMetrics rỗng (không dùng mock)', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Chưa có đủ dữ liệu phân tích');
    expect(el.textContent).toContain('Vào phòng học ngay');
    expect(el.textContent).toContain('0%');
    expect(el.textContent).toContain('Mục tiêu >= 90%');
    expect(el.textContent).toContain('Mục tiêu >= 80');
  });

  it('hiển thị số liệu đạt KPI khi hoàn thành các phiên học', () => {
    analyticsService.analyticsData.set({
      weeklyStudyHours: 18.5,
      taskCompletionRate: 95,
      averageFocusScore: 88,
      dailyMetrics: [
        { date: 'Thứ 2', minutesStudied: 120, pomodorosCompleted: 4 },
      ],
    });
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('95%');
    expect(el.textContent).toContain('Đạt KPI (>=90%)');
    expect(el.textContent).toContain('88 / 100');
    expect(el.textContent).toContain('Đạt KPI (>=80)');
    expect(el.textContent).toContain('18.5 giờ');
    expect(el.textContent).toContain('120 phút học');
  });
});
