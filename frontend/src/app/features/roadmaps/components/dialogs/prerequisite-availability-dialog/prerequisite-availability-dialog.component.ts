import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

export type AvailabilitySetupOption = 'hybrid' | 'calendar';

@Component({
  selector: 'app-prerequisite-availability-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './prerequisite-availability-dialog.component.html',
  styleUrl: './prerequisite-availability-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PrerequisiteAvailabilityDialogComponent {
  private readonly router = inject(Router);

  readonly open = input<boolean>(false);
  readonly returnUrl = input<string>('/roadmaps');

  readonly closeDialog = output<void>();
  readonly setupOptionSelected = output<AvailabilitySetupOption>();

  readonly selectedOption = signal<AvailabilitySetupOption>('hybrid');

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.open()) {
      this.closeDialog.emit();
    }
  }

  selectOption(option: AvailabilitySetupOption): void {
    this.selectedOption.set(option);
  }

  onClose(): void {
    this.closeDialog.emit();
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.closeDialog.emit();
    }
  }

  proceed(): void {
    this.navigateWithOption(this.selectedOption());
  }

  directNavigate(option: AvailabilitySetupOption): void {
    this.selectedOption.set(option);
    this.navigateWithOption(option);
  }

  private navigateWithOption(option: AvailabilitySetupOption): void {
    this.setupOptionSelected.emit(option);
    this.closeDialog.emit();

    const queryParams: Record<string, string> = {
      returnUrl: this.returnUrl(),
      autoOpen: 'true',
    };
    if (option === 'calendar') {
      queryParams['focus'] = 'calendar';
    }

    this.router.navigate(['/availability'], { queryParams });
  }
}
