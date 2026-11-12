import {
  Component,
  OnInit,
  DestroyRef,
  inject,
  signal,
  ChangeDetectionStrategy
} from '@angular/core';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/services/translation.service';
import { TranslatePipe } from '../../../shared/pipes/translate.pipe';
import { LoginResponse, MessageResponse } from '../../../models/auth.interface';
import {
  AuthCardComponent,
  AuthHeaderComponent,
  OtpInputComponent,
  AuthNoticeBannerComponent
} from '../shared';

@Component({
  selector: 'app-otp-validation',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    TranslatePipe,
    AuthCardComponent,
    AuthHeaderComponent,
    OtpInputComponent,
    AuthNoticeBannerComponent
  ],
  templateUrl: './otp-validation.component.html',
  styleUrl: './otp-validation.component.scss'
})
export class OtpValidationComponent implements OnInit {
  readonly authService = inject(AuthService);
  readonly translationService = inject(TranslationService);
  readonly router = inject(Router);
  readonly activatedRoute = inject(ActivatedRoute);
  readonly destroyRef = inject(DestroyRef);

  readonly email = signal<string>('');
  readonly flow = signal<string>('register');
  readonly currentOtp = signal<string>('');
  readonly isLoading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly successMessage = signal<string>('');

  ngOnInit() {
    this.errorMessage.set('');
    this.successMessage.set('');

    this.activatedRoute.queryParams
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (params: Record<string, string>) => {
          if (params['email'] && params['email'].length > 0) {
            const trimmed = params['email'].trim();
            this.email.set(trimmed);
            sessionStorage.setItem('pending_register_email', trimmed);
          } else {
            const stored = sessionStorage.getItem('pending_register_email');
            if (stored) {
              this.email.set(stored.trim());
            }
          }
          if (params['flow'] && params['flow'].length > 0) {
            this.flow.set(params['flow']);
          }
        },
        error: (_err: Error) => {},
        complete: () => {}
      });
  }

  onOtpChange(code: string) {
    this.currentOtp.set(code);
    if (code.length === 6) {
      this.errorMessage.set('');
    }
  }

  onOtpCompleted(code: string) {
    this.currentOtp.set(code);
    this.verifyOtp();
  }

  verifyOtp() {
    const code = this.currentOtp();
    if (code.length !== 6) {
      this.errorMessage.set(this.translationService.get('auth.otp.otpRequiredError'));
      return;
    }

    const emailVal = this.email();
    if (!emailVal) {
      this.errorMessage.set(this.translationService.get('auth.otp.sessionExpiredError'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.authService
      .verifyRegisterOtp({
        email: emailVal.trim().toLowerCase(),
        otpCode: code.trim()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: LoginResponse) => {
          this.isLoading.set(false);
          this.successMessage.set(this.translationService.get('auth.otp.verifySuccessRedirect'));
          sessionStorage.removeItem('pending_register_email');
          setTimeout(() => {
            this.router.navigate(['/dashboard']);
          }, 350);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(
            err,
            this.translationService.get('auth.otp.verificationFailed')
          ));
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  resendOtp() {
    const emailVal = this.email();
    if (!emailVal) {
      this.errorMessage.set(this.translationService.get('auth.otp.sessionExpiredError'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    const resendReq$ =
      this.flow() === 'register'
        ? this.authService.resendRegisterOtp({ email: emailVal })
        : this.authService.requestPasswordResetOtp({ email: emailVal });

    resendReq$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: MessageResponse) => {
          this.isLoading.set(false);
          this.successMessage.set(
            response.message || this.translationService.get('auth.otp.codeSentSuccess')
          );
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            parseHttpErrorMessage(err, this.translationService.get('auth.otp.resendFailedError'))
          );
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  onUseBackupKey() {
    this.errorMessage.set('');
    this.successMessage.set(this.translationService.get('auth.otp.backupKeyNotice'));
  }
}
