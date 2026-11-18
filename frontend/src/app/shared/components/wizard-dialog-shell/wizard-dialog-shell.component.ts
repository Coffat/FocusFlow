import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

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
  readonly title = input<string>('Tạo lộ trình học tập');
  readonly maxWidthClass = input<string>('max-w-[1040px]');
  readonly errorMessage = input<string | null>(null);

  readonly closeDialog = output<void>();
  readonly stepChange = output<1 | 2 | 3 | 4>();

  readonly steps: readonly WizardStepItem[] = [
    { step: 1, label: '1. Mục tiêu' },
    { step: 2, label: '2. Làm rõ' },
    { step: 3, label: '3. Cột mốc' },
    { step: 4, label: '4. Lịch học' },
  ];

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.open()) {
      this.closeDialog.emit();
    }
  }

  onStepClick(step: 1 | 2 | 3 | 4): void {
    this.stepChange.emit(step);
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
