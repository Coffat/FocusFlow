import { Directive, Input, computed, signal } from '@angular/core';
import { cn } from '../../utils/cn';

export type ButtonVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'link';
export type ButtonSize = 'default' | 'sm' | 'lg' | 'icon';

@Directive({
  selector: '[appButton]',
  standalone: true,
  host: {
    '[class]': 'classes()',
  }
})
export class ButtonDirective {
  private readonly _variant = signal<ButtonVariant>('default');
  private readonly _size = signal<ButtonSize>('default');
  private readonly _userClass = signal<string>('');

  @Input()
  set variant(v: ButtonVariant) {
    this._variant.set(v);
  }

  @Input()
  set size(s: ButtonSize) {
    this._size.set(s);
  }

  @Input('class')
  set userClass(c: string) {
    this._userClass.set(c);
  }

  readonly classes = computed(() => {
    const base = 'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)] disabled:pointer-events-none disabled:opacity-50 cursor-pointer select-none';

    const variants: Record<ButtonVariant, string> = {
      default: 'bg-[var(--primary)] text-[var(--primary-foreground)] shadow-xs hover:opacity-90',
      secondary: 'bg-[var(--secondary)] text-[var(--secondary-foreground)] shadow-xs hover:opacity-80 border border-[var(--border)]',
      outline: 'border border-[var(--border)] bg-transparent shadow-xs hover:bg-[var(--muted)] hover:text-[var(--foreground)]',
      ghost: 'hover:bg-[var(--muted)] hover:text-[var(--foreground)]',
      destructive: 'bg-[var(--destructive)] text-[var(--destructive-foreground)] shadow-xs hover:opacity-90',
      link: 'text-[var(--primary)] underline-offset-4 hover:underline'
    };

    const sizes: Record<ButtonSize, string> = {
      default: 'h-9 px-4 py-2',
      sm: 'h-8 rounded-md px-3 text-xs',
      lg: 'h-10 rounded-md px-6 text-base',
      icon: 'h-9 w-9'
    };

    return cn(base, variants[this._variant()], sizes[this._size()], this._userClass());
  });
}
