import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin } from 'rxjs';
import {
  AlertTriangle,
  BarChart2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Flame,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  RefreshCw,
  Sparkles,
} from 'lucide-angular';
import { AnalyticsService, getLocalMondayDate } from '../services/analytics.service';
import { AnalyticsDailyMetricResponse } from '../models/analytics.model';
import {
  CardComponent,
  CardDescriptionDirective,
  CardHeaderDirective,
  CardTitleDirective,
} from '../../../shared/ui/card/card.component';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';

@Component({
  selector: 'app-analytics-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    LucideAngularModule,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective,
    BadgeDirective,
    ButtonDirective,
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        BarChart2,
        CheckCircle2,
        ChevronLeft,
        ChevronRight,
        Flame,
        RefreshCw,
        Sparkles,
      }),
    },
  ],
  template: `
    <div class="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 class="text-2xl font-bold tracking-tight text-[var(--foreground)]">
            Báo Cáo &amp; Phân Tích Hiệu Suất
          </h1>
          <p class="text-xs sm:text-sm text-[var(--muted-foreground)] mt-0.5">
            Đo lường giờ tập trung, tỷ lệ hoàn thành, bám sát kế hoạch, WRLS và đánh giá tuần
          </p>
        </div>

        <button
          type="button"
          appButton
          variant="outline"
          size="sm"
          [disabled]="analyticsService.isLoading() || analyticsService.isWeeklyLoading()"
          (click)="refreshAll()"
          class="self-start sm:self-auto"
        >
          <lucide-icon name="refresh-cw" [size]="14" aria-hidden="true"></lucide-icon>
          <span>Làm mới</span>
        </button>
      </div>

      <!-- Error Banner -->
      @if (analyticsService.errorState(); as err) {
        <div
          role="alert"
          data-testid="analytics-error-banner"
          class="p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-900 dark:text-red-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="text-xs sm:text-sm flex items-center gap-2">
            <lucide-icon name="alert-triangle" [size]="15" aria-hidden="true"></lucide-icon>
            <span>{{ err.message }}</span>
            @if (err.code) {
              <span class="font-mono px-1.5 py-0.5 rounded bg-red-500/15 text-[11px]">{{ err.code }}</span>
            }
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button type="button" appButton variant="outline" size="sm" (click)="refreshAll()">Thử lại</button>
            <button type="button" appButton variant="ghost" size="sm" (click)="analyticsService.clearError()">Đóng</button>
          </div>
        </div>
      }

      <!-- Loading State -->
      @if (analyticsService.isLoading() && !analyticsService.summary()) {
        <div class="p-10 rounded-2xl border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center gap-3">
          <lucide-icon name="refresh-cw" [size]="22" class="animate-spin text-[var(--primary)]" aria-hidden="true"></lucide-icon>
          <p class="text-sm text-[var(--muted-foreground)]">Đang tổng hợp số liệu phân tích...</p>
        </div>
      } @else {
        <!-- KPI Grid (4 SRS Metrics) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <app-card>
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Tổng giờ tập trung (Focused Hours)</span>
            <div class="text-3xl font-bold text-[var(--foreground)]" data-testid="kpi-total-hours">
              {{ formatNum(summaryData()?.total_focused_hours ?? 0) }} giờ
            </div>
            <p class="text-xs text-[var(--muted-foreground)]">
              Tuần này: {{ formatNum(summaryData()?.weekly_study_hours ?? 0) }} giờ &bull;
              Chuỗi {{ summaryData()?.active_streak_days ?? 0 }} ngày
            </p>
          </app-card>

          <app-card>
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Tỷ lệ hoàn thành công việc</span>
            <div class="text-3xl font-bold text-emerald-700 dark:text-emerald-400 flex flex-wrap items-center gap-2" data-testid="kpi-completion-rate">
              <span>{{ formatNum(summaryData()?.task_completion_rate ?? 0) }}%</span>
              @if ((summaryData()?.task_completion_rate ?? 0) >= 90) {
                <span appBadge variant="success">Đạt KPI (&ge;90%)</span>
              } @else {
                <span appBadge variant="outline">Mục tiêu &ge; 90%</span>
              }
            </div>
            <p class="text-xs text-[var(--muted-foreground)]">
              {{ summaryData()?.completed_tasks_count ?? 0 }} / {{ summaryData()?.total_tasks_count ?? 0 }} nhiệm vụ hoàn thành
            </p>
          </app-card>

          <app-card>
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Tỷ lệ bám sát kế hoạch (Adherence)</span>
            <div class="text-3xl font-bold text-[var(--primary)] flex flex-wrap items-center gap-2" data-testid="kpi-adherence-rate">
              <span>{{ formatNum(summaryData()?.plan_adherence_rate ?? 0) }}%</span>
              @if ((summaryData()?.plan_adherence_rate ?? 0) >= 80) {
                <span appBadge variant="default">Ổn định (&ge;80%)</span>
              } @else {
                <span appBadge variant="outline">Mục tiêu &ge; 80%</span>
              }
            </div>
            <p class="text-xs text-[var(--muted-foreground)]">
              Điểm tập trung TB: {{ formatNum(summaryData()?.average_focus_score ?? 0) }} / 100
            </p>
          </app-card>

          <app-card>
            <span class="text-xs text-[var(--muted-foreground)] font-medium">Phiên phục hồi tuần (WRLS)</span>
            <div class="text-3xl font-bold text-[var(--foreground)] flex flex-wrap items-center gap-2" data-testid="kpi-wrls">
              <span>{{ summaryData()?.weekly_recovered_learning_sessions ?? 0 }}</span>
              <span appBadge variant="outline">WRLS</span>
            </div>
            <p class="text-xs text-[var(--muted-foreground)]">
              Weekly Recovered Learning Sessions trong tuần hiện tại
            </p>
          </app-card>
        </div>

        <!-- 7-Day Breakdown -->
        <app-card>
          <div appCardHeader class="pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 appCardTitle class="text-base font-semibold">Phân bổ học tập 7 ngày</h2>
              <p appCardDescription>
                @if (analyticsService.weekly(); as wk) {
                  Từ {{ wk.week_start }} đến {{ wk.week_end }} &bull;
                  {{ wk.completed_sessions_count }} phiên hoàn thành &bull;
                  WRLS tuần: {{ wk.weekly_recovered_learning_sessions }}
                } @else {
                  Thống kê số phút học và phiên Pomodoro hoàn thành mỗi ngày
                }
              </p>
            </div>

            <div class="flex items-center gap-1.5">
              <button
                type="button"
                appButton
                variant="outline"
                size="sm"
                data-testid="analytics-prev-week-btn"
                (click)="navigateWeek(-1)"
                aria-label="Tuần trước"
              >
                <lucide-icon name="chevron-left" [size]="14" aria-hidden="true"></lucide-icon>
                <span>Trước</span>
              </button>
              @if (analyticsService.weekOffset() !== 0) {
                <button type="button" appButton variant="ghost" size="sm" (click)="resetWeek()">
                  Hiện tại
                </button>
              }
              <button
                type="button"
                appButton
                variant="outline"
                size="sm"
                data-testid="analytics-next-week-btn"
                (click)="navigateWeek(1)"
                aria-label="Tuần sau"
              >
                <span>Sau</span>
                <lucide-icon name="chevron-right" [size]="14" aria-hidden="true"></lucide-icon>
              </button>
            </div>
          </div>

          <div class="space-y-3 pt-2">
            @if (dailyBreakdown().length === 0 || !hasAnyStudiedMinutes()) {
              <div class="py-10 text-center flex flex-col items-center justify-center">
                <div class="w-12 h-12 rounded-2xl bg-[var(--muted)] text-[var(--muted-foreground)] flex items-center justify-center mb-3">
                  <lucide-icon name="bar-chart-2" [size]="24" aria-hidden="true"></lucide-icon>
                </div>
                <h3 class="text-sm font-semibold text-[var(--foreground)] mb-1">
                  Chưa có đủ dữ liệu phân tích trong tuần này
                </h3>
                <p class="text-xs text-[var(--muted-foreground)] max-w-sm mb-4 leading-relaxed">
                  Dữ liệu phân tích sẽ được tổng hợp tự động sau khi bạn hoàn thành các phiên học trong phòng học Pomodoro.
                </p>
                <a routerLink="/workspace" appButton variant="default" size="sm" class="no-underline">
                  Vào phòng học ngay
                </a>
              </div>
            } @else {
              @for (metric of dailyBreakdown(); track metric.date) {
                <div
                  data-testid="daily-metric-row"
                  class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-[var(--border)]"
                  [class]="metric.is_today ? 'bg-[var(--primary)]/5 border-[var(--primary)]/40' : 'bg-[var(--background)]'"
                >
                  <div class="flex items-center gap-2 min-w-[160px]">
                    <span class="font-semibold text-sm text-[var(--foreground)]">{{ metric.day_label }}</span>
                    <span class="text-xs font-mono text-[var(--muted-foreground)]">{{ metric.date }}</span>
                    @if (metric.is_today) {
                      <span appBadge variant="default" class="text-[10px]">Hôm nay</span>
                    }
                  </div>

                  <div class="flex-1 h-2 rounded-full bg-[var(--muted)] overflow-hidden max-w-md">
                    <div
                      class="h-full bg-[var(--primary)] transition-all duration-300"
                      [style.width.%]="barPercentage(metric.minutes_studied)"
                    ></div>
                  </div>

                  <div class="flex items-center gap-3 shrink-0">
                    <span class="text-xs font-medium text-[var(--foreground)]">{{ metric.minutes_studied }} phút học</span>
                    <span appBadge variant="outline">{{ metric.pomodoros_completed }} Pomodoro</span>
                    <span class="text-xs text-[var(--muted-foreground)]">{{ metric.sessions_count }} phiên</span>
                  </div>
                </div>
              }
            }
          </div>
        </app-card>

        <!-- Weekly Review Section -->
        <app-card>
          <div appCardHeader class="pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 appCardTitle class="text-base font-semibold flex items-center gap-2">
                <lucide-icon name="sparkles" [size]="16" class="text-[var(--primary)]" aria-hidden="true"></lucide-icon>
                <span>Đánh Giá Tuần (Weekly Review)</span>
              </h2>
              <p appCardDescription>
                Phân tích điểm mạnh, nút thắt và khuyến nghị cải thiện từ AI Harness
              </p>
            </div>

            @if (analyticsService.roadmaps().length > 0) {
              <div class="flex flex-wrap items-center gap-2">
                <select
                  aria-label="Chọn lộ trình để tạo đánh giá tuần"
                  [ngModel]="selectedRoadmapId()"
                  (ngModelChange)="selectedRoadmapId.set($event)"
                  class="h-8 rounded-lg border border-[var(--input)] bg-[var(--background)] px-2.5 text-xs text-[var(--foreground)]"
                >
                  @for (rm of analyticsService.roadmaps(); track rm.id) {
                    <option [value]="rm.id">{{ rm.title }}</option>
                  }
                </select>
                <button
                  type="button"
                  appButton
                  variant="default"
                  size="sm"
                  data-testid="generate-weekly-review-btn"
                  [disabled]="analyticsService.isGeneratingReview() || !selectedRoadmapId()"
                  (click)="generateReview()"
                >
                  {{ analyticsService.isGeneratingReview() ? 'Đang tạo đánh giá...' : 'Tạo Weekly Review' }}
                </button>
              </div>
            }
          </div>

          @if (analyticsService.reviewError(); as rErr) {
            <div
              role="alert"
              data-testid="weekly-review-error"
              class="p-3 rounded-xl border border-amber-500/40 bg-amber-500/10 text-xs text-amber-900 dark:text-amber-200 flex items-center justify-between gap-2"
            >
              <span>{{ rErr.message }}</span>
              <button type="button" (click)="analyticsService.clearReviewError()" class="underline cursor-pointer">
                Đóng
              </button>
            </div>
          }

          @if (analyticsService.latestReview(); as rev) {
            <div class="space-y-4 pt-2" data-testid="weekly-review-content">
              <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--muted-foreground)]">
                <span>Kỳ đánh giá: <strong class="text-[var(--foreground)]">{{ rev.period_start }} – {{ rev.period_end }}</strong></span>
                <span>Tạo lúc: {{ formatLocalDateTime(rev.generated_at) }}</span>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)] space-y-1.5">
                  <div class="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                    Điểm mạnh nổi bật
                  </div>
                  <p class="text-xs sm:text-sm text-[var(--foreground)] leading-relaxed whitespace-pre-line">
                    {{ rev.strengths_feedback }}
                  </p>
                </div>

                <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)] space-y-1.5">
                  <div class="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                    Nút thắt cần lưu ý
                  </div>
                  <p class="text-xs sm:text-sm text-[var(--foreground)] leading-relaxed whitespace-pre-line">
                    {{ rev.bottlenecks_feedback }}
                  </p>
                </div>

                <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--background)] space-y-1.5">
                  <div class="text-xs font-bold uppercase tracking-wider text-[var(--primary)]">
                    Khuyến nghị hành động
                  </div>
                  <p class="text-xs sm:text-sm text-[var(--foreground)] leading-relaxed whitespace-pre-line">
                    {{ rev.action_recommendations }}
                  </p>
                </div>
              </div>
            </div>
          } @else {
            <div class="py-8 text-center text-xs sm:text-sm text-[var(--muted-foreground)]" data-testid="weekly-review-empty">
              Chưa có bản đánh giá tuần nào. Hãy chọn lộ trình và nhấn "Tạo Weekly Review" sau khi hoàn thành các phiên học trong tuần.
            </div>
          }
        </app-card>
      }
    </div>
  `,
})
export class AnalyticsPageComponent implements OnInit {
  readonly analyticsService = inject(AnalyticsService);
  private readonly destroyRef = inject(DestroyRef);

  readonly selectedRoadmapId = signal<string>('');

  readonly summaryData = computed(() => this.analyticsService.summary());

  readonly dailyBreakdown = computed<AnalyticsDailyMetricResponse[]>(() => {
    const wk = this.analyticsService.weekly();
    if (wk?.daily_breakdown && wk.daily_breakdown.length > 0) {
      return wk.daily_breakdown;
    }
    return this.analyticsService.summary()?.daily_metrics ?? [];
  });

  readonly hasAnyStudiedMinutes = computed(() =>
    this.dailyBreakdown().some((m) => m.minutes_studied > 0 || m.sessions_count > 0)
  );

  readonly maxDailyMinutes = computed(() => {
    const max = Math.max(60, ...this.dailyBreakdown().map((m) => m.minutes_studied));
    return max;
  });

  ngOnInit(): void {
    this.refreshAll();
  }

  refreshAll(): void {
    const weekStart = getLocalMondayDate(this.analyticsService.weekOffset());
    forkJoin([
      this.analyticsService.loadSummary(),
      this.analyticsService.loadWeekly(weekStart),
      this.analyticsService.loadLatestWeeklyReview(),
      this.analyticsService.loadRoadmaps(),
    ])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(([, , , roadmaps]) => {
        if (roadmaps.length > 0 && !this.selectedRoadmapId()) {
          const active = roadmaps.find((r) => r.status === 'ACTIVE') ?? roadmaps[0];
          this.selectedRoadmapId.set(active.id);
        }
      });
  }

  navigateWeek(delta: number): void {
    this.analyticsService.weekOffset.update((v) => v + delta);
    const weekStart = getLocalMondayDate(this.analyticsService.weekOffset());
    this.analyticsService
      .loadWeekly(weekStart)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  resetWeek(): void {
    this.analyticsService.weekOffset.set(0);
    const weekStart = getLocalMondayDate(0);
    this.analyticsService
      .loadWeekly(weekStart)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  generateReview(): void {
    const roadmapId = this.selectedRoadmapId();
    if (!roadmapId) return;

    const wk = this.analyticsService.weekly();
    const periodStart = wk?.week_start ?? getLocalMondayDate(this.analyticsService.weekOffset());
    const periodEnd = wk?.week_end ?? this.addDaysIso(periodStart, 6);

    this.analyticsService
      .generateWeeklyReview({
        roadmap_id: roadmapId,
        period_start: periodStart,
        period_end: periodEnd,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  barPercentage(minutes: number): number {
    return Math.min(100, Math.max(0, Math.round((minutes / this.maxDailyMinutes()) * 100)));
  }

  formatNum(val: number): string {
    return Number.isInteger(val) ? String(val) : val.toFixed(1);
  }

  formatLocalDateTime(iso: string): string {
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return iso;
    return dt.toLocaleString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private addDaysIso(dateIso: string, days: number): string {
    const [y, m, d] = dateIso.split('-').map(Number);
    const dt = new Date(y, (m || 1) - 1, (d || 1) + days);
    const ry = dt.getFullYear();
    const rm = String(dt.getMonth() + 1).padStart(2, '0');
    const rd = String(dt.getDate()).padStart(2, '0');
    return `${ry}-${rm}-${rd}`;
  }
}
