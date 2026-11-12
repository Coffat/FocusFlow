import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Brain,
  Sparkles,
  ArrowRight,
  ArrowLeftRight,
  Trophy,
  Star,
  Check,
} from 'lucide-angular';

export type AiInsightBannerType = 'insight' | 'domino_shift' | 'congratulation';

@Component({
  selector: 'app-ai-insight-banner',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        Brain,
        Sparkles,
        ArrowRight,
        ArrowLeftRight,
        Trophy,
        Star,
        Check,
      }),
    },
  ],
  templateUrl: './ai-insight-banner.component.html',
  styleUrl: './ai-insight-banner.component.scss',
  styles: [':host { display: block; width: 100%; }'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiInsightBannerComponent {
  readonly type = input<AiInsightBannerType>('insight');
  readonly title = input.required<string>();
  readonly message = input.required<string>();
  readonly actionLabel = input<string>();
  readonly actionRoute = input<string>();
  readonly complianceBadge = input<string>();
  readonly recommendations = input<string[]>();
  readonly metadata = input<Record<string, unknown>>();

  readonly actionClick = output<void>();

  onActionClick(): void {
    this.actionClick.emit();
  }
}
