import { Directive, computed, input } from '@angular/core';
import { cn } from '../../utils/cn';

export type BadgeVariant = 'default' | 'secondary' | 'outline' | 'destructive' | 'success';

@Directive({
  selector: '[appBadge]',
  standalone: true,
  host: { '[class]': 'classes()' }
})
export class BadgeDirective {
  readonly variant = input<BadgeVariant>('default');
  readonly userClass = input<string>('', { alias: 'class' });

  readonly classes = computed(() => {
    const base = 'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:ring-offset-2';

    const variants: Record<BadgeVariant, string> = {
      default: 'border-transparent bg-[var(--primary)] text-[var(--primary-foreground)] shadow-xs',
      secondary: 'border-transparent bg-[var(--secondary)] text-[var(--secondary-foreground)]',
      outline: 'text-[var(--foreground)] border-[var(--border)]',
      destructive: 'border-transparent bg-[var(--destructive)] text-[var(--destructive-foreground)] shadow-xs',
      success: 'border-transparent bg-emerald-600 text-white shadow-xs'
    };

    return cn(base, variants[this.variant()], this.userClass());
  });
}
