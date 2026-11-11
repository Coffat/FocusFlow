import { Component, ChangeDetectionStrategy, input } from '@angular/core';

@Component({
  selector: 'app-auth-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="space-y-2 mb-6 sm:mb-8 text-center">
      @if (showLogo()) {
        <div class="flex items-center justify-center mb-4">
          <img
            src="assets/logo.svg"
            alt="FocusFlow"
            class="h-12 w-12 object-contain"
          />
        </div>
      }
      <h1 class="font-serif text-2xl sm:text-[32px] sm:leading-[40px] font-normal text-on-surface tracking-tight inline-flex items-center justify-center gap-2">
        @if (icon()) {
          <span class="material-symbols-outlined text-2xl text-primary">{{ icon() }}</span>
        }
        <span>{{ title() }}</span>
      </h1>
      @if (subtitle()) {
        <p class="font-sans text-sm text-secondary leading-relaxed max-w-sm mx-auto">
          {{ subtitle() }}
        </p>
      }
    </div>
  `
})
export class AuthHeaderComponent {
  readonly title = input.required<string>();
  readonly subtitle = input<string>('');
  readonly icon = input<string | null>(null);
  readonly showLogo = input<boolean>(true);
}
