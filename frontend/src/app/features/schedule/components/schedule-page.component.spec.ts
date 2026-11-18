import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { SchedulePageComponent } from './schedule-page.component';
import { ScheduleService, getLocalMondayIso } from '../services/schedule.service';

describe('SchedulePageComponent', () => {
  let component: SchedulePageComponent;
  let fixture: ComponentFixture<SchedulePageComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SchedulePageComponent],
      providers: [
        ScheduleService,
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SchedulePageComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushInitialLoad() {
    fixture.detectChanges();
    httpMock.expectOne('/api/v1/account/calendar/status').flush({
      connected: false,
      provider: 'GOOGLE',
      sync_status: 'REVOKED',
    });
    const monday = getLocalMondayIso(0);
    httpMock.expectOne(`/api/v1/tasks/schedule/week?week_start=${monday}`).flush({
      week_start: monday,
      week_end: monday,
      items: [],
    });
    httpMock.expectOne('/api/v1/roadmaps').flush([
      {
        id: 'rm-1',
        user_id: 'u-1',
        goal_id: 'g-1',
        title: 'Lộ trình Python',
        status: 'ACTIVE',
        created_at: '2026-11-18T00:00:00Z',
        updated_at: '2026-11-18T00:00:00Z',
      },
    ]);
    fixture.detectChanges();
  }

  it('khởi tạo trang thời khóa biểu thành công và không gọi endpoint /calendar/tokens/reset', () => {
    flushInitialLoad();
    expect(component).toBeTruthy();
    expect(component.isDrawerOpen()).toBe(false);
  });

  it('mở và đóng Quick Drawer khi nhấn nút và phím Escape', () => {
    flushInitialLoad();
    component.openQuickDrawer();
    fixture.detectChanges();
    expect(component.isDrawerOpen()).toBe(true);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();
    expect(component.isDrawerOpen()).toBe(false);
  });

  it('Quick Drawer gọi POST /api/v1/roadmaps/{id}/reoptimize-schedule khi chọn tái tối ưu lịch', () => {
    flushInitialLoad();
    component.openQuickDrawer();
    component.selectedActionType.set('REOPTIMIZE_SCHEDULE');
    component.selectedDrawerRoadmapId.set('rm-1');
    component.applyTodayAdjustment();

    const req = httpMock.expectOne('/api/v1/roadmaps/rm-1/reoptimize-schedule');
    expect(req.request.method).toBe('POST');
    req.flush({
      id: 'prop-1',
      roadmap_id: 'rm-1',
      user_id: 'u-1',
      status: 'DRAFT',
      is_valid: true,
      has_soft_overflow: false,
      created_at: '2026-11-18T00:00:00Z',
      updated_at: '2026-11-18T00:00:00Z',
    });
    fixture.detectChanges();

    expect(component.isDrawerOpen()).toBe(false);
    expect(component.drawerSuccess()?.message).toContain('DRAFT');
  });

  it('hiển thị empty state khi tuần chưa có lịch học', () => {
    flushInitialLoad();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Chưa có buổi học nào trong tuần');
    expect(el.textContent).toContain('Tạo Lộ trình mới với AI');
  });

  it('xử lý kết nối Google Calendar từ thanh tác vụ schedule', () => {
    flushInitialLoad();
    const connectSpy = vi
      .spyOn(component.calendarService, 'connectGoogleCalendar')
      .mockImplementation(() => {});
    component.connectGoogleCalendar();
    expect(connectSpy).toHaveBeenCalledWith('/schedule');
  });
});
