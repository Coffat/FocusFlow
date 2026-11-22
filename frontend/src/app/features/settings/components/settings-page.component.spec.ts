import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, ActivatedRoute, Router } from '@angular/router';
import { signal } from '@angular/core';
import { MessageService, ConfirmationService } from 'primeng/api';
import { SettingsPageComponent } from './settings-page.component';
import { SettingsService } from '../services/settings.service';
import { AuthService } from '../../../core/services/auth.service';
import type {
  AIQuotaResponseDTO,
  UserPreferences,
  WebcalStatusResponseDTO,
} from '../models/settings.model';

describe('SettingsPageComponent', () => {
  let component: SettingsPageComponent;
  let fixture: ComponentFixture<SettingsPageComponent>;

  const mockUser = {
    id: '11111111-1111-1111-1111-111111111111',
    email: 'learner@focusflow.ai',
    fullName: 'Minh Hoàng',
    role: 'learner' as const,
    tier: 'PRO',
    createdAt: '2026-01-01T00:00:00Z',
  };

  const mockQuota: AIQuotaResponseDTO = {
    monthly_limit: 20,
    used_calls: 5,
    reserved_calls: 1,
    remaining_calls: 14,
    tokens_consumed: 6500,
    cycle_start: '2026-01-01T00:00:00Z',
    cycle_end: '2026-01-31T23:59:59Z',
  };

  const mockPreferences: UserPreferences = {
    theme: 'light',
    soundEnabled: true,
    defaultPomodoroDuration: 25,
    shortBreakDuration: 5,
    longBreakDuration: 15,
    aiCreditsLimit: 20,
    aiCreditsUsed: 5,
  };

  let mockSettingsService: {
    preferences: ReturnType<typeof signal<UserPreferences>>;
    quota: ReturnType<typeof signal<AIQuotaResponseDTO | null>>;
    quotaLoading: ReturnType<typeof signal<boolean>>;
    quotaError: ReturnType<typeof signal<string | null>>;
    passwordSaving: ReturnType<typeof signal<boolean>>;
    webcalStatus: ReturnType<typeof signal<WebcalStatusResponseDTO | null>>;
    webcalUrl: ReturnType<typeof signal<string | null>>;
    webcalLoading: ReturnType<typeof signal<boolean>>;
    webcalError: ReturnType<typeof signal<string | null>>;
    exportLoading: ReturnType<typeof signal<boolean>>;
    exportError: ReturnType<typeof signal<string | null>>;
    loadQuota: ReturnType<typeof vi.fn>;
    loadWebcalStatus: ReturnType<typeof vi.fn>;
    rotateWebcalToken: ReturnType<typeof vi.fn>;
    revokeWebcalToken: ReturnType<typeof vi.fn>;
    exportAccountData: ReturnType<typeof vi.fn>;
    savePreferences: ReturnType<typeof vi.fn>;
    changePassword: ReturnType<typeof vi.fn>;
  };

  let mockAuthService: {
    currentUser: ReturnType<typeof signal<any>>;
  };

  let mockMessageService: { add: ReturnType<typeof vi.fn> };
  let mockConfirmationService: { confirm: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    mockSettingsService = {
      preferences: signal(mockPreferences),
      quota: signal(mockQuota),
      quotaLoading: signal(false),
      quotaError: signal<string | null>(null),
      passwordSaving: signal(false),
      webcalStatus: signal<WebcalStatusResponseDTO | null>({
        has_active_token: false,
        is_active: false,
        rotated_at: null,
        last_used_at: null,
      }),
      webcalUrl: signal<string | null>(null),
      webcalLoading: signal(false),
      webcalError: signal<string | null>(null),
      exportLoading: signal(false),
      exportError: signal<string | null>(null),
      loadQuota: vi.fn().mockResolvedValue(undefined),
      loadWebcalStatus: vi.fn().mockResolvedValue(undefined),
      rotateWebcalToken: vi.fn().mockResolvedValue({
        webcal_url: 'webcal://localhost:8000/api/v1/feeds/new_real_token.ics',
        feed_url: 'http://localhost:8000/api/v1/feeds/new_real_token.ics',
        rotated_at: '2026-11-21T09:00:00Z',
      }),
      revokeWebcalToken: vi.fn().mockResolvedValue(true),
      exportAccountData: vi.fn().mockResolvedValue({
        schema_version: '1.0',
        exported_at: '2026-11-21T09:30:00Z',
        user: {
          id: mockUser.id,
          email: mockUser.email,
          full_name: mockUser.fullName,
          timezone: 'Asia/Ho_Chi_Minh',
          tier: mockUser.tier,
          role: 'LEARNER',
          created_at: mockUser.createdAt,
        },
        analytics_summary: {
          total_study_minutes: 0,
          current_streak_days: 0,
          longest_streak_days: 0,
        },
        study_sessions_count: 0,
        tasks_count: 0,
        roadmaps: [],
      }),
      savePreferences: vi.fn(),
      changePassword: vi.fn().mockResolvedValue({ message: 'Success' }),
    };

    mockAuthService = {
      currentUser: signal(mockUser),
    };

    mockMessageService = { add: vi.fn() };
    mockConfirmationService = { confirm: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [SettingsPageComponent],
      providers: [
        provideRouter([{ path: '**', component: SettingsPageComponent }]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SettingsService, useValue: mockSettingsService },
        { provide: AuthService, useValue: mockAuthService },
        { provide: MessageService, useValue: mockMessageService },
        { provide: ConfirmationService, useValue: mockConfirmationService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SettingsPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công SettingsPageComponent', () => {
    expect(component).toBeTruthy();
    expect(mockSettingsService.loadQuota).toHaveBeenCalled();
    expect(component.userTier()).toBe('PRO');
    expect(component.quotaUsagePercent()).toBe(25);
  });

  it('cập nhật tùy chọn học tập qua updatePreference', () => {
    component.updatePreference('defaultPomodoroDuration', 45);
    expect(mockSettingsService.savePreferences).toHaveBeenCalledWith({
      defaultPomodoroDuration: 45,
    });
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'success' })
    );
  });

  it('kiểm tra độ mạnh mật khẩu chuẩn xác', () => {
    component.passwordForm.patchValue({ new_password: 'abc' });
    component.checkPasswordStrength();
    expect(component.hasMinLength()).toBe(false);
    expect(component.hasUpper()).toBe(false);
    expect(component.isPasswordStrong()).toBe(false);

    component.passwordForm.patchValue({ new_password: 'ValidPassword123!' });
    component.checkPasswordStrength();
    expect(component.hasMinLength()).toBe(true);
    expect(component.hasUpper()).toBe(true);
    expect(component.hasLower()).toBe(true);
    expect(component.hasNumberOrSpecial()).toBe(true);
    expect(component.isPasswordStrong()).toBe(true);
  });

  it('kiểm tra mật khẩu xác nhận không khớp', () => {
    component.passwordForm.patchValue({
      new_password: 'ValidPassword123!',
      confirm_password: 'DifferentPassword123!',
    });
    expect(component.passwordsMismatch()).toBe(true);

    component.passwordForm.patchValue({
      confirm_password: 'ValidPassword123!',
    });
    expect(component.passwordsMismatch()).toBe(false);
  });

  it('gọi onChangePassword cập nhật mật khẩu khi dữ liệu hợp lệ', async () => {
    component.passwordForm.patchValue({
      current_password: 'OldPassword123!',
      new_password: 'ValidPassword123!',
      confirm_password: 'ValidPassword123!',
    });
    component.checkPasswordStrength();

    await component.onChangePassword();

    expect(mockSettingsService.changePassword).toHaveBeenCalledWith({
      current_password: 'OldPassword123!',
      new_password: 'ValidPassword123!',
    });
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'success' })
    );
  });

  it('FE-MOCK-04: vô hiệu hóa nút xóa tài khoản GDPR, hiển thị thông báo trung thực và KHÔNG mở dialog hay bắn toast giả', () => {
    component.setTab('security');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const deleteBtn = compiled.querySelector(
      '[data-testid="delete-account-btn"]'
    ) as HTMLButtonElement | null;
    expect(deleteBtn).toBeTruthy();
    expect(deleteBtn?.disabled).toBe(true);
    expect(deleteBtn?.getAttribute('aria-disabled')).toBe('true');

    const notice = compiled.querySelector('[data-testid="delete-account-unavailable-notice"]');
    expect(notice).toBeTruthy();
    expect(notice?.textContent).toContain('FR-PROFILE-002');
    expect(notice?.textContent).toContain('chưa khả dụng');

    component.onRequestDeleteAccount();
    expect(mockConfirmationService.confirm).not.toHaveBeenCalled();
    expect(mockMessageService.add).not.toHaveBeenCalled();
  });

  it('xử lý kết nối và ngắt kết nối Google Calendar 1-Click', () => {
    const connectSpy = vi.spyOn(component.calendarService, 'connectGoogleCalendar').mockImplementation(() => {});
    const disconnectSpy = vi.spyOn(component.calendarService, 'disconnectGoogleCalendar');

    // 1. Click connect without returnUrl -> default return_to
    component.onConnectGoogleCalendar();
    expect(connectSpy).toHaveBeenCalledWith('/settings?tab=calendar');

    // 2. Click connect with returnUrl & autoOpen -> encoded return_to
    component.returnUrl.set('/roadmaps');
    component.autoOpen.set(true);
    component.onConnectGoogleCalendar();
    expect(connectSpy).toHaveBeenCalledWith(
      '/settings?tab=calendar&returnUrl=%2Froadmaps&autoOpen=true'
    );

    // 3. Click disconnect triggers confirmation dialog
    component.onDisconnectGoogleCalendar();
    expect(mockConfirmationService.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        header: 'Xác nhận ngắt kết nối',
      })
    );
  });

  it('trích xuất returnUrl, autoOpen và focus=calendar từ query params trong ngOnInit', async () => {
    const router = TestBed.inject(Router);
    await router.navigate([], {
      queryParams: {
        returnUrl: '/roadmaps/new',
        autoOpen: 'true',
        focus: 'calendar',
      },
    });

    component.ngOnInit();

    expect(component.returnUrl()).toBe('/roadmaps/new');
    expect(component.autoOpen()).toBe(true);
    expect(component.activeTab()).toBe('calendar');
  });

  it('gọi scrollIntoView mượt mà tới google-calendar-section khi scrollToGoogleCalendarSection được gọi', () => {
    const mockElement = document.createElement('section');
    mockElement.id = 'google-calendar-section';
    mockElement.scrollIntoView = vi.fn();
    document.body.appendChild(mockElement);

    component.scrollToGoogleCalendarSection();

    expect(mockElement.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'start',
    });

    document.body.removeChild(mockElement);
  });

  it('điều hướng trở lại Lộ trình với continueToRoadmap kèm autoOpen', () => {
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

    // Case 1: returnUrl without query params and autoOpen=true
    component.returnUrl.set('/roadmaps');
    component.autoOpen.set(true);
    component.continueToRoadmap();
    expect(navigateSpy).toHaveBeenCalledWith('/roadmaps?autoOpen=true');

    // Case 2: returnUrl with existing query params and autoOpen=true
    component.returnUrl.set('/roadmaps?mode=create');
    component.autoOpen.set(true);
    component.continueToRoadmap();
    expect(navigateSpy).toHaveBeenCalledWith('/roadmaps?mode=create&autoOpen=true');

    // Case 3: returnUrl already has autoOpen=true
    component.returnUrl.set('/roadmaps?autoOpen=true');
    component.autoOpen.set(true);
    component.continueToRoadmap();
    expect(navigateSpy).toHaveBeenCalledWith('/roadmaps?autoOpen=true');

    // Case 4: returnUrl is null -> defaults to /roadmaps
    component.returnUrl.set(null);
    component.autoOpen.set(false);
    component.continueToRoadmap();
    expect(navigateSpy).toHaveBeenCalledWith('/roadmaps');
  });

  it('hiển thị Banner thành công và nút [Tiếp tục tạo Lộ trình] khi returnUrl có giá trị và Calendar đã kết nối', () => {
    component.setTab('calendar');
    component.returnUrl.set('/roadmaps');
    component.autoOpen.set(true);

    // Mock calendar connected
    vi.spyOn(component.calendarService, 'isConnected').mockReturnValue(true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;

    // Check back links
    const tabBackLink = compiled.querySelector('[data-testid="tab-back-to-roadmap-link"]');
    expect(tabBackLink).toBeTruthy();
    expect(tabBackLink?.textContent).toContain('Quay lại Lộ trình');

    const headerBackLink = compiled.querySelector('[data-testid="header-back-to-roadmap-link"]');
    expect(headerBackLink).toBeTruthy();

    // Check success banner
    const banner = compiled.querySelector('[data-testid="calendar-success-banner"]');
    expect(banner).toBeTruthy();
    expect(banner?.textContent).toContain(
      'Đã liên kết Google Calendar thành công! Bạn đã đủ điều kiện để AI lập lịch học tự động.'
    );

    // Check CTA button
    const continueBtn = compiled.querySelector('[data-testid="continue-to-roadmap-btn"]') as HTMLButtonElement;
    expect(continueBtn).toBeTruthy();
    expect(continueBtn.textContent).toContain('Tiếp tục tạo Lộ trình');

    const continueSpy = vi.spyOn(component, 'continueToRoadmap');
    continueBtn.click();
    expect(continueSpy).toHaveBeenCalled();
  });

  it('chuyển đổi giữa 4 horizontal tabs và cập nhật query param tab', () => {
    expect(component.activeTab()).toBe('general');

    component.setTab('ai');
    expect(component.activeTab()).toBe('ai');

    component.setTab('calendar');
    expect(component.activeTab()).toBe('calendar');

    component.setTab('security');
    expect(component.activeTab()).toBe('security');

    component.setTab('general');
    expect(component.activeTab()).toBe('general');
  });

  it('hỗ trợ điều hướng phím mũi tên giữa 4 tab (A11y roving tabindex)', () => {
    const eventRight = new KeyboardEvent('keydown', { key: 'ArrowRight' });
    component.onTabKeydown(eventRight, 'general');
    expect(component.activeTab()).toBe('ai');

    component.onTabKeydown(eventRight, 'ai');
    expect(component.activeTab()).toBe('calendar');

    const eventLeft = new KeyboardEvent('keydown', { key: 'ArrowLeft' });
    component.onTabKeydown(eventLeft, 'calendar');
    expect(component.activeTab()).toBe('ai');
  });

  it('tự động cập nhật checklist độ mạnh mật khẩu khi nhập liệu qua valueChanges', () => {
    component.passwordForm.get('new_password')?.setValue('ComplexPass123!');
    expect(component.hasMinLength()).toBe(true);
    expect(component.hasUpper()).toBe(true);
    expect(component.hasLower()).toBe(true);
    expect(component.hasNumberOrSpecial()).toBe(true);
    expect(component.isPasswordStrong()).toBe(true);
  });

  it('FE-MOCK-03: xuất dữ liệu cá nhân GDPR thật qua exportAccountData khi backend thành công', async () => {
    const createObjectUrlSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock');
    const revokeObjectUrlSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    await component.onExportData();

    expect(mockSettingsService.exportAccountData).toHaveBeenCalledTimes(1);
    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith('blob:mock');
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        summary: 'Đã xuất dữ liệu',
      })
    );

    createObjectUrlSpy.mockRestore();
    revokeObjectUrlSpy.mockRestore();
  });

  it('FE-MOCK-03: hiển thị toast lỗi và KHÔNG tải tệp giả hay bắn toast thành công khi exportAccountData thất bại', async () => {
    mockSettingsService.exportAccountData.mockResolvedValueOnce(null);
    mockSettingsService.exportError.set('Không thể xuất dữ liệu cá nhân lúc này. Vui lòng thử lại sau.');
    const createObjectUrlSpy = vi.spyOn(URL, 'createObjectURL');

    await component.onExportData();

    expect(createObjectUrlSpy).not.toHaveBeenCalled();
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'error',
        summary: 'Lỗi xuất dữ liệu',
      })
    );
    expect(mockMessageService.add).not.toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'success' })
    );
    createObjectUrlSpy.mockRestore();
  });

  describe('FE-MOCK-01: 4 trạng thái UI tường minh cho AI Quota (Loading, Error, Empty, Success)', () => {
    it('hiển thị trạng thái Loading khi quotaLoading() === true', () => {
      component.setTab('ai');
      mockSettingsService.quotaLoading.set(true);
      mockSettingsService.quotaError.set(null);
      mockSettingsService.quota.set(null);
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="quota-loading-state"]')).toBeTruthy();
      expect(el.querySelector('[data-testid="quota-error-state"]')).toBeNull();
      expect(el.querySelector('[data-testid="quota-success-state"]')).toBeNull();
      expect(el.querySelector('[data-testid="quota-empty-state"]')).toBeNull();
    });

    it('hiển thị trạng thái Error với nút Thử lại khi quotaError() có giá trị và KHÔNG hiển thị số liệu giả (3450 / 10 / 2)', () => {
      component.setTab('ai');
      mockSettingsService.quotaLoading.set(false);
      mockSettingsService.quota.set(null);
      mockSettingsService.quotaError.set('Không thể tải thông tin hạn ngạch AI. Vui lòng thử lại.');
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      const errorState = el.querySelector('[data-testid="quota-error-state"]');
      expect(errorState).toBeTruthy();
      expect(errorState?.textContent).toContain(
        'Không thể tải thông tin hạn ngạch AI. Vui lòng thử lại.'
      );
      expect(el.querySelector('[data-testid="quota-success-state"]')).toBeNull();
      expect(el.textContent).not.toContain('3,450');
      expect(el.textContent).not.toContain('3450');
      expect(component.quotaUsagePercent()).toBe(0);

      mockSettingsService.loadQuota.mockClear();
      const retryBtn = el.querySelector('[data-testid="quota-retry-btn"]') as HTMLButtonElement;
      expect(retryBtn).toBeTruthy();
      retryBtn.click();
      expect(mockSettingsService.loadQuota).toHaveBeenCalledTimes(1);
    });

    it('hiển thị trạng thái Empty khi không loading, không lỗi và quota() === null', () => {
      component.setTab('ai');
      mockSettingsService.quotaLoading.set(false);
      mockSettingsService.quotaError.set(null);
      mockSettingsService.quota.set(null);
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="quota-empty-state"]')).toBeTruthy();
      expect(el.querySelector('[data-testid="quota-success-state"]')).toBeNull();
      expect(el.textContent).not.toContain('3,450');
      expect(component.quotaUsagePercent()).toBe(0);
    });

    it('hiển thị trạng thái Success với đúng số liệu thật từ backend khi quota() có dữ liệu', () => {
      component.setTab('ai');
      mockSettingsService.quotaLoading.set(false);
      mockSettingsService.quotaError.set(null);
      mockSettingsService.quota.set(mockQuota);
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="quota-success-state"]')).toBeTruthy();
      expect(el.querySelector('[data-testid="quota-used-calls"]')?.textContent?.trim()).toBe('5');
      expect(el.querySelector('[data-testid="quota-reserved-calls"]')?.textContent?.trim()).toBe('1');
      expect(el.querySelector('[data-testid="quota-remaining-calls"]')?.textContent?.trim()).toBe('14');
      expect(el.querySelector('[data-testid="quota-tokens-consumed"]')?.textContent?.trim()).toBe('6,500');
      expect(component.quotaUsagePercent()).toBe(25);
    });
  });

  describe('FE-MOCK-02: Tích hợp WebCal thật (không còn token giả ff_live_sec_789123)', () => {
    it('hiển thị trạng thái chưa tạo WebCal và không chứa token giả cứng', () => {
      component.setTab('calendar');
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      expect(mockSettingsService.loadWebcalStatus).toHaveBeenCalled();
      expect(el.textContent).not.toContain('ff_live_sec_789123');
      expect(el.querySelector('[data-testid="webcal-inactive-status"]')).toBeTruthy();

      const createBtn = el.querySelector('[data-testid="webcal-create-btn"]') as HTMLButtonElement;
      createBtn.click();
      expect(mockSettingsService.rotateWebcalToken).toHaveBeenCalledTimes(1);
    });

    it('hiển thị URL một lần + cảnh báo bảo mật khi vừa xoay vòng token', () => {
      component.setTab('calendar');
      mockSettingsService.webcalUrl.set('webcal://localhost:8000/api/v1/feeds/once-token.ics');
      mockSettingsService.webcalStatus.set({
        has_active_token: true,
        is_active: true,
        rotated_at: '2026-11-21T09:00:00Z',
        last_used_at: null,
      });
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      const input = el.querySelector('[data-testid="webcal-url-input"]') as HTMLInputElement;
      expect(input?.value).toBe('webcal://localhost:8000/api/v1/feeds/once-token.ics');
      expect(el.querySelector('[data-testid="webcal-onetime-warning"]')).toBeTruthy();
    });

    it('hiển thị trạng thái đang hoạt động (đã băm SHA-256) khi reload mà không có URL một lần', () => {
      component.setTab('calendar');
      mockSettingsService.webcalUrl.set(null);
      mockSettingsService.webcalStatus.set({
        has_active_token: true,
        is_active: true,
        rotated_at: '2026-11-21T09:00:00Z',
        last_used_at: null,
      });
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="webcal-active-status"]')).toBeTruthy();
      expect(el.querySelector('[data-testid="webcal-url-input"]')).toBeNull();
    });

    it('hiển thị banner lỗi khi webcalError() có giá trị', () => {
      component.setTab('calendar');
      mockSettingsService.webcalError.set('Không thể tải trạng thái liên kết WebCal.');
      fixture.detectChanges();

      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="webcal-error-banner"]')?.textContent).toContain(
        'Không thể tải trạng thái liên kết WebCal.'
      );
    });
  });
});
