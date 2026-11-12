import { Component, OnInit, DestroyRef, inject, ChangeDetectionStrategy, signal, computed } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import { AuthService } from '../../../core/services/auth.service';
import { GoogleSsoService } from '../../../core/services/google-sso.service';
import { TranslationService, LanguageCode } from '../../../core/services/translation.service';
import { TranslatePipe } from '../../../shared/pipes/translate.pipe';
import {
  passwordComplexityValidator,
  evaluatePasswordStrength,
  checkPasswordMinLength,
  checkPasswordLetterCase,
  checkPasswordNumber,
  checkPasswordSpecialChar,
  checkPasswordMismatch
} from '../../../shared/validators/password.validator';
import { strictEmailValidator } from '../../../shared/validators/email.validator';
import {
  GoogleAuthRequest,
  LoginResponse,
  MessageResponse,
  RequestRegisterOtpRequest
} from '../../../models/auth.interface';
import {
  AuthCardComponent,
  AuthHeaderComponent,
  SocialAuthComponent,
  AuthFormFieldComponent,
  PasswordStrengthMeterComponent,
  AuthNoticeBannerComponent
} from '../shared';

@Component({
  selector: 'app-sign-up',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    TranslatePipe,
    AuthCardComponent,
    AuthHeaderComponent,
    SocialAuthComponent,
    AuthFormFieldComponent,
    PasswordStrengthMeterComponent,
    AuthNoticeBannerComponent
  ],
  templateUrl: './sign-up.component.html',
  styleUrl: './sign-up.component.scss'
})
export class SignUpComponent implements OnInit {
  readonly authService = inject(AuthService);
  readonly googleSsoService = inject(GoogleSsoService);
  readonly translationService = inject(TranslationService);
  readonly formBuilder = inject(FormBuilder);
  readonly router = inject(Router);
  readonly destroyRef = inject(DestroyRef);

  readonly signUpForm = this.formBuilder.group({
    fullName: ['', [Validators.required]],
    email: ['', [Validators.required, strictEmailValidator]],
    password: ['', [Validators.required, passwordComplexityValidator]],
    confirmPassword: ['', [Validators.required]],
    termsAccepted: [true, [Validators.requiredTrue]]
  });

  readonly isPasswordVisible = signal<boolean>(false);
  readonly isConfirmPasswordVisible = signal<boolean>(false);
  readonly isLoading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly infoMessage = signal<string>('');
  readonly successMessage = signal<string>('');
  readonly passwordStrength = signal<number>(0);

  readonly strengthLabelKey = computed<string>(() => {
    const strength = this.passwordStrength();
    if (strength <= 1) {
      return 'auth.signUp.weakSecurity';
    }
    if (strength <= 3) {
      return 'auth.signUp.mediumSecurity';
    }
    return 'auth.signUp.strongSecurity';
  });

  ngOnInit() {
    this.errorMessage.set('');
    this.infoMessage.set('');
    this.successMessage.set('');

    this.signUpForm.get('password')?.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (value: string | null) => {
          this.calculatePasswordEntropy(value || '');
        },
        error: (_err: Error) => {},
        complete: () => {}
      });

    this.initGoogleAuth();
  }

  initGoogleAuth() {
    this.googleSsoService.credential$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (credential: string) => {
          this.handleGoogleAuth({ idToken: credential, accessToken: '' });
        },
        error: (_err: Error) => {
          this.errorMessage.set(this.translationService.get('auth.signIn.googleAuthFailed'));
        },
        complete: () => {}
      });

    this.googleSsoService.token$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (token: string) => {
          this.handleGoogleAuth({ idToken: '', accessToken: token });
        },
        error: (_err: Error) => {
          this.errorMessage.set(this.translationService.get('auth.signIn.googleAuthFailed'));
        },
        complete: () => {}
      });

    this.googleSsoService.error$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_errorMsg: string) => {
          this.isLoading.set(false);
          this.errorMessage.set(this.translationService.get('auth.signIn.googleAuthFailed'));
        },
        error: (_err: Error) => {},
        complete: () => {}
      });

    this.googleSsoService.initialize();
  }

  signInWithGoogle() {
    this.errorMessage.set('');
    this.infoMessage.set('');
    this.isLoading.set(true);
    this.googleSsoService.requestGoogleSignIn();
  }

  handleGoogleAuth(request: GoogleAuthRequest) {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.authService.signInWithGoogle(request)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: LoginResponse) => {
          this.isLoading.set(false);
          this.router.navigate(['/dashboard']);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(err, this.translationService.get('auth.signIn.googleAuthFailed')));
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  calculatePasswordEntropy(password: string) {
    this.passwordStrength.set(evaluatePasswordStrength(password).score);
  }

  get hasMinLength(): boolean {
    return checkPasswordMinLength(this.signUpForm.get('password')?.value || '');
  }

  get hasLetterCase(): boolean {
    return checkPasswordLetterCase(this.signUpForm.get('password')?.value || '');
  }

  get hasNumber(): boolean {
    return checkPasswordNumber(this.signUpForm.get('password')?.value || '');
  }

  get hasSpecialChar(): boolean {
    return checkPasswordSpecialChar(this.signUpForm.get('password')?.value || '');
  }

  get isPasswordValid(): boolean {
    return evaluatePasswordStrength(this.signUpForm.get('password')?.value || '').isValid;
  }

  togglePasswordVisibility() {
    this.isPasswordVisible.update(v => !v);
  }

  toggleConfirmPasswordVisibility() {
    this.isConfirmPasswordVisible.update(v => !v);
  }

  get isPasswordMismatch(): boolean {
    return checkPasswordMismatch(
      this.signUpForm.get('password')?.value || '',
      this.signUpForm.get('confirmPassword')?.value || ''
    );
  }

  switchLanguage(lang: LanguageCode) {
    this.translationService.setLanguage(lang);
  }

  requestOtp() {
    if (this.signUpForm.invalid || !this.isPasswordValid) {
      this.signUpForm.markAllAsTouched();
      return;
    }

    if (this.isPasswordMismatch) {
      this.errorMessage.set(this.translationService.get('auth.signUp.passwordMismatchError'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.infoMessage.set('');
    this.successMessage.set('');

    const cleanEmail = String(this.signUpForm.get('email')?.value || '').trim().toLowerCase();
    const cleanFullName = String(this.signUpForm.get('fullName')?.value || '').trim();

    const payload: RequestRegisterOtpRequest = {
      fullName: cleanFullName,
      email: cleanEmail,
      password: String(this.signUpForm.get('password')?.value || '')
    };

    this.authService.requestRegisterOtp(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: MessageResponse) => {
          this.isLoading.set(false);
          sessionStorage.setItem('pending_register_email', cleanEmail);
          this.router.navigate(['/verify-otp'], {
            queryParams: { email: cleanEmail, flow: 'register' }
          });
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(err, this.translationService.get('auth.signUp.registrationFailedError')));
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }
}
