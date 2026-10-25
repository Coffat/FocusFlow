import {
  Component,
  OnInit,
  DestroyRef,
  inject,
  ElementRef,
  ViewChildren,
  QueryList,
  signal,
  computed,
  ChangeDetectorRef,
  NgZone
} from '@angular/core';
import { CommonModule } from '@angular/common';
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
  imports: [FormsModule, RouterLink, ButtonModule, TranslatePipe],
  templateUrl: './otp-validation.component.html',
  styleUrl: './otp-validation.component.scss'
})
export class OtpValidationComponent implements OnInit {
  authService: AuthService;
  translationService: TranslationService;
  router: Router;
  activatedRoute: ActivatedRoute;
  cdr: ChangeDetectorRef;
  ngZone: NgZone;
  destroyRef: DestroyRef;

  @ViewChildren('digitInput') digitInputs!: QueryList<ElementRef<HTMLInputElement>>;

  email = '';
  flow = 'register';
  otpDigits: string[] = ['', '', '', '', '', ''];
  fullOtp = '';
  isAutoFilled = false;
  isLoading = false;
  errorMessage = '';
  successMessage = '';
  cooldownSeconds = signal<number>(60);
  timerIntervalId: number = 0;

  formattedCooldown = computed<string>(() => {
    const total = this.cooldownSeconds();
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    const minsStr = mins < 10 ? '0' + mins : String(mins);
    const secsStr = secs < 10 ? '0' + secs : String(secs);
    return minsStr + ':' + secsStr;
  });

  constructor(
    authService: AuthService,
    translationService: TranslationService,
    router: Router,
    activatedRoute: ActivatedRoute,
    cdr: ChangeDetectorRef,
    ngZone: NgZone
  ) {
    this.authService = authService;
    this.translationService = translationService;
    this.router = router;
    this.activatedRoute = activatedRoute;
    this.cdr = cdr;
    this.ngZone = ngZone;
    this.destroyRef = inject(DestroyRef);
  }

  ngOnInit() {
    this.errorMessage = '';
    this.successMessage = '';

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
            this.email = params['email'].trim();
            sessionStorage.setItem('pending_register_email', this.email);
          } else {
            const stored = sessionStorage.getItem('pending_register_email');
            if (stored) {
              this.email = stored.trim();
            }
          }
          if (params['flow'] && params['flow'].length > 0) {
            this.flow = params['flow'];
          }
          this.cdr.markForCheck();
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
    this.cdr.markForCheck();

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
        this.cdr.markForCheck();
      });
    }, 1000);
  }

  onDigitInput(event: Event, index: number) {
    const target = event.target as HTMLInputElement;
    const sanitized = target.value.replace(/[^0-9]/g, '');
    const char = sanitized.length > 0 ? sanitized.slice(-1) : '';

    this.otpDigits[index] = char;
    target.value = char;
    this.fullOtp = this.otpDigits.join('');
    this.cdr.markForCheck();

    if (char.length > 0 && index < 5) {
      this.focusInput(index + 1);
    }

    if (this.fullOtp.length === 6) {
      this.errorMessage = '';
      this.cdr.markForCheck();
    }
  }

  onDigitKeyDown(event: KeyboardEvent, index: number) {
    if (event.key === 'Backspace') {
      const currentVal = this.otpDigits[index];
      if (currentVal.length === 0 && index > 0) {
        this.otpDigits[index - 1] = '';
        this.focusInput(index - 1);
        this.fullOtp = this.otpDigits.join('');
      } else {
        this.otpDigits[index] = '';
        this.fullOtp = this.otpDigits.join('');
      }
      this.cdr.markForCheck();
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

    const inputsArray = this.digitInputs ? this.digitInputs.toArray() : [];
    for (let i = 0; i < 6; i++) {
      const d = digitsOnly[i] || '';
      this.otpDigits[i] = d;
      if (inputsArray[i]) {
        inputsArray[i].nativeElement.value = d;
      }
    }

    this.isAutoFilled = true;
    this.fullOtp = this.otpDigits.join('');
    this.cdr.markForCheck();

    const targetFocusIndex = Math.min(digitsOnly.length, 5);
    this.focusInput(targetFocusIndex);
  }

  focusInput(index: number) {
    const inputsArray = this.digitInputs ? this.digitInputs.toArray() : [];
    if (inputsArray[index]) {
      inputsArray[index].nativeElement.focus();
      inputsArray[index].nativeElement.select();
    }
  }

  verifyOtp() {
    if (this.fullOtp.length !== 6) {
      this.errorMessage = this.translationService.get('auth.otp.otpRequiredError') || 'Vui lòng nhập đủ 6 chữ số OTP.';
      this.cdr.markForCheck();
      return;
    }

    if (!this.email) {
      this.errorMessage = 'Không xác định được địa chỉ email cần xác thực. Vui lòng quay lại trang Đăng ký.';
      this.cdr.markForCheck();
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.markForCheck();

    this.authService
      .verifyRegisterOtp({
        email: this.email.trim().toLowerCase(),
        otpCode: this.fullOtp.trim()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (_response: LoginResponse) => {
          this.isLoading = false;
          this.successMessage = 'Xác thực OTP thành công! Đang chuyển hướng vào hệ thống...';
          sessionStorage.removeItem('pending_register_email');
          this.cdr.markForCheck();
          setTimeout(() => {
            this.router.navigate(['/dashboard']);
          }, 300);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(
            err,
            this.translationService.get('auth.otp.verificationFailed') || 'Xác thực OTP thất bại. Vui lòng thử lại.'
          );
          this.cdr.markForCheck();
        },
        complete: () => {
          this.isLoading = false;
          this.cdr.markForCheck();
        }
      });
  }

  resendOtp() {
    if (this.cooldownSeconds() > 0 || this.isLoading) {
      return;
    }

    if (!this.email) {
      this.errorMessage = 'Email không hợp lệ. Vui lòng quay lại trang Đăng ký.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const resendReq$ =
      this.flow === 'register'
        ? this.authService.resendRegisterOtp({ email: this.email })
        : this.authService.requestPasswordResetOtp({ email: this.email });

    resendReq$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: MessageResponse) => {
          this.isLoading = false;
          this.successMessage =
            response.message || this.translationService.get('auth.otp.codeSentSuccess');
          this.startCooldownTimer(60);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading = false;
          this.errorMessage = parseHttpErrorMessage(err, 'Resend request failed. Please try again.');
        },
        complete: () => {
          this.isLoading = false;
        }
      });
  }

  onUseBackupKey() {
    this.errorMessage = '';
    this.successMessage = this.translationService.get('auth.otp.backupKeyNotice');
  }
}
