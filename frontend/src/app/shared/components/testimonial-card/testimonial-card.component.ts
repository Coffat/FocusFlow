import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-testimonial-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'hairline-card rounded-xl p-6 flex flex-col justify-between hover:-translate-y-0.5 hover:shadow-md transition-all duration-200',
  },
  template: `
    <p class="text-sm text-on-surface italic font-serif-headline text-lg leading-relaxed mb-6">
      "{{ quote() }}"
    </p>
    <div class="flex items-center gap-3 pt-4 border-t border-outline-variant/30">
      <div
        class="w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs shrink-0"
        [class]="badgeColor()"
      >
        {{ avatarInitials() }}
      </div>
      <div>
        <p class="text-xs font-semibold text-on-surface leading-tight font-sans">{{ authorName() }}</p>
        <p class="text-[11px] text-on-surface-variant font-sans">{{ authorRole() }}</p>
      </div>
    </div>
  `,
})
export class TestimonialCardComponent {
  readonly quote = input.required<string>();
  readonly authorName = input.required<string>();
  readonly authorRole = input.required<string>();
  readonly avatarInitials = input.required<string>();
  readonly badgeColor = input<string>('bg-secondary-container text-on-secondary-container');
}
