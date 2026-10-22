import { Component, Input, Directive, computed, signal } from '@angular/core';
import { cn } from '../../utils/cn';

@Component({
  selector: 'app-card',
  standalone: true,
  template: `
    <div [class]="classes()">
      <ng-content />
    </div>
  `
})
export class CardComponent {
  private readonly _userClass = signal<string>('');

  @Input('class')
  set userClass(c: string) {
    this._userClass.set(c);
  }

  readonly classes = computed(() => {
    return cn(
      'rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] shadow-xs p-6 space-y-4',
      this._userClass()
    );
  });
}

@Directive({
  selector: '[appCardHeader]',
  standalone: true,
  host: { '[class]': 'classes()' }
})
export class CardHeaderDirective {
  readonly classes = computed(() => 'flex flex-col space-y-1.5');
}

@Directive({
  selector: '[appCardTitle]',
  standalone: true,
  host: { '[class]': 'classes()' }
})
export class CardTitleDirective {
  readonly classes = computed(() => 'font-semibold leading-none tracking-tight text-lg');
}

@Directive({
  selector: '[appCardDescription]',
  standalone: true,
  host: { '[class]': 'classes()' }
})
export class CardDescriptionDirective {
  readonly classes = computed(() => 'text-sm text-[var(--muted-foreground)]');
}
