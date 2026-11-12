import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export type KpiTrend = 'up' | 'down' | 'neutral';
export type KpiTone = 'moss' | 'amber' | 'slate' | 'purple' | 'emerald';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './kpi-card.component.html',
  styleUrl: './kpi-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KpiCardComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string | number>();
  readonly target = input<string | number>();
  readonly delta = input<string | number>();
  readonly icon = input<string>();
  readonly trend = input<KpiTrend>('neutral');
  readonly tone = input<KpiTone>('moss');
  readonly progress = input<number>();
  readonly subtitle = input<string>();
  readonly footerText = input<string>();

  readonly toneBarColor = computed<string>(() => {
    switch (this.tone()) {
      case 'amber':
        return '#D97706';
      case 'purple':
        return '#7C3AED';
      case 'slate':
        return '#64748B';
      case 'emerald':
        return '#10B981';
      case 'moss':
      default:
        return '#246B4A';
    }
  });

  readonly toneIconClass = computed<string>(() => {
    switch (this.tone()) {
      case 'amber':
        return 'text-amber-600 bg-amber-50';
      case 'purple':
        return 'text-purple-600 bg-purple-50';
      case 'slate':
        return 'text-slate-600 bg-slate-50';
      case 'emerald':
        return 'text-emerald-600 bg-emerald-50';
      case 'moss':
      default:
        return 'text-[#246B4A] bg-emerald-50/80';
    }
  });

  readonly trendIcon = computed<string>(() => {
    switch (this.trend()) {
      case 'up':
        return 'trending_up';
      case 'down':
        return 'trending_down';
      case 'neutral':
      default:
        return 'remove';
    }
  });
}
