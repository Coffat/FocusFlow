import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { AppNavbarComponent } from './app-navbar.component';
import { AuthService } from '../../../core/services/auth.service';
import {
  NotificationService,
  type NotificationItemDTO,
} from '../../../core/services/notification.service';

describe('AppNavbarComponent', () => {
  let component: AppNavbarComponent;
  let fixture: ComponentFixture<AppNavbarComponent>;
  let router: Router;
  let mockAuthService: {
    currentUser: ReturnType<typeof signal<any>>;
    logout: ReturnType<typeof vi.fn>;
  };
  let mockNotificationService: {
    items: ReturnType<typeof signal<NotificationItemDTO[]>>;
    unreadCount: ReturnType<typeof signal<number>>;
    loading: ReturnType<typeof signal<boolean>>;
    error: ReturnType<typeof signal<string | null>>;
    loadNotifications: ReturnType<typeof vi.fn>;
    markRead: ReturnType<typeof vi.fn>;
    markAllRead: ReturnType<typeof vi.fn>;
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
    mockNotificationService = {
      items: signal<NotificationItemDTO[]>([]),
      unreadCount: signal<number>(0),
      loading: signal<boolean>(false),
      error: signal<string | null>(null),
      loadNotifications: vi.fn(),
      markRead: vi.fn().mockImplementation((id: string) =>
        of({
          id,
          notification_type: 'SCHEDULE_APPLIED',
          title: 'Lịch học mới',
          content: 'Đã áp dụng lịch học.',
          resource_url: '/schedule',
          is_read: true,
          read_at: '2026-11-21T09:15:00Z',
          created_at: '2026-11-21T09:00:00Z',
        }),
      ),
      markAllRead: vi.fn().mockReturnValue(of({ updated_count: 1 })),
    };

    await TestBed.configureTestingModule({
      imports: [AppNavbarComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService },
        { provide: NotificationService, useValue: mockNotificationService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AppNavbarComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('khởi tạo thành công AppNavbarComponent', () => {
    expect(component).toBeTruthy();
  });

  it('hiển thị thương hiệu FocusFlow và khẩu hiệu', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector<HTMLImageElement>('a[aria-label="FocusFlow Home"] img')?.getAttribute('src')).toBe('assets/logo.svg');
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

  describe('FE-MOCK-08: Trung tâm thông báo trên Navbar Bell', () => {
    it('tự động tải thông báo khi người dùng đã đăng nhập và hiển thị unread badge', () => {
      expect(mockNotificationService.loadNotifications).toHaveBeenCalledTimes(1);

      mockNotificationService.unreadCount.set(3);
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      const badge = el.querySelector('[data-testid="notification-unread-badge"]');
      expect(badge?.textContent?.trim()).toBe('3');
    });

    it('mở popover thông báo, hiển thị danh sách và gọi markRead + điều hướng khi bấm item chưa đọc', () => {
      const unreadItem: NotificationItemDTO = {
        id: 'notif-1',
        notification_type: 'SCHEDULE_APPLIED',
        title: 'Lịch học chính thức đã được áp dụng',
        content: 'Lộ trình TypeScript đã sẵn sàng.',
        resource_url: '/schedule',
        is_read: false,
        read_at: null,
        created_at: '2026-11-21T09:00:00Z',
      };
      mockNotificationService.items.set([unreadItem]);
      mockNotificationService.unreadCount.set(1);

      const el = fixture.nativeElement as HTMLElement;
      const bellBtn = el.querySelector('[data-testid="notification-bell-btn"]') as HTMLButtonElement;
      bellBtn.click();
      fixture.detectChanges();

      expect(el.querySelector('[data-testid="notification-popover"]')).toBeTruthy();
      const itemBtn = el.querySelector('[data-testid="notification-item"]') as HTMLButtonElement;
      expect(itemBtn.textContent).toContain('Lịch học chính thức đã được áp dụng');

      itemBtn.click();
      fixture.detectChanges();

      expect(mockNotificationService.markRead).toHaveBeenCalledWith('notif-1');
      expect(component.isNotificationsOpen()).toBe(false);
      expect(router.navigateByUrl).toHaveBeenCalledWith('/schedule');
    });

    it('gọi markAllRead khi nhấn nút Đánh dấu tất cả đã đọc', () => {
      mockNotificationService.unreadCount.set(2);
      component.toggleNotifications();
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      const markAllBtn = el.querySelector('[data-testid="notification-mark-all-btn"]') as HTMLButtonElement;
      markAllBtn.click();

      expect(mockNotificationService.markAllRead).toHaveBeenCalledTimes(1);
    });

    it('hiển thị trạng thái lỗi và nút Thử lại khi tải thông báo thất bại', () => {
      mockNotificationService.error.set('Không thể tải thông báo. Vui lòng thử lại.');
      component.toggleNotifications();
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="notification-error"]')?.textContent).toContain(
        'Không thể tải thông báo. Vui lòng thử lại.',
      );

      mockNotificationService.loadNotifications.mockClear();
      const retryBtn = el.querySelector('[data-testid="notification-retry-btn"]') as HTMLButtonElement;
      retryBtn.click();
      expect(mockNotificationService.loadNotifications).toHaveBeenCalledTimes(1);
    });
  });
});
