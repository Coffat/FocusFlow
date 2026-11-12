import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { MessageService, ConfirmationService } from 'primeng/api';
import { SettingsPageComponent } from './settings-page.component';
import { SettingsService } from '../services/settings.service';
import { AuthService } from '../../../core/services/auth.service';
import type { AIQuotaResponseDTO, UserPreferences } from '../models/settings.model';

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
    passwordSaving: ReturnType<typeof signal<boolean>>;
    loadQuota: ReturnType<typeof vi.fn>;
    savePreferences: ReturnType<typeof vi.fn>;
    changePassword: ReturnType<typeof vi.fn>;
    resetWebCalToken: ReturnType<typeof vi.fn>;
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
      passwordSaving: signal(false),
      loadQuota: vi.fn().mockResolvedValue(undefined),
      savePreferences: vi.fn(),
      changePassword: vi.fn().mockResolvedValue({ message: 'Success' }),
      resetWebCalToken: vi.fn().mockResolvedValue({
        webcal_url: 'webcal://focusflow.app/api/v1/calendar/feed.ics?token=new_token',
      }),
    };

    mockAuthService = {
      currentUser: signal(mockUser),
    };

    mockMessageService = { add: vi.fn() };
    mockConfirmationService = { confirm: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [SettingsPageComponent],
      providers: [
        provideRouter([]),
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

  it('mở hộp thoại xác nhận khi yêu cầu xóa tài khoản GDPR', () => {
    component.onRequestDeleteAccount();
    expect(mockConfirmationService.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        header: 'Xác nhận Xóa Vĩnh Viễn Tài Khoản',
      })
    );
  });

  it('xử lý kết nối và ngắt kết nối Google Calendar 1-Click', () => {
    const connectSpy = vi.spyOn(component.calendarService, 'connectGoogleCalendar').mockImplementation(() => {});
    const disconnectSpy = vi.spyOn(component.calendarService, 'disconnectGoogleCalendar');

    // 1. Click connect
    component.onConnectGoogleCalendar();
    expect(connectSpy).toHaveBeenCalledWith('/settings?tab=calendar');

    // 2. Click disconnect triggers confirmation dialog
    component.onDisconnectGoogleCalendar();
    expect(mockConfirmationService.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        header: 'Xác nhận ngắt kết nối',
      })
    );
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

  it('xuất dữ liệu cá nhân GDPR thành công với onExportData', () => {
    component.onExportData();
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        summary: 'Đã xuất dữ liệu',
      })
    );
  });
});
