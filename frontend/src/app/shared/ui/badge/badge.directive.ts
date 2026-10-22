import { Directive, Input, computed, signal } from '@angular/core';
import { cn } from '../../utils/cn';

export type BadgeVariant = 'default' | 'secondary' | 'outline' | 'destructive' | 'success';

@Directive({
  selector: '[appBadge]',
  standalone: true,
  host: { '[class]': 'classes()' }
})
export class BadgeDirective {
  private readonly _variant = signal<BadgeVariant>('default');
  private readonly _userClass = signal<string>('');

  @Input()
  set variant(v: BadgeVariant) {
    this._variant.set(v);
  }

  @Input('class')
  set userClass(c: string) {
    this._userClass.set(c);
  }

  readonly classes = computed(() => {
    const base = 'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-2';

    const variants: Record<BadgeVariant, string> = {
      default: 'border-transparent bg-[var(--primary)] text-[var(--primary-foreground)] shadow-xs',
      secondary: 'border-transparent bg-[var(--secondary)] text-[var(--secondary-foreground)]',
      outline: 'text-[var(--foreground)] border-[var(--border)]',
      destructive: 'border-transparent bg-[var(--destructive)] text-[var(--destructive-foreground)] shadow-xs',
      success: 'border-transparent bg-emerald-600 text-white shadow-xs'
    };

    return cn(base, variants[this._variant()], this._userClass());
  });
}
