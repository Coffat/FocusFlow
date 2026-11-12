import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Clock,
  Flame,
  Target,
  Timer,
  TrendingUp,
  TrendingDown,
  Minus,
  Route,
  CirclePlay,
  CirclePause,
  CircleCheck,
  Check,
} from 'lucide-angular';

export type KpiTrend = 'up' | 'down' | 'neutral';
export type KpiTone = 'moss' | 'amber' | 'slate' | 'purple' | 'emerald';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        Clock,
        Flame,
        Target,
        Timer,
        TrendingUp,
        TrendingDown,
        Minus,
        Route,
        CirclePlay,
        CirclePause,
        CircleCheck,
        Check,
      }),
    },
  ],
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
        return 'text-amber-600 bg-amber-50 border border-amber-200/60';
      case 'purple':
        return 'text-purple-600 bg-purple-50 border border-purple-200/60';
      case 'slate':
        return 'text-slate-600 bg-slate-50 border border-slate-200/60';
      case 'emerald':
        return 'text-emerald-600 bg-emerald-50 border border-emerald-200/60';
      case 'moss':
      default:
        return 'text-[#246B4A] bg-emerald-50/80 border border-emerald-200/60';
    }
  });

  readonly resolvedIconName = computed<string>(() => {
    const raw = this.icon();
    if (!raw) return 'clock';
    const lower = raw.toLowerCase().trim();
    switch (lower) {
      case 'schedule':
      case 'clock':
        return 'clock';
      case 'local_fire_department':
      case 'flame':
      case 'fire':
        return 'flame';
      case 'track_changes':
      case 'target':
        return 'target';
      case 'timer':
        return 'timer';
      case 'alt_route':
      case 'route':
        return 'route';
      case 'play_circle':
      case 'circle_play':
        return 'circle-play';
      case 'pause_circle':
      case 'circle_pause':
        return 'circle-pause';
      case 'task_alt':
      case 'circle_check':
      case 'check_circle':
        return 'circle-check';
      case 'check':
        return 'check';
      default:
        return lower.replace(/_/g, '-');
    }
  });

  readonly trendIconName = computed<string>(() => {
    switch (this.trend()) {
      case 'up':
        return 'trending-up';
      case 'down':
        return 'trending-down';
      case 'neutral':
      default:
        return 'minus';
    }
  });
}
