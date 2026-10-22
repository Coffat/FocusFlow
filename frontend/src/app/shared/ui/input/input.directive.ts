import { Directive, Input, computed, signal } from '@angular/core';
import { cn } from '../../utils/cn';

@Directive({
  selector: '[appInput]',
  standalone: true,
  host: { '[class]': 'classes()' }
})
export class InputDirective {
  private readonly _userClass = signal<string>('');

  @Input('class')
  set userClass(c: string) {
    this._userClass.set(c);
  }

  readonly classes = computed(() => {
    return cn(
      'flex h-9 w-full rounded-md border border-[var(--input)] bg-transparent px-3 py-1 text-sm shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--muted-foreground)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)] disabled:cursor-not-allowed disabled:opacity-50',
      this._userClass()
    );
  });
}
