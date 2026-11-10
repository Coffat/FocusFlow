import { Component, OnInit, DestroyRef, inject, ChangeDetectionStrategy, signal } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
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
import { OtpInputComponent } from '../shared/otp-input/otp-input.component';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    TranslatePipe,
    OtpInputComponent
  ],
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

  readonly passwordForm = this.formBuilder.group({
    newPassword: ['', [Validators.required, passwordComplexityValidator]],
    confirmPassword: ['', [Validators.required]]
  });

  readonly step = signal<'email' | 'otp' | 'new_password'>('email');
  resetToken = '';
  currentOtpCode = signal<string>('');

  readonly isLoading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly isSuccess = signal<boolean>(false);
  readonly successMessage = signal<string>('');
  readonly isPasswordVisible = signal<boolean>(false);
  readonly isConfirmPasswordVisible = signal<boolean>(false);

  ngOnInit() {
    this.errorMessage.set('');
    this.successMessage.set('');
    this.isSuccess.set(false);
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
          this.currentOtpCode.set('');
          this.successMessage.set(
            response.message || this.translationService.get('auth.forgotPassword.codeSentSuccess')
          );
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            parseHttpErrorMessage(err, this.translationService.get('auth.forgotPassword.dispatchError'))
          );
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  onOtpChange(code: string) {
    this.currentOtpCode.set(code);
  }

  onOtpCompleted(code: string) {
    this.currentOtpCode.set(code);
    this.verifyOtp();
  }

  // --- Step 2: Verify OTP ---
  verifyOtp() {
    const code = this.currentOtpCode();
    if (code.length !== 6) {
      this.errorMessage.set(this.translationService.get('auth.otp.otpRequiredError'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    const emailValue = String(this.forgotForm.get('email')?.value || '').trim().toLowerCase();

    const payload: VerifyPasswordResetOtpRequest = {
      email: emailValue,
      otpCode: code
    };

    this.authService.verifyPasswordResetOtp(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: VerifyPasswordResetOtpResponse) => {
          this.isLoading.set(false);
          this.resetToken = response.reset_token;
          this.step.set('new_password');
          this.passwordForm.reset();
          this.successMessage.set(
            response.message || this.translationService.get('auth.forgotPassword.otpVerifiedSuccess')
          );
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            parseHttpErrorMessage(err, this.translationService.get('auth.otp.verificationFailed'))
          );
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
          this.successMessage.set(
            response.message || this.translationService.get('auth.forgotPassword.resetSuccess')
          );
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            parseHttpErrorMessage(err, this.translationService.get('auth.forgotPassword.updateFailedError'))
          );
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  backToEmail() {
    this.step.set('email');
    this.errorMessage.set('');
    this.successMessage.set('');
  }
}
