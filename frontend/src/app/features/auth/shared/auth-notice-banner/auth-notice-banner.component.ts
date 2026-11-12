import { Component, ChangeDetectionStrategy, input, computed } from '@angular/core';

@Component({
  selector: 'app-auth-notice-banner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (message() || title()) {
      <div [class]="containerClasses()" [attr.role]="ariaRole()">
        <span class="material-symbols-outlined" [class]="iconClasses()">
          {{ iconName() }}
        </span>
        <div class="leading-relaxed">
          @if (title()) {
            @if (type() === 'session-lock') {
              <span class="font-semibold text-on-surface">{{ title() }}: </span>
            } @else {
              <div class="font-semibold mb-0.5">{{ title() }}</div>
            }
          }
          @if (message()) {
            <span>{{ message() }}</span>
          }
          <ng-content />
        </div>
      </div>
    }
  `
})
export class AuthNoticeBannerComponent {
  readonly type = input<'error' | 'info' | 'success' | 'session-lock'>('info');
  readonly message = input<string>('');
  readonly title = input<string>('');

  readonly ariaRole = computed(() => (this.type() === 'error' ? 'alert' : 'status'));

  readonly iconName = computed(() => {
    switch (this.type()) {
      case 'error':
        return 'error';
      case 'success':
        return 'check_circle';
      case 'session-lock':
        return 'shield';
      case 'info':
      default:
        return 'info';
    }
  });

  readonly containerClasses = computed(() => {
    switch (this.type()) {
      case 'error':
        return 'mb-5 p-3.5 rounded-lg bg-[#ffdad6] dark:bg-error-container/30 text-[#93000a] dark:text-error text-xs font-sans flex items-start gap-2.5 border border-[#ba1a1a]/20 dark:border-error/30';
      case 'success':
        return 'mb-5 p-3.5 rounded-lg bg-[#aaf2c8]/30 dark:bg-emerald-950/30 text-[#005234] dark:text-emerald-300 text-xs font-sans flex items-start gap-2.5 border border-[#005234]/20 dark:border-emerald-800/30';
      case 'session-lock':
        return 'p-3.5 rounded-lg border border-outline-variant bg-surface text-secondary text-xs font-sans flex items-start gap-3';
      case 'info':
      default:
        return 'mb-5 p-3.5 rounded-lg bg-[#f0dbff] dark:bg-primary-container/20 text-[#583878] dark:text-on-primary-container text-xs font-sans flex items-start gap-2.5 border border-[#715091]/20 dark:border-outline-variant/30';
    }
  });

  readonly iconClasses = computed(() => {
    switch (this.type()) {
      case 'error':
        return 'text-[18px] text-[#ba1a1a] dark:text-error shrink-0';
      case 'success':
        return 'text-[18px] text-[#005234] dark:text-emerald-400 shrink-0';
      case 'session-lock':
        return 'text-base text-primary mt-0.5 shrink-0';
      case 'info':
      default:
        return 'text-[18px] text-[#583878] dark:text-primary shrink-0';
    }
  });
}
