import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { DashboardWeeklyGridComponent } from './dashboard-weekly-grid.component';
import { DashboardScheduleBlock } from '../models/dashboard.model';

describe('DashboardWeeklyGridComponent', () => {
  let component: DashboardWeeklyGridComponent;
  let fixture: ComponentFixture<DashboardWeeklyGridComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardWeeklyGridComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardWeeklyGridComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công với ngày và tuần động theo thời gian thực', () => {
    expect(component).toBeTruthy();
    const days = component.days();
    expect(days.length).toBe(7);
    expect(days[0].label).toBe('T2');
    expect(days[6].label).toBe('CN');

    // Có ít nhất 1 ngày là isToday nếu weekOffset = 0
    const todayDays = days.filter((d) => d.isToday);
    expect(todayDays.length).toBe(1);

    // weekLabel có định dạng Tuần X (DD/MM – DD/MM)
    expect(component.weekLabel()).toMatch(/Tuần \d+ \(\d{2}\/\d{2} – \d{2}\/\d{2}\)/);
  });

  it('thay đổi weekOffset cập nhật tuần và ngày tương ứng', () => {
    fixture.componentRef.setInput('weekOffset', 1);
    fixture.detectChanges();

    const daysNextWeek = component.days();
    // Tuần kế tiếp không có isToday (vì hôm nay thuộc tuần hiện tại)
    expect(daysNextWeek.filter((d) => d.isToday).length).toBe(0);
  });

  it('badge Domino Shift chỉ hiển thị khi hasDominoShift = true', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Domino Shift Active');

    fixture.componentRef.setInput('hasDominoShift', true);
    fixture.detectChanges();

    expect(el.textContent).toContain('Domino Shift Active');
  });

  it('hiển thị ca học và tính toán phân cấp hiển thị chính xác', () => {
    const mockBlock: DashboardScheduleBlock = {
      id: 'blk-1',
      title: 'Full IELTS Mock Test',
      dayOfWeek: 1,
      dayLabel: 'T2',
      startTime: '08:00',
      endTime: '10:00',
      type: 'upcoming',
      code: 'RD-IELTS-75',
      pomodoroCount: 4,
      durationMinutes: 120,
    };

    fixture.componentRef.setInput('scheduleBlocks', [mockBlock]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Full IELTS Mock Test');
    expect(el.textContent).toContain('08:00 – 10:00');
    expect(el.textContent).toContain('RD-IELTS-75');
    expect(el.textContent).toContain('4 phiên');
  });
});
