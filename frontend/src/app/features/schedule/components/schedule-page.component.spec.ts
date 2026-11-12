import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { SchedulePageComponent } from './schedule-page.component';
import { ScheduleService } from '../services/schedule.service';

describe('SchedulePageComponent', () => {
  let component: SchedulePageComponent;
  let fixture: ComponentFixture<SchedulePageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SchedulePageComponent],
      providers: [
        ScheduleService,
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SchedulePageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo trang thời khóa biểu thành công', () => {
    expect(component).toBeTruthy();
    expect(component.isDrawerOpen()).toBe(false);
  });

  it('mở và đóng Quick Drawer khi nhấn nút điều chỉnh lịch hôm nay', () => {
    component.openQuickDrawer();
    fixture.detectChanges();
    expect(component.isDrawerOpen()).toBe(true);

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[role="dialog"]')).toBeTruthy();

    component.closeQuickDrawer();
    fixture.detectChanges();
    expect(component.isDrawerOpen()).toBe(false);
  });

  it('nhấn phím Escape đóng Quick Drawer khi đang mở', () => {
    component.openQuickDrawer();
    fixture.detectChanges();
    expect(component.isDrawerOpen()).toBe(true);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();

    expect(component.isDrawerOpen()).toBe(false);
  });

  it('áp dụng điều chỉnh hôm nay (Domino Shift) không gọi PUT availabilities', () => {
    component.openQuickDrawer();
    fixture.detectChanges();

    component.selectedActionType.set('DOMINO_SHIFT');
    component.actionReason.set('Bận tăng ca');
    component.applyTodayAdjustment();
    fixture.detectChanges();

    expect(component.isDrawerOpen()).toBe(false);
    expect(component.drawerSuccess()).toContain('Đã kích hoạt Domino Shift');
    expect(component.drawerSuccess()).toContain('Bận tăng ca');
  });

  it('hiển thị empty state khi danh sách weeklySlots rỗng', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Chưa có buổi học nào trong tuần');
    expect(el.textContent).toContain('Tạo Lộ trình mới với AI');
    expect(el.textContent).toContain('Cấu hình Giờ rảnh');
  });

  it('xử lý kết nối Google Calendar từ thanh tác vụ schedule', () => {
    const connectSpy = vi.spyOn(component.calendarService, 'connectGoogleCalendar').mockImplementation(() => {});
    component.connectGoogleCalendar();
    expect(connectSpy).toHaveBeenCalledWith('/schedule');
  });
});
