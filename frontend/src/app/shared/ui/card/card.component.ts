import { Component, ChangeDetectionStrategy, Directive, computed, input } from '@angular/core';
import { cn } from '../../utils/cn';

@Component({
  selector: 'app-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div [class]="classes()">
      <ng-content />
    </div>
  `
})
export class CardComponent {
  readonly userClass = input<string>('', { alias: 'class' });

  readonly classes = computed(() => {
    return cn(
      'rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] shadow-xs p-6 space-y-4',
      this.userClass()
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
