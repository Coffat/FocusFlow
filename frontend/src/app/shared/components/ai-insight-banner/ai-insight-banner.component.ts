import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

export type AiInsightBannerType = 'insight' | 'domino_shift' | 'congratulation';

@Component({
  selector: 'app-ai-insight-banner',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './ai-insight-banner.component.html',
  styleUrl: './ai-insight-banner.component.scss',
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
