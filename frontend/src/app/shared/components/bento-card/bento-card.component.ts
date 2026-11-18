import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-bento-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class]': 'hostClasses()',
  },
  template: `
    <div>
      @if (category()) {
        <div class="inline-flex items-center gap-1.5 text-xs uppercase tracking-wider text-primary font-semibold mb-3 font-sans">
          <span class="w-1.5 h-1.5 rounded-full bg-primary-container"></span>
          {{ category() }}
        </div>
      }
      @if (icon()) {
        <div class="w-9 h-9 rounded-lg bg-surface-container flex items-center justify-center text-primary mb-5 border border-outline-variant/40">
          <span class="material-symbols-outlined text-[20px]">{{ icon() }}</span>
        </div>
      }
      <h3 class="font-serif-headline text-xl text-on-surface mb-2 font-medium">{{ title() }}</h3>
      <p class="text-sm text-on-surface-variant mb-6 font-sans leading-relaxed">{{ description() }}</p>
    </div>
    <ng-content />
  `,
})
export class BentoCardComponent {
  readonly colSpan = input<number | string>(7);
  readonly icon = input<string>('');
  readonly title = input<string>('');
  readonly description = input<string>('');
  readonly category = input<string | undefined>(undefined);

  readonly hostClasses = computed(() => {
    const span = Number(this.colSpan()) || 7;
    const spanClass =
      span === 5
        ? 'md:col-span-5'
        : span === 7
          ? 'md:col-span-7'
          : span === 12
            ? 'md:col-span-12'
            : span === 6
              ? 'md:col-span-6'
              : `md:col-span-${span}`;

    return `${spanClass} hairline-card rounded-xl p-6 md:p-8 flex flex-col justify-between hover:-translate-y-1.5 hover:shadow-[0_16px_36px_-6px_rgba(0,0,0,0.08)] hover:border-primary/50 transition-all duration-250`;
  });
}
