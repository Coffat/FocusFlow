import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { AppNavbarComponent } from './app-navbar.component';
import { AuthService } from '../../../core/services/auth.service';

describe('AppNavbarComponent', () => {
  let component: AppNavbarComponent;
  let fixture: ComponentFixture<AppNavbarComponent>;
  let router: Router;

  const mockUser = {
    id: 'u1',
    email: 'hoang@focusflow.ai',
    fullName: 'Minh Hoàng',
    role: 'learner' as const,
    isActive: true,
    aiCreditsRemaining: 100,
    totalStudyMinutes: 240,
    currentStreakDays: 5,
    createdAt: '2026-01-01',
  };

  beforeEach(async () => {
    const mockAuthService = {
      currentUser: signal(mockUser),
    };

    await TestBed.configureTestingModule({
      imports: [AppNavbarComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AppNavbarComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('khởi tạo thành công AppNavbarComponent', () => {
    expect(component).toBeTruthy();
  });

  it('hiển thị thương hiệu FocusFlow và khẩu hiệu', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.brand-title')?.textContent).toContain('FocusFlow');
    expect(el.textContent).toContain('Plan Smarter • Do Better');
  });

  it('hiển thị đủ 5 tab điều hướng chính', () => {
    expect(component.navItems.length).toBe(5);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Tổng quan');
    expect(el.textContent).toContain('Lộ trình');
    expect(el.textContent).toContain('Thời khóa biểu');
    expect(el.textContent).toContain('Hàng đợi Task');
    expect(el.textContent).toContain('Báo cáo');
  });

  it('hiển thị chữ viết tắt họ tên người dùng chính xác', () => {
    expect(component.userInitials()).toBe('MH');
    expect(component.userDisplayName()).toBe('Minh Hoàng');
  });

  it('điều hướng khi nhấn tìm kiếm nhanh ⌘K', () => {
    component.onSearchTrigger();
    expect(router.navigate).toHaveBeenCalledWith(['/roadmaps']);
  });
});
