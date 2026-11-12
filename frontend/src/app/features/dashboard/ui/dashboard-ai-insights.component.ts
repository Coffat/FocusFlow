import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { DashboardAiInsight, DashboardAdaptationStatus } from '../models/dashboard.model';
import { AiInsightBannerComponent } from '../../../shared/components/ai-insight-banner/ai-insight-banner.component';

@Component({
  selector: 'app-dashboard-ai-insights',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AiInsightBannerComponent],
  template: `
    <div class="space-y-4">
      @if (insight(); as ins) {
        <app-ai-insight-banner
          type="insight"
          title="Phân tích Nhận thức & Hiệu suất"
          [message]="ins.summary"
          complianceBadge="SRL Zimmerman"
          [recommendations]="ins.recommendations"
          actionLabel="Tối ưu hóa lịch"
          actionRoute="/schedule"
        />
      }

      @if (adaptation(); as adapt) {
        <app-ai-insight-banner
          type="domino_shift"
          title="Điều phối Thích ứng: Domino Shift"
          [message]="adapt.alertMessage"
          [complianceBadge]="adapt.affectedTasksCount + ' task tự dịch chuyển'"
          [metadata]="{ reason: adapt.rescheduleReason }"
          actionLabel="Xem lịch biểu"
          actionRoute="/schedule"
        />
      }
    </div>
  `,
})
export class DashboardAiInsightsComponent {
  readonly insight = input<DashboardAiInsight | null>(null);
  readonly adaptation = input<DashboardAdaptationStatus | null>(null);
}
