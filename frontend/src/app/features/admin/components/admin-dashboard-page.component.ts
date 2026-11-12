import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import {
  CardComponent,
  CardDescriptionDirective,
  CardHeaderDirective,
  CardTitleDirective
} from '../../../shared/ui/card/card.component';

interface AdminUserQuotaRow {
  readonly id: string;
  readonly email: string;
  readonly role: 'LEARNER' | 'ADMIN';
  readonly tier: 'FREE' | 'PRO';
  readonly status: 'ACTIVE' | 'LOCKED';
  readonly remainingCredits: number;
}

interface AISystemMetricSummary {
  readonly totalRequests24h: number;
  readonly tier123PassRate: number;
  readonly avgLatencyMs: number;
  readonly totalTokensConsumed: number;
}

@Component({
  selector: 'app-admin-dashboard-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ButtonDirective,
    BadgeDirective,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective
  ],
  template: `
    <div class="max-w-6xl mx-auto w-full p-6 space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Cổng Quản Trị Hệ Thống (Admin Portal)</h1>
          <p class="text-sm text-[var(--muted-foreground)]">
            Quản lý tài khoản, hạn ngạch AI (UC-18) và giám sát chất lượng 3-Tier Validation Gate (UC-19)
          </p>
        </div>
        <span appBadge variant="default">RBAC: ADMIN</span>
      </div>

      <!-- UC-19: AI Monitoring & Token Telemetry -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Yêu cầu AI (24h)</span>
            <div class="text-3xl font-bold">{{ aiMetrics().totalRequests24h }}</div>
          </div>
        </app-card>

        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Tỷ lệ vượt Cổng 3-Tier</span>
            <div class="text-3xl font-bold text-emerald-600">{{ aiMetrics().tier123PassRate }}%</div>
          </div>
        </app-card>

        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Độ trễ TTFT trung bình</span>
            <div class="text-3xl font-bold">{{ aiMetrics().avgLatencyMs }} ms</div>
          </div>
        </app-card>

        <app-card>
          <div class="space-y-1">
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Tổng Token tiêu thụ</span>
            <div class="text-3xl font-bold">{{ aiMetrics().totalTokensConsumed }}</div>
          </div>
        </app-card>
      </div>

      <!-- UC-18: User Account & AI Quota Administration -->
      <app-card>
        <div appCardHeader class="pb-2">
          <h2 appCardTitle class="text-base font-semibold">Quản lý Người học & Hạn ngạch AI (UC-18)</h2>
          <p appCardDescription>Khóa/Mở khóa tài khoản và cấp phát lại hạn ngạch AI 2 pha</p>
        </div>

        <div class="space-y-3 pt-2">
          @if (users().length === 0) {
            <div class="p-8 text-center text-xs text-[var(--muted-foreground)] border border-dashed border-[var(--border)] rounded-xl">
              Chưa có người học nào trong danh sách quản trị
            </div>
          } @else {
            @for (user of users(); track user.id) {
              <div class="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--background)]">
                <div class="space-y-0.5">
                  <div class="font-medium text-sm">{{ user.email }}</div>
                  <div class="text-xs text-[var(--muted-foreground)]">
                    Gói: {{ user.tier }} • Hạn ngạch còn lại: {{ user.remainingCredits }} lượt
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span appBadge variant="outline">{{ user.status }}</span>
                  <button appButton variant="secondary" size="sm" type="button" (click)="grantBonusQuota(user.id)">
                    +5 AI Quota
                  </button>
                </div>
              </div>
            }
          }
        </div>
      </app-card>
    </div>
  `
})
export class AdminDashboardPageComponent {
  readonly aiMetrics = signal<AISystemMetricSummary>({
    totalRequests24h: 0,
    tier123PassRate: 0,
    avgLatencyMs: 0,
    totalTokensConsumed: 0
  });

  readonly users = signal<readonly AdminUserQuotaRow[]>([]);

  grantBonusQuota(userId: string): void {
    this.users.update(rows =>
      rows.map(row =>
        row.id === userId ? { ...row, remainingCredits: row.remainingCredits + 5 } : row
      )
    );
  }
}
