import {
  Component,
  OnInit,
  DestroyRef,
  inject,
  ElementRef,
  viewChildren,
  signal,
  computed,
  ChangeDetectionStrategy,
  NgZone
} from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/services/translation.service';
import { TranslatePipe } from '../../../shared/pipes/translate.pipe';
import { LoginResponse, MessageResponse } from '../../../models/auth.interface';

@Component({
  selector: 'app-otp-validation',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ButtonModule, TranslatePipe],
  templateUrl: './otp-validation.component.html',
  styleUrl: './otp-validation.component.scss'
})
export class OtpValidationComponent implements OnInit {
  readonly authService = inject(AuthService);
  readonly translationService = inject(TranslationService);
  readonly router = inject(Router);
  readonly activatedRoute = inject(ActivatedRoute);
  readonly ngZone = inject(NgZone);
  readonly destroyRef = inject(DestroyRef);

  readonly digitInputs = viewChildren<ElementRef<HTMLInputElement>>('digitInput');

  readonly email = signal<string>('');
  readonly flow = signal<string>('register');
  readonly otpDigits = signal<string[]>(['', '', '', '', '', '']);
  readonly fullOtp = computed<string>(() => this.otpDigits().join(''));
  readonly isAutoFilled = signal<boolean>(false);
  readonly isLoading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly successMessage = signal<string>('');
  readonly cooldownSeconds = signal<number>(60);
  private timerIntervalId: number = 0;

  readonly formattedCooldown = computed<string>(() => {
    const total = this.cooldownSeconds();
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    const minsStr = mins < 10 ? '0' + mins : String(mins);
    const secsStr = secs < 10 ? '0' + secs : String(secs);
    return minsStr + ':' + secsStr;
  });

  ngOnInit() {
    this.errorMessage.set('');
    this.successMessage.set('');

    this.destroyRef.onDestroy(() => {
      if (this.timerIntervalId !== 0) {
        window.clearInterval(this.timerIntervalId);
        this.timerIntervalId = 0;
      }
    });

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

    this.startCooldownTimer(60);
  }

  startCooldownTimer(seconds: number) {
    if (this.timerIntervalId !== 0) {
      window.clearInterval(this.timerIntervalId);
      this.timerIntervalId = 0;
    }

    this.cooldownSeconds.set(seconds);

    this.timerIntervalId = window.setInterval(() => {
      this.ngZone.run(() => {
        const current = this.cooldownSeconds();
        if (current <= 1) {
          this.cooldownSeconds.set(0);
          window.clearInterval(this.timerIntervalId);
          this.timerIntervalId = 0;
        } else {
          this.cooldownSeconds.set(current - 1);
        }
      });
    }, 1000);
  }

  onDigitInput(event: Event, index: number) {
    const target = event.target as HTMLInputElement;
    const sanitized = target.value.replace(/[^0-9]/g, '');
    const char = sanitized.length > 0 ? sanitized.slice(-1) : '';

    const newDigits = [...this.otpDigits()];
    newDigits[index] = char;
    this.otpDigits.set(newDigits);
    target.value = char;

    if (char.length > 0 && index < 5) {
      this.focusInput(index + 1);
    }

    if (this.fullOtp().length === 6) {
      this.errorMessage.set('');
    }
  }

  onDigitKeyDown(event: KeyboardEvent, index: number) {
    if (event.key === 'Backspace') {
      const currentVal = this.otpDigits()[index];
      const newDigits = [...this.otpDigits()];
      if (currentVal.length === 0 && index > 0) {
        newDigits[index - 1] = '';
        this.otpDigits.set(newDigits);
        this.focusInput(index - 1);
      } else {
        newDigits[index] = '';
        this.otpDigits.set(newDigits);
      }
    } else if (event.key === 'ArrowLeft' && index > 0) {
      this.focusInput(index - 1);
    } else if (event.key === 'ArrowRight' && index < 5) {
      this.focusInput(index + 1);
    }
  }

  onDigitPaste(event: ClipboardEvent) {
    event.preventDefault();
    const pastedData = event.clipboardData?.getData('text') || '';
    const digitsOnly = pastedData.replace(/[^0-9]/g, '').slice(0, 6);

    if (digitsOnly.length === 0) {
      return;
    }

    const inputsArray = this.digitInputs();
    const newDigits = [...this.otpDigits()];
    for (let i = 0; i < 6; i++) {
      const d = digitsOnly[i] || '';
      newDigits[i] = d;
      if (inputsArray[i]) {
        inputsArray[i].nativeElement.value = d;
      }
    }

    this.isAutoFilled.set(true);
    this.otpDigits.set(newDigits);

    const targetFocusIndex = Math.min(digitsOnly.length, 5);
    this.focusInput(targetFocusIndex);
  }

  focusInput(index: number) {
    const inputsArray = this.digitInputs();
    if (inputsArray[index]) {
      inputsArray[index].nativeElement.focus();
      inputsArray[index].nativeElement.select();
    }
  }

  verifyOtp() {
    if (this.fullOtp().length !== 6) {
      this.errorMessage.set(this.translationService.get('auth.otp.otpRequiredError') || 'Vui lòng nhập đủ 6 chữ số OTP.');
      return;
    }

    const emailVal = this.email();
    if (!emailVal) {
      this.errorMessage.set('Không xác định được địa chỉ email cần xác thực. Vui lòng quay lại trang Đăng ký.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.authService
      .verifyRegisterOtp({
        email: emailVal.trim().toLowerCase(),
        otpCode: this.fullOtp().trim()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: LoginResponse) => {
          this.isLoading.set(false);
          this.successMessage.set('Xác thực OTP thành công! Đang chuyển hướng vào hệ thống...');
          sessionStorage.removeItem('pending_register_email');
          setTimeout(() => {
            this.router.navigate(['/dashboard']);
          }, 300);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(
            err,
            this.translationService.get('auth.otp.verificationFailed') || 'Xác thực OTP thất bại. Vui lòng thử lại.'
          ));
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
  }

  resendOtp() {
    if (this.cooldownSeconds() > 0 || this.isLoading()) {
      return;
    }

    const emailVal = this.email();
    if (!emailVal) {
      this.errorMessage.set('Email không hợp lệ. Vui lòng quay lại trang Đăng ký.');
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
          this.startCooldownTimer(60);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.errorMessage.set(parseHttpErrorMessage(err, 'Resend request failed. Please try again.'));
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
