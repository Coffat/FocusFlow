import {
  Component,
  ChangeDetectionStrategy,
  signal,
  effect,
  output,
  input,
  ElementRef,
  viewChildren,
  OnDestroy,
  OnInit
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslatePipe } from '../../../../shared/pipes/translate.pipe';

@Component({
  selector: 'app-otp-input',
  standalone: true,
  imports: [CommonModule, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="space-y-4">
      <div class="flex items-center justify-between mb-2">
        <label class="font-sans text-xs uppercase tracking-wider text-secondary font-medium">
          {{ label() }}
        </label>
        @if (isAutoFilled()) {
          <span class="font-mono text-[11px] text-primary font-medium">{{ 'auth.otp.autoFillDetected' | translate }}</span>
        }
      </div>

      <!-- 6-digit grid container -->
      <div class="grid grid-cols-6 gap-2 sm:gap-3">
        @for (item of digits(); track $index) {
          <input
            #inputBox
            type="text"
            inputmode="numeric"
            pattern="[0-9]*"
            maxlength="1"
            [value]="item"
            [disabled]="disabled()"
            (input)="onInput($event, $index)"
            (keydown)="onKeyDown($event, $index)"
            (paste)="onPaste($event)"
            [placeholder]="placeholder()"
            class="w-full h-14 text-center font-mono text-2xl font-semibold bg-surface-container-lowest border border-outline-variant rounded-lg text-on-surface focus:border-on-surface focus:ring-1 focus:ring-on-surface focus:bg-white transition-all outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            [class.border-on-surface]="item !== ''"
            [attr.aria-label]="('auth.otp.digitAriaLabel' | translate) + ' ' + ($index + 1)"
          />
        }
      </div>

      <!-- Countdown & Resend action bar -->
      <div class="flex items-center justify-between py-1 font-sans text-xs">
        <span class="text-secondary flex items-center gap-1.5">
          <span class="material-symbols-outlined text-[15px] text-secondary">schedule</span>
          {{ 'auth.otp.didntReceiveCode' | translate }}
        </span>
        <div>
          @if (timerSeconds() > 0) {
            <span class="font-mono text-secondary font-medium">
              {{ 'auth.otp.resendIn' | translate }} {{ formattedTimer() }}
            </span>
          } @else {
            <button
              type="button"
              (click)="onResend()"
              [disabled]="disabled()"
              class="text-primary hover:underline font-semibold cursor-pointer disabled:opacity-50"
            >
              {{ 'auth.otp.resendCodeNow' | translate }}
            </button>
          }
        </div>
      </div>
    </div>
  `
})
export class OtpInputComponent implements OnInit, OnDestroy {
  readonly label = input<string>('TEMPORAL AUTHENTICATION CODE');
  readonly placeholder = input<string>('·');
  readonly disabled = input<boolean>(false);
  readonly initialSeconds = input<number>(60);

  readonly codeChange = output<string>();
  readonly codeCompleted = output<string>();
  readonly resend = output<void>();

  readonly inputBoxes = viewChildren<ElementRef<HTMLInputElement>>('inputBox');

  readonly digits = signal<string[]>(['', '', '', '', '', '']);
  readonly timerSeconds = signal<number>(60);
  readonly isAutoFilled = signal<boolean>(false);

  private timerInterval?: ReturnType<typeof setInterval>;

  ngOnInit() {
    this.timerSeconds.set(this.initialSeconds());
    this.startTimer();
  }

  ngOnDestroy() {
    this.stopTimer();
  }

  startTimer() {
    this.stopTimer();
    this.timerInterval = setInterval(() => {
      const current = this.timerSeconds();
      if (current > 0) {
        this.timerSeconds.set(current - 1);
      } else {
        this.stopTimer();
      }
    }, 1000);
  }

  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = undefined;
    }
  }

  formattedTimer(): string {
    const sec = this.timerSeconds();
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  onInput(event: Event, index: number) {
    const input = event.target as HTMLInputElement;
    const value = input.value.replace(/[^0-9]/g, '');

    const currentDigits = [...this.digits()];
    currentDigits[index] = value ? value[value.length - 1] : '';
    this.digits.set(currentDigits);
    input.value = currentDigits[index];

    const currentCode = currentDigits.join('');
    this.codeChange.emit(currentCode);

    if (value && index < 5) {
      const boxes = this.inputBoxes();
      if (boxes && boxes[index + 1]) {
        boxes[index + 1].nativeElement.focus();
        boxes[index + 1].nativeElement.select();
      }
    }

    if (currentCode.length === 6) {
      this.codeCompleted.emit(currentCode);
    }
  }

  onKeyDown(event: KeyboardEvent, index: number) {
    if (event.key === 'Backspace') {
      const currentDigits = [...this.digits()];
      if (!currentDigits[index] && index > 0) {
        const boxes = this.inputBoxes();
        if (boxes && boxes[index - 1]) {
          boxes[index - 1].nativeElement.focus();
          boxes[index - 1].nativeElement.select();
        }
      }
    } else if (event.key === 'ArrowLeft' && index > 0) {
      const boxes = this.inputBoxes();
      boxes[index - 1]?.nativeElement.focus();
    } else if (event.key === 'ArrowRight' && index < 5) {
      const boxes = this.inputBoxes();
      boxes[index + 1]?.nativeElement.focus();
    }
  }

  onPaste(event: ClipboardEvent) {
    event.preventDefault();
    const pasted = event.clipboardData?.getData('text') || '';
    const cleanNumbers = pasted.replace(/[^0-9]/g, '').slice(0, 6);
    if (!cleanNumbers) return;

    const currentDigits = [...this.digits()];
    for (let i = 0; i < 6; i++) {
      currentDigits[i] = cleanNumbers[i] || '';
    }
    this.digits.set(currentDigits);
    this.isAutoFilled.set(true);

    const fullCode = currentDigits.join('');
    this.codeChange.emit(fullCode);

    const boxes = this.inputBoxes();
    const nextEmptyIndex = currentDigits.findIndex(d => !d);
    const targetIndex = nextEmptyIndex === -1 ? 5 : nextEmptyIndex;
    if (boxes && boxes[targetIndex]) {
      boxes[targetIndex].nativeElement.focus();
    }

    if (fullCode.length === 6) {
      this.codeCompleted.emit(fullCode);
    }
  }

  onResend() {
    this.timerSeconds.set(this.initialSeconds());
    this.startTimer();
    this.resend.emit();
  }

  clear() {
    this.digits.set(['', '', '', '', '', '']);
    this.isAutoFilled.set(false);
    this.codeChange.emit('');
    const boxes = this.inputBoxes();
    boxes[0]?.nativeElement.focus();
  }
}
