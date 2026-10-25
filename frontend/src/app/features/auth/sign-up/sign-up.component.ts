import { Component, OnInit, DestroyRef, inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
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
  RequestRegisterOtpRequest,
  VerifyRegisterOtpRequest
} from '../../../models/auth.interface';

@Component({
  selector: 'app-sign-up',
  imports: [ReactiveFormsModule, RouterLink, ButtonModule, CheckboxModule, TranslatePipe],
  templateUrl: './sign-up.component.html',
  styleUrl: './sign-up.component.scss'
})
export class SignUpComponent implements OnInit {
  authService: AuthService;
  googleSsoService: GoogleSsoService;
  translationService: TranslationService;
  formBuilder: FormBuilder;
  router: Router;
  destroyRef: DestroyRef;

  signUpForm: FormGroup;

  isPasswordVisible = false;
  isConfirmPasswordVisible = false;
  isLoading = false;
  errorMessage = '';
  successMessage = '';
  passwordStrength = 0;

  constructor(
    authService: AuthService,
    googleSsoService: GoogleSsoService,
    translationService: TranslationService,
    formBuilder: FormBuilder,
    router: Router
  ) {
    this.authService = authService;
    this.googleSsoService = googleSsoService;
    this.translationService = translationService;
    this.formBuilder = formBuilder;
    this.router = router;
    this.destroyRef = inject(DestroyRef);

    this.signUpForm = this.formBuilder.group({
      fullName: ['', [Validators.required]],
      email: ['', [Validators.required, strictEmailValidator]],
      password: ['', [Validators.required, passwordComplexityValidator]],
      confirmPassword: ['', [Validators.required]],
      termsAccepted: [true, [Validators.requiredTrue]]
    });
  }

  ngOnInit() {
    this.errorMessage = '';
    this.successMessage = '';

    this.signUpForm.get('password')?.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (value: string) => {
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
          this.errorMessage = this.translationService.get('auth.signIn.googleAuthFailed');
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
          this.errorMessage = this.translationService.get('auth.signIn.googleAuthFailed');
        },
        complete: () => {}
      });

    this.googleSsoService.error$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_errorMsg: string) => {
          this.isLoading = false;
          this.errorMessage = this.translationService.get('auth.signIn.googleAuthFailed');
        },
        error: (_err: Error) => {},
        complete: () => {}
      });

    this.googleSsoService.initialize();
  }

  signInWithGoogle() {
    this.errorMessage = '';
    this.isLoading = true;
    this.googleSsoService.requestGoogleSignIn();
  }

  handleGoogleAuth(request: GoogleAuthRequest) {
    this.isLoading = true;
    this.errorMessage = '';

    this.authService.signInWithGoogle(request)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: LoginResponse) => {
          this.isLoading = false;
          this.router.navigate(['/dashboard']);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(err, this.translationService.get('auth.signIn.googleAuthFailed'));
        },
        complete: () => {
          this.isLoading = false;
        }
      });
  }

  calculatePasswordEntropy(password: string) {
    this.passwordStrength = evaluatePasswordStrength(password).score;
  }

  get hasMinLength(): boolean {
    return checkPasswordMinLength(this.signUpForm.get('password')?.value);
  }

  get hasLetterCase(): boolean {
    return checkPasswordLetterCase(this.signUpForm.get('password')?.value);
  }

  get hasNumber(): boolean {
    return checkPasswordNumber(this.signUpForm.get('password')?.value);
  }

  get hasSpecialChar(): boolean {
    return checkPasswordSpecialChar(this.signUpForm.get('password')?.value);
  }

  get isPasswordValid(): boolean {
    return evaluatePasswordStrength(this.signUpForm.get('password')?.value).isValid;
  }

  togglePasswordVisibility() {
    this.isPasswordVisible = !this.isPasswordVisible;
  }

  toggleConfirmPasswordVisibility() {
    this.isConfirmPasswordVisible = !this.isConfirmPasswordVisible;
  }

  get isPasswordMismatch(): boolean {
    return checkPasswordMismatch(
      this.signUpForm.get('password')?.value,
      this.signUpForm.get('confirmPassword')?.value
    );
  }

  switchLanguage(lang: LanguageCode) {
    this.translationService.setLanguage(lang);
  }

  get strengthLabelKey(): string {
    if (this.passwordStrength <= 1) {
      return 'auth.signUp.weakSecurity';
    }
    if (this.passwordStrength <= 3) {
      return 'auth.signUp.mediumSecurity';
    }
    return 'auth.signUp.strongSecurity';
  }

  requestOtp() {
    if (this.signUpForm.invalid || !this.isPasswordValid) {
      this.signUpForm.markAllAsTouched();
      return;
    }

    if (this.isPasswordMismatch) {
      this.errorMessage = this.translationService.get('auth.signUp.passwordMismatchError');
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

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
          this.isLoading = false;
          sessionStorage.setItem('pending_register_email', cleanEmail);
          this.router.navigate(['/verify-otp'], {
            queryParams: { email: cleanEmail, flow: 'register' }
          });
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(err, 'Registration failed. Please check form inputs.');
        },
        complete: () => {
          this.isLoading = false;
        }
      });
  }
}
