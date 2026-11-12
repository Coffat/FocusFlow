import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { of, throwError, BehaviorSubject } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { OtpValidationComponent } from './otp-validation.component';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/services/translation.service';
import { LoginResponse, MessageResponse } from '../../../models/auth.interface';

describe('OtpValidationComponent', () => {
  let component: OtpValidationComponent;
  let fixture: ComponentFixture<OtpValidationComponent>;
  let router: Router;
  let queryParamsSubject: BehaviorSubject<Record<string, string>>;

  const mockAuthService = {
    verifyRegisterOtp: vi.fn(),
    resendRegisterOtp: vi.fn(),
    requestPasswordResetOtp: vi.fn()
  };

  const mockTranslationService = {
    get: vi.fn((key: string) => key),
    setLanguage: vi.fn(),
    currentLanguage: () => 'vi'
  };

  const mockLoginResponse: LoginResponse = {
    accessToken: 'valid-jwt-token',
    tokenType: 'Bearer',
    expiresIn: 3600,
    user: {
      id: 'usr-456',
      email: 'student@mit.edu',
      fullName: 'John Doe',
      role: 'learner',
      tier: 'free',
      createdAt: '2026-11-01T00:00:00Z'
    }
  };

  const mockMessageResponse: MessageResponse = {
    message: 'New OTP dispatched'
  };

  beforeEach(async () => {
    sessionStorage.clear();
    vi.clearAllMocks();
    queryParamsSubject = new BehaviorSubject<Record<string, string>>({
      email: 'student@mit.edu',
      flow: 'register'
    });

    await TestBed.configureTestingModule({
      imports: [OtpValidationComponent],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            queryParams: queryParamsSubject.asObservable()
          }
        },
        { provide: AuthService, useValue: mockAuthService },
        { provide: TranslationService, useValue: mockTranslationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(OtpValidationComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('should create and initialize email and flow from queryParams', () => {
    expect(component).toBeTruthy();
    expect(component.email()).toBe('student@mit.edu');
    expect(component.flow()).toBe('register');
    expect(sessionStorage.getItem('pending_register_email')).toBe('student@mit.edu');
    expect(component.isLoading()).toBe(false);
  });

  it('should fallback to sessionStorage if queryParams do not contain email', async () => {
    sessionStorage.setItem('pending_register_email', 'cached@stanford.edu');
    queryParamsSubject.next({});

    expect(component.email()).toBe('cached@stanford.edu');
  });

  describe('OTP Code handling', () => {
    it('should update currentOtp signal on onOtpChange', () => {
      component.onOtpChange('123');
      expect(component.currentOtp()).toBe('123');

      component.errorMessage.set('Previous error');
      component.onOtpChange('123456');
      expect(component.currentOtp()).toBe('123456');
      expect(component.errorMessage()).toBe('');
    });

    it('should invoke verifyOtp when onOtpCompleted is fired', () => {
      mockAuthService.verifyRegisterOtp.mockReturnValue(of(mockLoginResponse));
      component.onOtpCompleted('654321');

      expect(component.currentOtp()).toBe('654321');
      expect(mockAuthService.verifyRegisterOtp).toHaveBeenCalledWith({
        email: 'student@mit.edu',
        otpCode: '654321'
      });
    });
  });

  describe('verifyOtp', () => {
    it('should show error if code length is not 6', () => {
      component.currentOtp.set('12345');
      component.verifyOtp();

      expect(component.errorMessage()).toBe('auth.otp.otpRequiredError');
      expect(mockAuthService.verifyRegisterOtp).not.toHaveBeenCalled();
    });

    it('should show error if email is missing', () => {
      component.email.set('');
      component.currentOtp.set('123456');
      component.verifyOtp();

      expect(component.errorMessage()).toBe('auth.otp.sessionExpiredError');
      expect(mockAuthService.verifyRegisterOtp).not.toHaveBeenCalled();
    });

    it('should call verifyRegisterOtp and navigate to dashboard on success', () => {
      vi.useFakeTimers();
      mockAuthService.verifyRegisterOtp.mockReturnValue(of(mockLoginResponse));
      component.currentOtp.set('123456');

      component.verifyOtp();

      expect(mockAuthService.verifyRegisterOtp).toHaveBeenCalledWith({
        email: 'student@mit.edu',
        otpCode: '123456'
      });
      expect(component.successMessage()).toBe('auth.otp.verifySuccessRedirect');
      expect(sessionStorage.getItem('pending_register_email')).toBeNull();

      vi.advanceTimersByTime(400);
      expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
      vi.useRealTimers();
    });

    it('should handle verifyRegisterOtp error', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Invalid OTP code' },
        status: 400,
        statusText: 'Bad Request'
      });
      mockAuthService.verifyRegisterOtp.mockReturnValue(throwError(() => errorResponse));

      component.currentOtp.set('000000');
      component.verifyOtp();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Invalid OTP code');
      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('resendOtp', () => {
    it('should fail resend if email is empty', () => {
      component.email.set('');
      component.resendOtp();

      expect(component.errorMessage()).toBe('auth.otp.sessionExpiredError');
      expect(mockAuthService.resendRegisterOtp).not.toHaveBeenCalled();
    });

    it('should call resendRegisterOtp when flow is register', () => {
      mockAuthService.resendRegisterOtp.mockReturnValue(of(mockMessageResponse));
      component.flow.set('register');

      component.resendOtp();

      expect(mockAuthService.resendRegisterOtp).toHaveBeenCalledWith({ email: 'student@mit.edu' });
      expect(component.isLoading()).toBe(false);
      expect(component.successMessage()).toBe('New OTP dispatched');
    });

    it('should call requestPasswordResetOtp when flow is not register', () => {
      mockAuthService.requestPasswordResetOtp.mockReturnValue(of(mockMessageResponse));
      component.flow.set('reset');

      component.resendOtp();

      expect(mockAuthService.requestPasswordResetOtp).toHaveBeenCalledWith({ email: 'student@mit.edu' });
      expect(component.isLoading()).toBe(false);
      expect(component.successMessage()).toBe('New OTP dispatched');
    });

    it('should handle resendOtp error', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Too many requests' },
        status: 429,
        statusText: 'Too Many Requests'
      });
      mockAuthService.resendRegisterOtp.mockReturnValue(throwError(() => errorResponse));

      component.resendOtp();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Too many requests');
    });
  });

  describe('Backup Key Notice', () => {
    it('should show notice on onUseBackupKey', () => {
      component.errorMessage.set('Some error');
      component.onUseBackupKey();

      expect(component.errorMessage()).toBe('');
      expect(component.successMessage()).toBe('auth.otp.backupKeyNotice');
    });
  });
});
