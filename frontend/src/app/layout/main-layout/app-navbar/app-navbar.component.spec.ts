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
  let mockAuthService: {
    currentUser: ReturnType<typeof signal<any>>;
    logout: ReturnType<typeof vi.fn>;
  };

  const mockUser = {
    id: 'u1',
    email: 'hoang@focusflow.ai',
    fullName: 'Minh Hoàng',
    role: 'learner' as const,
    tier: 'PRO',
    isActive: true,
    aiCreditsRemaining: 100,
    totalStudyMinutes: 240,
    currentStreakDays: 5,
    createdAt: '2026-01-01',
  };

  beforeEach(async () => {
    mockAuthService = {
      currentUser: signal(mockUser),
      logout: vi.fn(),
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
    expect(el.textContent).toContain('Roadmap Hub');
    expect(el.textContent).toContain('Thời khóa biểu');
    expect(el.textContent).toContain('Hàng đợi Task');
    expect(el.textContent).toContain('Báo cáo');
  });

  it('hiển thị chữ viết tắt họ tên người dùng chính xác', () => {
    expect(component.userInitials()).toBe('MH');
    expect(component.userDisplayName()).toBe('Minh Hoàng');
    expect(component.userEmail()).toBe('hoang@focusflow.ai');
    expect(component.userTier()).toBe('PRO');
    expect(component.userRole()).toBe('learner');
  });

  it('xử lý đúng fallback khi người dùng không có fullName hoặc chưa đăng nhập', () => {
    mockAuthService.currentUser.set({
      id: 'u2',
      email: 'alex@example.com',
      fullName: '',
      role: 'user',
      tier: 'free',
      createdAt: '2026-01-01',
    });
    fixture.detectChanges();
    expect(component.userDisplayName()).toBe('alex');
    expect(component.userInitials()).toBe('AL');
    expect(component.userTier()).toBe('FREE');

    mockAuthService.currentUser.set(null);
    fixture.detectChanges();
    expect(component.userDisplayName()).toBe('Người học');
    expect(component.userInitials()).toBe('NH');
    expect(component.userEmail()).toBe('');
    expect(component.userTier()).toBe('FREE');
    expect(component.userRole()).toBe('user');
  });

  it('điều hướng khi nhấn tìm kiếm nhanh ⌘K', () => {
    component.onSearchTrigger();
    expect(router.navigate).toHaveBeenCalledWith(['/roadmaps']);
  });

  it('toggle và đóng User Menu chuẩn xác', () => {
    expect(component.isUserMenuOpen()).toBe(false);

    component.toggleUserMenu();
    expect(component.isUserMenuOpen()).toBe(true);

    component.closeUserMenu();
    expect(component.isUserMenuOpen()).toBe(false);
  });

  it('toggle và đóng Mobile Menu chuẩn xác', () => {
    expect(component.isMobileMenuOpen()).toBe(false);

    component.toggleMobileMenu();
    expect(component.isMobileMenuOpen()).toBe(true);

    component.closeMobileMenu();
    expect(component.isMobileMenuOpen()).toBe(false);
  });

  it('đảm bảo đóng menu còn lại khi mở menu khác', () => {
    component.toggleMobileMenu();
    expect(component.isMobileMenuOpen()).toBe(true);

    component.toggleUserMenu();
    expect(component.isUserMenuOpen()).toBe(true);
    expect(component.isMobileMenuOpen()).toBe(false);

    component.toggleMobileMenu();
    expect(component.isMobileMenuOpen()).toBe(true);
    expect(component.isUserMenuOpen()).toBe(false);
  });

  it('đóng các menu khi bấm phím Escape', () => {
    component.toggleUserMenu();
    component.toggleMobileMenu();
    expect(component.isMobileMenuOpen()).toBe(true);

    component.onEscapePress();
    expect(component.isUserMenuOpen()).toBe(false);
    expect(component.isMobileMenuOpen()).toBe(false);
  });

  it('thực hiện logout đầy đủ và điều hướng về trang sign-in', () => {
    component.toggleUserMenu();
    expect(component.isUserMenuOpen()).toBe(true);

    component.onLogout();
    expect(component.isUserMenuOpen()).toBe(false);
    expect(mockAuthService.logout).toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/sign-in']);
  });
});
