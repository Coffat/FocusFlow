import { Component, ChangeDetectionStrategy, inject, signal } from '@angular/core';
import { DecimalPipe, JsonPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { SettingsService } from '../services/settings.service';
import {
  CardComponent,
  CardHeaderDirective,
  CardTitleDirective,
  CardDescriptionDirective,
} from '../../../shared/ui/card/card.component';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';
import { AvailabilityConfigComponent } from './availability-config/availability-config.component';

@Component({
  selector: 'app-settings-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    DecimalPipe,
    JsonPipe,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective,
    ButtonDirective,
    BadgeDirective,
    AvailabilityConfigComponent,
  ],
  template: `
    <div class="max-w-4xl mx-auto w-full p-6 space-y-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Cài Đặt Hệ Thống</h1>
          <p class="text-sm text-[var(--muted-foreground)]">
            Quản lý tùy chọn cá nhân, hạn ngạch AI và phiên bảo mật
          </p>
        </div>
        <a routerLink="/availability" appButton variant="outline"> ⏰ Quản lý Thời Gian Rảnh </a>
      </div>

      <!-- Quick Link to Availability -->
      <app-card>
        <div
          appCardHeader
          class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        >
          <div>
            <h3 appCardTitle>Thời Gian Rảnh Lai (Hybrid Availability)</h3>
            <p appCardDescription>
              Trang cấu hình quỹ giờ linh hoạt (Mode A) và khung giờ cố định (Mode B) hiện là trang
              độc lập tại
              <code class="px-1.5 py-0.5 rounded bg-[var(--muted)] text-xs font-mono"
                >/availability</code
              >.
            </p>
          </div>
          <a routerLink="/availability" appButton variant="default"> Mở trang Lịch Rảnh &rarr; </a>
        </div>
      </app-card>

      <!-- Availability Management Section (FR-AVAIL v2.0) -->
      <app-availability-config />

      <!-- AI Quota Card -->
      <app-card>
        <div appCardHeader>
          <div class="flex items-center justify-between">
            <div>
              <h3 appCardTitle>Hạn Ngạch Trí Tuệ Nhân Tạo (AI Credits)</h3>
              <p appCardDescription>
                Cơ chế bảo toàn hạn ngạch 2 pha (Reserve/Commit) theo ADR-005
              </p>
            </div>
            <span appBadge variant="outline">
              {{ settingsService.preferences().aiCreditsUsed }} /
              {{ settingsService.preferences().aiCreditsLimit }} Credits
            </span>
          </div>
        </div>

        <div class="w-full bg-[var(--muted)] h-2 rounded-full overflow-hidden my-2">
          <div
            class="bg-[var(--primary)] h-full"
            [style.width.%]="
              (settingsService.preferences().aiCreditsUsed /
                settingsService.preferences().aiCreditsLimit) *
              100
            "
          ></div>
        </div>
        <p class="text-xs text-[var(--muted-foreground)]">
          Mỗi lộ trình học tạo bằng Gemini AI chỉ tính là 1 AI Credit duy nhất.
        </p>
      </app-card>

      <!-- Preferences -->
      <app-card>
        <div appCardHeader class="flex items-start justify-between gap-4">
          <div>
            <h3 appCardTitle>Learner Memory</h3>
            <p appCardDescription>
              Chỉ các nhận định chưa bị từ chối mới được dùng để cá nhân hóa kế hoạch học.
            </p>
          </div>
          <button appButton variant="outline" type="button" (click)="requestReset()">
            Reset Profile
          </button>
        </div>

        @if (resetPending()) {
          <div class="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4" role="alert">
            <p class="text-sm font-medium">Xác nhận đưa Learner Profile về Cold Start?</p>
            <p class="mt-1 text-xs text-[var(--muted-foreground)]">
              Memory và mastery sẽ bị xóa; lịch sử phiên học gốc vẫn được giữ nguyên.
            </p>
            <div class="mt-3 flex gap-2">
              <button appButton type="button" (click)="confirmReset()">Xác nhận Reset</button>
              <button appButton variant="secondary" type="button" (click)="resetPending.set(false)">
                Hủy
              </button>
            </div>
          </div>
        }

        @if (settingsService.memoryLoading()) {
          <p class="py-6 text-sm" aria-live="polite">Đang tải Learner Memory…</p>
        } @else if (settingsService.memoryError(); as error) {
          <div class="py-4" role="alert">
            <p class="text-sm text-red-600">{{ error }}</p>
            <button appButton variant="outline" type="button" class="mt-2" (click)="reloadMemory()">
              Thử lại
            </button>
          </div>
        } @else if (settingsService.learnerMemory().length === 0) {
          <p class="py-6 text-sm text-[var(--muted-foreground)]">
            Chưa có memory. Hệ thống sẽ học từ dữ liệu đủ bằng chứng hoặc thông tin bạn xác nhận rõ.
          </p>
        } @else {
          <div class="space-y-3">
            @for (item of settingsService.learnerMemory(); track item.id) {
              <article class="rounded-lg border border-[var(--border)] p-4" tabindex="0">
                <div class="flex flex-wrap items-center gap-2">
                  <strong class="text-sm">{{ item.memory_key }}</strong>
                  <span appBadge variant="outline">{{ item.category }}</span>
                  <span appBadge variant="outline">{{ item.epistemic_level }}</span>
                  <span class="text-xs text-[var(--muted-foreground)]"
                    >Confidence {{ item.confidence * 100 | number: '1.0-0' }}%</span
                  >
                </div>
                <pre class="mt-2 whitespace-pre-wrap text-xs">{{ item.value | json }}</pre>
                <p class="mt-2 text-xs text-[var(--muted-foreground)]">
                  {{ item.sample_size }} mẫu · {{ item.evidence.length }} bằng chứng
                </p>
                <div class="mt-3 flex gap-2">
                  @if (item.status !== 'CONFIRMED') {
                    <button appButton size="sm" type="button" (click)="confirmMemory(item.id)">
                      Xác nhận
                    </button>
                  }
                  <button
                    appButton
                    size="sm"
                    variant="secondary"
                    type="button"
                    (click)="rejectMemory(item.id)"
                  >
                    Từ chối inference
                  </button>
                </div>
              </article>
            }
          </div>
        }
      </app-card>

      <!-- Preferences -->
      <app-card>
        <div appCardHeader>
          <h3 appCardTitle>Tùy chọn Học Tập</h3>
          <p appCardDescription>Cấu hình mặc định cho phiên Pomodoro và âm thanh chuông báo</p>
        </div>

        <div class="space-y-4 pt-2">
          <div class="flex items-center justify-between py-2 border-b border-[var(--border)]">
            <div>
              <div class="text-sm font-medium">Thời lượng Pomodoro mặc định</div>
              <div class="text-xs text-[var(--muted-foreground)]">
                Thời gian cho mỗi phiên làm việc tập trung
              </div>
            </div>
            <span class="text-sm font-mono font-semibold"
              >{{ settingsService.preferences().defaultPomodoroDuration }} phút</span
            >
          </div>

          <div class="flex items-center justify-between py-2">
            <div>
              <div class="text-sm font-medium">Âm thanh chuông báo</div>
              <div class="text-xs text-[var(--muted-foreground)]">
                Phát chuông khi kết thúc phiên học hoặc giờ nghỉ
              </div>
            </div>
            <span appBadge variant="success">Bật</span>
          </div>
        </div>
      </app-card>
    </div>
  `,
})
export class SettingsPageComponent {
  readonly settingsService = inject(SettingsService);
  readonly resetPending = signal(false);

  constructor() {
    void this.settingsService.loadLearnerMemory();
  }

  reloadMemory(): void {
    void this.settingsService.loadLearnerMemory();
  }

  requestReset(): void {
    this.resetPending.set(true);
  }

  confirmReset(): void {
    void this.settingsService.resetLearnerMemory().then(() => this.resetPending.set(false));
  }

  confirmMemory(id: string): void {
    void this.settingsService.updateMemory(id, { action: 'confirm', value: null });
  }

  rejectMemory(id: string): void {
    void this.settingsService.updateMemory(id, { action: 'reject', value: null });
  }
}
