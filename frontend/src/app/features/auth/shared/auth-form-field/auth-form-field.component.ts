import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-auth-form-field',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <label
          [for]="forId() || null"
          class="block font-sans text-[13px] sm:text-sm font-medium text-neutral-800 dark:text-on-surface"
        >
          {{ label() }}
        </label>
        @if (linkText() && linkRoute()) {
          <a
            [routerLink]="linkRoute()"
            class="font-sans text-xs text-secondary hover:text-on-surface hover:underline transition-colors"
          >
            {{ linkText() }}
          </a>
        } @else if (hint()) {
          <span class="font-sans text-xs text-secondary">
            {{ hint() }}
          </span>
        }
      </div>

      <div class="relative">
        @if (prefixIcon()) {
          <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-secondary">
            <span class="material-symbols-outlined text-[20px]">{{ prefixIcon() }}</span>
          </div>
        }

        <ng-content />

        @if (showSuffix() || suffixIcon()) {
          <button
            type="button"
            (click)="suffixClick.emit()"
            [attr.aria-label]="suffixAriaLabel() || suffixIcon() || 'toggle action'"
            class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-secondary hover:text-on-surface transition-colors cursor-pointer"
          >
            @if (suffixIcon()) {
              <span class="material-symbols-outlined text-[20px]">{{ suffixIcon() }}</span>
            }
          </button>
        }
      </div>

      @if (errorMessage()) {
        <span class="text-xs text-error font-sans block mt-1.5" role="alert">
          {{ errorMessage() }}
        </span>
      }
    </div>
  `
})
export class AuthFormFieldComponent {
  readonly label = input.required<string>();
  readonly forId = input<string>('');
  readonly hint = input<string>('');
  readonly linkText = input<string>('');
  readonly linkRoute = input<string>('');
  readonly prefixIcon = input<string>('');
  readonly suffixIcon = input<string>('');
  readonly suffixAriaLabel = input<string>('');
  readonly showSuffix = input<boolean>(false);
  readonly errorMessage = input<string>('');

  readonly suffixClick = output<void>();
}
