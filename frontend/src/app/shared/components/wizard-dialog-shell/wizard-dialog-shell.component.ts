import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  computed,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export interface WizardSseProgressBannerState {
  status: string;
  progressPercent: number;
  message: string;
  stage?: string;
}

export interface WizardStepItem {
  step: 1 | 2 | 3 | 4;
  label: string;
}

@Component({
  selector: 'app-wizard-dialog-shell',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './wizard-dialog-shell.component.html',
  styleUrl: './wizard-dialog-shell.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WizardDialogShellComponent {
  readonly open = input<boolean>(false);
  readonly activeStep = input<1 | 2 | 3 | 4>(1);
  readonly title = input<string>('WIZARD KHỞI TẠO LỘ TRÌNH HỌC TẬP');
  readonly maxWidthClass = input<string>('max-w-[920px]');
  readonly errorMessage = input<string | null>(null);
  readonly sseProgress = input<WizardSseProgressBannerState | null>(null);

  readonly closeDialog = output<void>();
  readonly saveDraftAndExit = output<void>();
  readonly stepChange = output<1 | 2 | 3 | 4>();

  readonly steps: readonly WizardStepItem[] = [
    { step: 1, label: '1. Mục tiêu' },
    { step: 2, label: '2. Phỏng vấn AI' },
    { step: 3, label: '3. Cột mốc' },
    { step: 4, label: '4. Đề xuất Lịch' },
  ];

  readonly isSseActive = computed<boolean>(() => {
    const sse = this.sseProgress();
    if (!sse) return false;
    const status = sse.status?.toUpperCase() ?? '';
    return (
      status === 'PROCESSING' ||
      status === 'CONNECTING' ||
      status === 'STREAMING' ||
      status === 'RESERVED' ||
      status === 'VALIDATING_TIER_1_2_3'
    );
  });

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.open()) {
      this.closeDialog.emit();
    }
  }

  onStepClick(step: 1 | 2 | 3 | 4): void {
    this.stepChange.emit(step);
  }

  onSaveDraft(): void {
    this.saveDraftAndExit.emit();
  }

  onClose(): void {
    this.closeDialog.emit();
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.closeDialog.emit();
    }
  }
}
