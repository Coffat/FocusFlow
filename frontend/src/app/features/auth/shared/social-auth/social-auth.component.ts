import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';

@Component({
  selector: 'app-social-auth',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mb-6">
      <!-- Google Authentication Capsule (Full width) -->
      <button
        class="w-full h-12 px-4 rounded-lg border border-outline-variant bg-surface-container-lowest hover:bg-surface-container-low text-on-surface flex items-center justify-center gap-3 transition-colors duration-150 active:scale-[0.99] group shadow-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        type="button"
        [disabled]="disabled()"
        (click)="googleClick.emit()"
      >
        <svg aria-hidden="true" class="w-4 h-4 shrink-0" viewBox="0 0 24 24">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"></path>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"></path>
        </svg>
        <span class="font-sans text-sm font-medium text-on-surface group-hover:text-primary transition-colors">
          {{ googleButtonText() }}
        </span>
      </button>
    </div>

    <!-- Hairline Divider -->
    <div class="relative flex items-center justify-center my-6">
      <div class="w-full border-t border-outline-variant"></div>
      <span class="absolute bg-surface px-3 font-sans text-xs uppercase tracking-wider text-secondary">
        {{ dividerText() }}
      </span>
    </div>
  `
})
export class SocialAuthComponent {
  readonly googleButtonText = input<string>('Tiếp tục với Google');
  readonly dividerText = input<string>('or continue with email');
  readonly disabled = input<boolean>(false);

  readonly googleClick = output<void>();
}
