import { Component, OnInit, DestroyRef, inject, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { HttpErrorResponse } from '@angular/common/http';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService, LanguageCode } from '../../../core/services/translation.service';
import { TranslatePipe } from '../../../shared/pipes/translate.pipe';
import {
  RequestPasswordResetOtpRequest,
  VerifyPasswordResetOtpRequest,
  VerifyPasswordResetOtpResponse,
  ConfirmPasswordResetRequest,
  MessageResponse
} from '../../../models/auth.interface';

import {
  passwordComplexityValidator,
  checkPasswordMismatch
} from '../../../shared/validators/password.validator';
import { strictEmailValidator } from '../../../shared/validators/email.validator';

@Component({
  selector: 'app-forgot-password',
  imports: [ReactiveFormsModule, RouterLink, ButtonModule, TranslatePipe],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent implements OnInit {
  authService: AuthService;
  translationService: TranslationService;
  formBuilder: FormBuilder;
  router: Router;
  destroyRef: DestroyRef;
  cdr: ChangeDetectorRef;

  forgotForm: FormGroup;
  otpForm: FormGroup;
  passwordForm: FormGroup;

  step: 'email' | 'otp' | 'new_password' = 'email';
  resetToken = '';

  isLoading = false;
  errorMessage = '';
  isSuccess = false;
  successMessage = '';
  cooldownSeconds = 0;
  isPasswordVisible = false;
  isConfirmPasswordVisible = false;
  private timerIntervalId: number = 0;

  constructor(
    authService: AuthService,
    translationService: TranslationService,
    formBuilder: FormBuilder,
    router: Router
  ) {
    this.authService = authService;
    this.translationService = translationService;
    this.formBuilder = formBuilder;
    this.router = router;
    this.destroyRef = inject(DestroyRef);
    this.cdr = inject(ChangeDetectorRef);

    this.forgotForm = this.formBuilder.group({
      email: ['', [Validators.required, strictEmailValidator]]
    });

    this.otpForm = this.formBuilder.group({
      otpCode: ['', [Validators.required, Validators.pattern('^[0-9]{6}$')]]
    });

    this.passwordForm = this.formBuilder.group({
      newPassword: ['', [Validators.required, passwordComplexityValidator]],
      confirmPassword: ['', [Validators.required]]
    });

    this.destroyRef.onDestroy(() => {
      this.clearCooldownTimer();
    });
  }

  ngOnInit() {
    this.errorMessage = '';
    this.successMessage = '';
    this.isSuccess = false;
  }

  get isPasswordMismatch(): boolean {
    return checkPasswordMismatch(
      this.passwordForm.get('newPassword')?.value,
      this.passwordForm.get('confirmPassword')?.value
    );
  }

  togglePasswordVisibility() {
    this.isPasswordVisible = !this.isPasswordVisible;
  }

  toggleConfirmPasswordVisibility() {
    this.isConfirmPasswordVisible = !this.isConfirmPasswordVisible;
  }

  switchLanguage(lang: LanguageCode) {
    this.translationService.setLanguage(lang);
  }

  private clearCooldownTimer() {
    if (this.timerIntervalId) {
      window.clearInterval(this.timerIntervalId);
      this.timerIntervalId = 0;
    }
  }

  startCooldown(seconds: number = 60) {
    this.clearCooldownTimer();
    this.cooldownSeconds = seconds;
    this.cdr.markForCheck();

    this.timerIntervalId = window.setInterval(() => {
      this.cooldownSeconds--;
      if (this.cooldownSeconds <= 0) {
        this.clearCooldownTimer();
      }
      this.cdr.markForCheck();
    }, 1000);
  }


  // --- Step 1: Request OTP via Email ---
  requestReset() {
    if (this.forgotForm.invalid) {
      this.forgotForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const emailValue = String(this.forgotForm.get('email')?.value || '').trim().toLowerCase();
    const payload: RequestPasswordResetOtpRequest = {
      email: emailValue
    };

    this.authService.requestPasswordResetOtp(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: MessageResponse) => {
          this.isLoading = false;
          this.step = 'otp';
          this.otpForm.reset();
          this.successMessage = response.message;
          this.startCooldown(60);
          this.cdr.markForCheck();
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(err, 'Unable to dispatch code. Please try again.');
          this.cdr.markForCheck();
        },
        complete: () => {
          this.isLoading = false;
          this.cdr.markForCheck();
        }
      });
  }

  // --- Step 2: Verify OTP ---
  verifyOtp() {
    if (this.otpForm.invalid) {
      this.otpForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const emailValue = String(this.forgotForm.get('email')?.value || '').trim().toLowerCase();
    const otpValue = String(this.otpForm.get('otpCode')?.value || '').trim();

    const payload: VerifyPasswordResetOtpRequest = {
      email: emailValue,
      otpCode: otpValue
    };

    this.authService.verifyPasswordResetOtp(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: VerifyPasswordResetOtpResponse) => {
          this.isLoading = false;
          this.resetToken = response.reset_token;
          this.step = 'new_password';
          this.passwordForm.reset();
          this.successMessage = response.message;
          this.cdr.markForCheck();
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(err, 'Invalid OTP verification code. Please try again.');
          this.cdr.markForCheck();
        },
        complete: () => {
          this.isLoading = false;
          this.cdr.markForCheck();
        }
      });
  }

  // --- Step 3: Set New Password ---
  confirmReset() {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }

    const newPass = String(this.passwordForm.get('newPassword')?.value || '');
    const confirmPass = String(this.passwordForm.get('confirmPassword')?.value || '');

    if (newPass !== confirmPass) {
      this.errorMessage = this.translationService.get('auth.forgotPassword.passwordMismatchError');
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const emailValue = String(this.forgotForm.get('email')?.value || '').trim().toLowerCase();

    const payload: ConfirmPasswordResetRequest = {
      email: emailValue,
      newPassword: newPass,
      resetToken: this.resetToken
    };

    this.authService.confirmPasswordReset(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: MessageResponse) => {
          this.isLoading = false;
          this.isSuccess = true;
          this.successMessage = response.message;
          this.cdr.markForCheck();
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(err, 'Password update failed. Please try again.');
          this.cdr.markForCheck();
        },
        complete: () => {
          this.isLoading = false;
          this.cdr.markForCheck();
        }
      });
  }

  resendOtp() {
    if (this.cooldownSeconds > 0 || this.isLoading) return;
    this.requestReset();
  }

  backToEmail() {
    this.step = 'email';
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.markForCheck();
  }

  backToOtp() {
    this.step = 'otp';
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.markForCheck();
  }
}
