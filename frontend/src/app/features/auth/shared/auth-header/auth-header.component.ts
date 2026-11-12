import { Component, ChangeDetectionStrategy, input, computed } from '@angular/core';

@Component({
  selector: 'app-auth-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div [class]="containerClass()">
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

      @if (icon() && iconStyle() === 'circle') {
        <div class="flex items-center gap-3.5 mb-3">
          <div class="w-11 h-11 rounded-full bg-neutral-100 dark:bg-surface-container border border-neutral-200 dark:border-outline-variant flex items-center justify-center text-neutral-800 dark:text-on-surface shrink-0">
            <span class="material-symbols-outlined text-[22px]">{{ icon() }}</span>
          </div>
          <h1 class="font-serif font-medium text-neutral-950 dark:text-on-surface tracking-tight text-2xl sm:text-[32px] sm:leading-[40px]">
            {{ title() }}
          </h1>
        </div>
      } @else {
        <h1 class="font-serif font-medium text-neutral-950 dark:text-on-surface tracking-tight text-2xl sm:text-[32px] sm:leading-[40px] inline-flex items-center justify-center gap-2.5">
          @if (icon() && iconStyle() === 'inline') {
            <span class="material-symbols-outlined text-[28px] text-primary">{{ icon() }}</span>
          }
          <span>{{ title() }}</span>
        </h1>
      }

      @if (subtitle()) {
        <p
          class="font-sans text-neutral-500 dark:text-secondary text-[15px] sm:text-base mt-2.5 mb-7 leading-relaxed"
          [class.max-w-md]="iconStyle() !== 'circle'"
          [class.mx-auto]="iconStyle() !== 'circle'"
        >
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
  readonly iconStyle = input<'circle' | 'inline'>('inline');
  readonly showLogo = input<boolean>(true);

  readonly containerClass = computed(() =>
    this.iconStyle() === 'circle'
      ? 'mb-6'
      : 'space-y-2 mb-6 sm:mb-8 text-center'
  );
}
