import { Component, ChangeDetectionStrategy, input } from '@angular/core';

@Component({
  selector: 'app-auth-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="w-full max-w-[540px] mx-auto my-auto py-6 sm:py-8 flex flex-col items-center">
      @if (showLogo()) {
        <div class="flex items-center justify-center mb-5">
          <img
            src="assets/logo.svg"
            alt="FocusFlow"
            width="56"
            height="56"
            class="h-14 w-14 object-contain"
          />
        </div>
      }
      <div
        class="w-full bg-white dark:bg-surface-container-lowest rounded-xl border border-neutral-200/80 dark:border-outline-variant/40 p-7 sm:p-11 shadow-[0_4px_24px_rgba(0,0,0,0.03)]"
        [class]="cardClass()"
      >
        <ng-content />
      </div>
    </div>
  `
})
export class AuthCardComponent {
  readonly showLogo = input<boolean>(true);
  readonly cardClass = input<string>('');
}
