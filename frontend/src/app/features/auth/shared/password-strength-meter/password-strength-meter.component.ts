import { Component, ChangeDetectionStrategy, input } from '@angular/core';

@Component({
  selector: 'app-password-strength-meter',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="pt-1.5">
      <div class="flex items-center gap-2 h-2 pt-1">
        @for (i of [1, 2, 3, 4]; track i) {
          <div
            class="flex-1 h-full rounded-full transition-colors duration-200"
            [class.bg-primary]="strength() >= i"
            [class.bg-neutral-200]="strength() < i"
            [class.dark:bg-outline-variant]="strength() < i"
          ></div>
        }
      </div>
      <div class="flex items-center justify-between mt-1.5 text-secondary font-sans text-xs">
        <span>{{ securityLabel() }}</span>
        <span class="text-primary font-medium">{{ strengthText() }}</span>
      </div>
    </div>
  `
})
export class PasswordStrengthMeterComponent {
  readonly strength = input<number>(0);
  readonly securityLabel = input<string>('Mức độ bảo mật');
  readonly strengthText = input<string>('');
}
