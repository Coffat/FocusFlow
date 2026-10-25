import { Component, OnInit, DestroyRef, inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { HttpErrorResponse } from '@angular/common/http';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import { strictEmailValidator } from '../../../shared/validators/email.validator';
import { AuthService } from '../../../core/services/auth.service';
import { GoogleSsoService } from '../../../core/services/google-sso.service';
import { TranslationService, LanguageCode } from '../../../core/services/translation.service';
import { TranslatePipe } from '../../../shared/pipes/translate.pipe';
import { GoogleAuthRequest, LoginRequest, LoginResponse } from '../../../models/auth.interface';

@Component({
  selector: 'app-sign-in',
  imports: [ReactiveFormsModule, RouterLink, ButtonModule, CheckboxModule, TranslatePipe],
  templateUrl: './sign-in.component.html',
  styleUrl: './sign-in.component.scss'
})
export class SignInComponent implements OnInit {
  authService: AuthService;
  googleSsoService: GoogleSsoService;
  translationService: TranslationService;
  formBuilder: FormBuilder;
  router: Router;
  destroyRef: DestroyRef;

  signInForm: FormGroup;
  isPasswordVisible = false;
  isLoading = false;
  errorMessage = '';

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

    this.signInForm = this.formBuilder.group({
      email: ['', [Validators.required, strictEmailValidator]],
      password: ['', [Validators.required]],
      rememberMe: [true]
    });
  }

  ngOnInit() {
    this.errorMessage = '';
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

  togglePasswordVisibility() {
    this.isPasswordVisible = !this.isPasswordVisible;
  }

  switchLanguage(lang: LanguageCode) {
    this.translationService.setLanguage(lang);
  }

  signIn() {
    if (this.signInForm.invalid) {
      this.signInForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const credentials: LoginRequest = {
      email: String(this.signInForm.get('email')?.value || '').trim().toLowerCase(),
      password: String(this.signInForm.get('password')?.value || ''),
      rememberMe: Boolean(this.signInForm.get('rememberMe')?.value || false)
    };

    this.authService.signIn(credentials)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: LoginResponse) => {
          this.isLoading = false;
          this.router.navigate(['/dashboard']);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(err, 'Authentication failed. Please verify credentials.');
        },
        complete: () => {
          this.isLoading = false;
        }
      });
  }
}
