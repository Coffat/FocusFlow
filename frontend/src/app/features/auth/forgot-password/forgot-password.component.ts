import { Component, OnInit, DestroyRef, inject, ChangeDetectionStrategy, signal } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
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
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, ButtonModule, TranslatePipe],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent implements OnInit {
  readonly authService = inject(AuthService);
  readonly translationService = inject(TranslationService);
  readonly formBuilder = inject(FormBuilder);
  readonly router = inject(Router);
  readonly destroyRef = inject(DestroyRef);

  readonly forgotForm = this.formBuilder.group({
    email: ['', [Validators.required, strictEmailValidator]]
  });

  readonly otpForm = this.formBuilder.group({
    otpCode: ['', [Validators.required, Validators.pattern('^[0-9]{6}$')]]
  });

  readonly passwordForm = this.formBuilder.group({
    newPassword: ['', [Validators.required, passwordComplexityValidator]],
    confirmPassword: ['', [Validators.required]]
  });

  readonly step = signal<'email' | 'otp' | 'new_password'>('email');
  resetToken = '';

  readonly isLoading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly isSuccess = signal<boolean>(false);
  readonly successMessage = signal<string>('');
  readonly cooldownSeconds = signal<number>(0);
  readonly isPasswordVisible = signal<boolean>(false);
  readonly isConfirmPasswordVisible = signal<boolean>(false);
  private timerIntervalId: number = 0;

  ngOnInit() {
    this.errorMessage.set('');
    this.successMessage.set('');
    this.isSuccess.set(false);

    this.destroyRef.onDestroy(() => {
      this.clearCooldownTimer();
    });
  }

  get isPasswordMismatch(): boolean {
    return checkPasswordMismatch(
      this.passwordForm.get('newPassword')?.value || '',
      this.passwordForm.get('confirmPassword')?.value || ''
    );
  }

  togglePasswordVisibility() {
    this.isPasswordVisible.update(v => !v);
  }

  toggleConfirmPasswordVisibility() {
    this.isConfirmPasswordVisible.update(v => !v);
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
    this.cooldownSeconds.set(seconds);

    this.timerIntervalId = window.setInterval(() => {
      const current = this.cooldownSeconds();
      if (current <= 1) {
        this.cooldownSeconds.set(0);
        this.clearCooldownTimer();
      } else {
        this.cooldownSeconds.set(current - 1);
      }
    }, 1000);
  }

  // --- Step 1: Request OTP via Email ---
  requestReset() {
    if (this.forgotForm.invalid) {
      this.forgotForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    const emailValue = String(this.forgotForm.get('email')?.value || '').trim().toLowerCase();
    const payload: RequestPasswordResetOtpRequest = {
      email: emailValue
    };

    this.authService.requestPasswordResetOtp(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: MessageResponse) => {
          this.isLoading.set(false);
          this.step.set('otp');
          this.otpForm.reset();
          this.successMessage.set(response.message);
          this.startCooldown(60);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(err, 'Unable to dispatch code. Please try again.'));
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  // --- Step 2: Verify OTP ---
  verifyOtp() {
    if (this.otpForm.invalid) {
      this.otpForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

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
          this.isLoading.set(false);
          this.resetToken = response.reset_token;
          this.step.set('new_password');
          this.passwordForm.reset();
          this.successMessage.set(response.message);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(err, 'Invalid OTP verification code. Please try again.'));
        },
        complete: () => {
          this.isLoading.set(false);
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
      this.errorMessage.set(this.translationService.get('auth.forgotPassword.passwordMismatchError'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

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
          this.isLoading.set(false);
          this.isSuccess.set(true);
          this.successMessage.set(response.message);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(err, 'Password update failed. Please try again.'));
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  resendOtp() {
    if (this.cooldownSeconds() > 0 || this.isLoading()) return;
    this.requestReset();
  }

  backToEmail() {
    this.step.set('email');
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  backToOtp() {
    this.step.set('otp');
    this.errorMessage.set('');
    this.successMessage.set('');
  }
}
