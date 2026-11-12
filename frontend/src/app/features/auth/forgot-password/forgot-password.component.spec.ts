import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { ForgotPasswordComponent } from './forgot-password.component';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/services/translation.service';
import {
  MessageResponse,
  VerifyPasswordResetOtpResponse
} from '../../../models/auth.interface';

describe('ForgotPasswordComponent', () => {
  let component: ForgotPasswordComponent;
  let fixture: ComponentFixture<ForgotPasswordComponent>;

  const mockAuthService = {
    requestPasswordResetOtp: vi.fn(),
    verifyPasswordResetOtp: vi.fn(),
    confirmPasswordReset: vi.fn()
  };

  const mockTranslationService = {
    get: vi.fn((key: string) => key),
    setLanguage: vi.fn(),
    currentLanguage: () => 'vi'
  };

  const mockMessageResponse: MessageResponse = {
    message: 'OTP sent'
  };

  const mockVerifyOtpResponse: VerifyPasswordResetOtpResponse = {
    message: 'OTP verified',
    reset_token: 'valid-reset-token-123'
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [ForgotPasswordComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: mockAuthService },
        { provide: TranslationService, useValue: mockTranslationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ForgotPasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and initialize in email step', () => {
    expect(component).toBeTruthy();
    expect(component.step()).toBe('email');
    expect(component.isLoading()).toBe(false);
    expect(component.isSuccess()).toBe(false);
    expect(component.forgotForm.get('email')?.value).toBe('');
  });

  describe('Step 1: Request Password Reset OTP', () => {
    it('should not call authService if email is invalid', () => {
      component.forgotForm.setValue({ email: 'invalid-email' });
      component.requestReset();

      expect(component.forgotForm.touched).toBe(true);
      expect(mockAuthService.requestPasswordResetOtp).not.toHaveBeenCalled();
    });

    it('should request OTP and advance to otp step on success', () => {
      mockAuthService.requestPasswordResetOtp.mockReturnValue(of(mockMessageResponse));

      component.forgotForm.setValue({ email: 'scholar@oxford.ac.uk' });
      component.requestReset();

      expect(mockAuthService.requestPasswordResetOtp).toHaveBeenCalledWith({
        email: 'scholar@oxford.ac.uk'
      });
      expect(component.step()).toBe('otp');
      expect(component.isLoading()).toBe(false);
      expect(component.successMessage()).toBe('OTP sent');
    });

    it('should handle request OTP error', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Account does not exist' },
        status: 404,
        statusText: 'Not Found'
      });
      mockAuthService.requestPasswordResetOtp.mockReturnValue(throwError(() => errorResponse));

      component.forgotForm.setValue({ email: 'unknown@oxford.ac.uk' });
      component.requestReset();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Account does not exist');
      expect(component.step()).toBe('email');
    });
  });

  describe('Step 2: Verify OTP', () => {
    beforeEach(() => {
      component.forgotForm.setValue({ email: 'scholar@oxford.ac.uk' });
      component.step.set('otp');
    });

    it('should update currentOtpCode on onOtpChange and onOtpCompleted', () => {
      component.onOtpChange('1234');
      expect(component.currentOtpCode()).toBe('1234');

      mockAuthService.verifyPasswordResetOtp.mockReturnValue(of(mockVerifyOtpResponse));
      component.onOtpCompleted('123456');
      expect(component.currentOtpCode()).toBe('123456');
      expect(mockAuthService.verifyPasswordResetOtp).toHaveBeenCalledWith({
        email: 'scholar@oxford.ac.uk',
        otpCode: '123456'
      });
    });

    it('should show error if verifyOtp is called with incomplete code', () => {
      component.currentOtpCode.set('123');
      component.verifyOtp();

      expect(component.errorMessage()).toBe('auth.otp.otpRequiredError');
      expect(mockAuthService.verifyPasswordResetOtp).not.toHaveBeenCalled();
    });

    it('should verify OTP and advance to new_password step on success', () => {
      mockAuthService.verifyPasswordResetOtp.mockReturnValue(of(mockVerifyOtpResponse));

      component.currentOtpCode.set('654321');
      component.verifyOtp();

      expect(mockAuthService.verifyPasswordResetOtp).toHaveBeenCalledWith({
        email: 'scholar@oxford.ac.uk',
        otpCode: '654321'
      });
      expect(component.resetToken).toBe('valid-reset-token-123');
      expect(component.step()).toBe('new_password');
      expect(component.isLoading()).toBe(false);
    });

    it('should handle verify OTP error', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Invalid or expired OTP' },
        status: 400,
        statusText: 'Bad Request'
      });
      mockAuthService.verifyPasswordResetOtp.mockReturnValue(throwError(() => errorResponse));

      component.currentOtpCode.set('999999');
      component.verifyOtp();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Invalid or expired OTP');
      expect(component.step()).toBe('otp');
    });

    it('should allow user to go back to email step', () => {
      component.backToEmail();
      expect(component.step()).toBe('email');
      expect(component.errorMessage()).toBe('');
      expect(component.successMessage()).toBe('');
    });
  });

  describe('Step 3: New Password & Confirmation', () => {
    beforeEach(() => {
      component.forgotForm.setValue({ email: 'scholar@oxford.ac.uk' });
      component.resetToken = 'valid-reset-token-123';
      component.step.set('new_password');
    });

    it('should calculate password entropy when new password changes', () => {
      const newPassCtrl = component.passwordForm.get('newPassword');
      newPassCtrl?.setValue('weak');
      expect(component.passwordStrength()).toBeLessThanOrEqual(1);

      newPassCtrl?.setValue('SecurePass123!');
      expect(component.passwordStrength()).toBeGreaterThanOrEqual(3);
      expect(component.isPasswordValid).toBe(true);
    });

    it('should reject submission if passwordForm is invalid', () => {
      component.confirmReset();
      expect(component.passwordForm.touched).toBe(true);
      expect(mockAuthService.confirmPasswordReset).not.toHaveBeenCalled();
    });

    it('should show error if passwords mismatch', () => {
      component.passwordForm.setValue({
        newPassword: 'SecurePassword123!',
        confirmPassword: 'MismatchPassword123!'
      });

      component.confirmReset();
      expect(component.isPasswordMismatch).toBe(true);
      expect(component.errorMessage()).toBe('auth.forgotPassword.passwordMismatchError');
      expect(mockAuthService.confirmPasswordReset).not.toHaveBeenCalled();
    });

    it('should confirm reset and transition to success view', () => {
      mockAuthService.confirmPasswordReset.mockReturnValue(of(mockMessageResponse));

      component.passwordForm.setValue({
        newPassword: 'SecurePassword123!',
        confirmPassword: 'SecurePassword123!'
      });

      component.confirmReset();

      expect(mockAuthService.confirmPasswordReset).toHaveBeenCalledWith({
        email: 'scholar@oxford.ac.uk',
        newPassword: 'SecurePassword123!',
        resetToken: 'valid-reset-token-123'
      });
      expect(component.isSuccess()).toBe(true);
      expect(component.isLoading()).toBe(false);
    });

    it('should handle confirm reset error', () => {
      const errorResponse = new HttpErrorResponse({
        error: { detail: 'Token expired' },
        status: 400,
        statusText: 'Bad Request'
      });
      mockAuthService.confirmPasswordReset.mockReturnValue(throwError(() => errorResponse));

      component.passwordForm.setValue({
        newPassword: 'SecurePassword123!',
        confirmPassword: 'SecurePassword123!'
      });

      component.confirmReset();

      expect(component.isLoading()).toBe(false);
      expect(component.errorMessage()).toContain('Token expired');
      expect(component.isSuccess()).toBe(false);
    });
  });

  describe('Password Visibility Toggles', () => {
    it('should toggle password visibility signals', () => {
      expect(component.isPasswordVisible()).toBe(false);
      component.togglePasswordVisibility();
      expect(component.isPasswordVisible()).toBe(true);

      expect(component.isConfirmPasswordVisible()).toBe(false);
      component.toggleConfirmPasswordVisibility();
      expect(component.isConfirmPasswordVisible()).toBe(true);
    });
  });
});
