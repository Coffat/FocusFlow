import { Component, OnInit, DestroyRef, inject, ChangeDetectionStrategy, signal } from '@angular/core';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import { strictEmailValidator } from '../../../shared/validators/email.validator';
import { AuthService } from '../../../core/services/auth.service';
import { GoogleSsoService } from '../../../core/services/google-sso.service';
import { TranslationService, LanguageCode } from '../../../core/services/translation.service';
import { TranslatePipe } from '../../../shared/pipes/translate.pipe';
import { GoogleAuthRequest, LoginRequest, LoginResponse } from '../../../models/auth.interface';
import { AuthHeaderComponent } from '../shared/auth-header/auth-header.component';
import { SocialAuthComponent } from '../shared/social-auth/social-auth.component';

@Component({
  selector: 'app-sign-in',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    TranslatePipe,
    AuthHeaderComponent,
    SocialAuthComponent
  ],
  templateUrl: './sign-in.component.html',
  styleUrl: './sign-in.component.scss'
})
export class SignInComponent implements OnInit {
  readonly authService = inject(AuthService);
  readonly googleSsoService = inject(GoogleSsoService);
  readonly translationService = inject(TranslationService);
  readonly formBuilder = inject(FormBuilder);
  readonly router = inject(Router);
  readonly destroyRef = inject(DestroyRef);

  readonly signInForm = this.formBuilder.group({
    email: ['', [Validators.required, strictEmailValidator]],
    password: ['', [Validators.required]],
    rememberMe: [true]
  });

  readonly isPasswordVisible = signal<boolean>(false);
  readonly isLoading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly infoMessage = signal<string>('');

  ngOnInit() {
    this.errorMessage.set('');
    this.infoMessage.set('');
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

  togglePasswordVisibility() {
    this.isPasswordVisible.update(v => !v);
  }

  switchLanguage(lang: LanguageCode) {
    this.translationService.setLanguage(lang);
  }

  signIn() {
    if (this.signInForm.invalid) {
      this.signInForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.infoMessage.set('');

    const credentials: LoginRequest = {
      email: String(this.signInForm.get('email')?.value || '').trim().toLowerCase(),
      password: String(this.signInForm.get('password')?.value || ''),
      rememberMe: Boolean(this.signInForm.get('rememberMe')?.value || false)
    };

    this.authService.signIn(credentials)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: LoginResponse) => {
          this.isLoading.set(false);
          this.router.navigate(['/dashboard']);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(err, this.translationService.get('auth.signIn.authFailedError')));
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }
}
