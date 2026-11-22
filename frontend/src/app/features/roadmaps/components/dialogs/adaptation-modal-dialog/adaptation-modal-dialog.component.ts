import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export type AdaptationStrategyType = 'DOMINO_SHIFT' | 'COMPACT_REBALANCE' | 'BACKLOG_PAUSE';

export interface AdaptationConfirmEvent {
  strategy: AdaptationStrategyType;
  roadmapId?: string | null;
}

@Component({
  selector: 'app-adaptation-modal-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './adaptation-modal-dialog.component.html',
  styleUrl: './adaptation-modal-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdaptationModalDialogComponent {
  readonly open = input<boolean>(false);
  readonly roadmapId = input<string | null>(null);
  readonly roadmapTitle = input<string>('');
  readonly missedSessionsCount = input<number>(0);
  readonly missedMinutes = input<number>(0);
  readonly currentDeadline = input<string>('');
  readonly shiftedDeadline = input<string>('');
  readonly submitting = input<boolean>(false);
  readonly errorMessage = input<string | null>(null);

  readonly closeModal = output<void>();
  readonly confirmAdaptation = output<AdaptationConfirmEvent>();

  readonly selectedStrategy = signal<AdaptationStrategyType>('DOMINO_SHIFT');

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.open() && !this.submitting()) {
      this.closeModal.emit();
    }
  }

  selectStrategy(strategy: AdaptationStrategyType): void {
    if (this.submitting()) {
      return;
    }
    this.selectedStrategy.set(strategy);
  }

  onClose(): void {
    if (this.submitting()) {
      return;
    }
    this.closeModal.emit();
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget && !this.submitting()) {
      this.closeModal.emit();
    }
  }

  onConfirm(): void {
    if (this.submitting()) {
      return;
    }
    this.confirmAdaptation.emit({
      strategy: this.selectedStrategy(),
      roadmapId: this.roadmapId(),
    });
  }
}
