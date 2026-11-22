import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AdminDashboardPageComponent } from './admin-dashboard-page.component';
import { AdminStatusService } from '../services/admin-status.service';

describe('AdminDashboardPageComponent (FE-MOCK-06)', () => {
  let fixture: ComponentFixture<AdminDashboardPageComponent>;
  let mockAdminStatusService: { getStatus: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    mockAdminStatusService = {
      getStatus: vi.fn().mockReturnValue(
        of({
          enabled: false,
          role: 'ADMIN',
          message: 'Cổng quản trị chưa được kích hoạt trong bản phát hành hiện tại.',
        })
      ),
    };

    await TestBed.configureTestingModule({
      imports: [AdminDashboardPageComponent],
      providers: [
        provideRouter([]),
        { provide: AdminStatusService, useValue: mockAdminStatusService },
      ],
    }).compileComponents();
  });

  it('hiển thị thẻ trạng thái trung thực từ GET /api/v1/account/admin/status và không còn nút +5 AI Quota giả', () => {
    fixture = TestBed.createComponent(AdminDashboardPageComponent);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(mockAdminStatusService.getStatus).toHaveBeenCalledTimes(1);
    expect(el.querySelector('[data-testid="admin-honest-status-card"]')).toBeTruthy();
    expect(el.textContent).toContain('Cổng quản trị chưa được kích hoạt');
    expect(el.textContent).not.toContain('+5 AI Quota');
  });

  it('hiển thị thông báo 403 Forbidden khi backend từ chối quyền truy cập', () => {
    mockAdminStatusService.getStatus.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 403, statusText: 'Forbidden' }))
    );

    fixture = TestBed.createComponent(AdminDashboardPageComponent);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="admin-status-forbidden"]')).toBeTruthy();
    expect(el.textContent).toContain('403 Forbidden');
  });
});
