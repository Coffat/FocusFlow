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
import { RoadmapService } from '../../services/roadmap.service';
import { PlanningStep } from '../../models/roadmap.model';
import { ButtonDirective } from '../../../../shared/ui/button/button.directive';
import { BadgeDirective, BadgeVariant } from '../../../../shared/ui/badge/badge.directive';
import {
  CardComponent,
  CardDescriptionDirective,
  CardHeaderDirective,
  CardTitleDirective,
} from '../../../../shared/ui/card/card.component';
import { InputDirective } from '../../../../shared/ui/input/input.directive';

@Component({
  selector: 'app-roadmap-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    ButtonDirective,
    BadgeDirective,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective,
    InputDirective,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="max-w-6xl mx-auto w-full p-4 sm:p-6 space-y-6">
      <!-- Page Header & Portfolio Selector (UC-10) -->
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            @if (selectedDetail(); as detail) {
              <span
                appBadge
                [variant]="getStatusBadgeVariant(detail.status)"
                data-testid="roadmap-status-badge"
              >
                {{ getStatusLabel(detail.status) }}
              </span>
              @if (detail.target_date) {
                <span class="text-xs font-mono text-[var(--muted-foreground)]">
                  Ngày đích: {{ detail.target_date }}
                </span>
              }
            } @else {
              <span appBadge variant="secondary">Chưa chọn lộ trình</span>
            }
          </div>
          <h1 class="text-xl sm:text-2xl font-bold tracking-tight">
            {{ selectedDetail()?.title || roadmapService.currentRoadmap()?.title || 'Không Gian Lập Kế Hoạch Lộ Trình AI (SRL)' }}
          </h1>
          <p class="text-xs sm:text-sm text-[var(--muted-foreground)]">
            {{
              selectedDetail()?.goal?.raw_description ||
                selectedDetail()?.description ||
                roadmapService.currentRoadmap()?.targetGoal ||
                'Phân rã mục tiêu, phê duyệt cột mốc Cấp 1 và kiểm định Đề xuất Lịch học Cấp 2 trước khi áp dụng chính thức.'
            }}
          </p>
        </div>

        <!-- Portfolio Switcher & Actions -->
        <div class="flex flex-wrap items-center gap-2.5">
          @if (roadmapService.roadmaps().length > 0) {
            <div class="flex items-center gap-2">
              <label for="roadmap-portfolio-select" class="sr-only">
                Chọn lộ trình học tập
              </label>
              <select
                id="roadmap-portfolio-select"
                data-testid="roadmap-portfolio-select"
                aria-label="Chọn lộ trình học tập"
                [value]="selectedDetail()?.id ?? ''"
                (change)="onSelectRoadmap($event)"
                class="h-9 rounded-lg border border-[var(--input)] bg-[var(--card)] px-3 py-1 text-xs sm:text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)]"
              >
                @for (rm of roadmapService.roadmaps(); track rm.id) {
                  <option [value]="rm.id">
                    {{ rm.title }} ({{ rm.status }})
                  </option>
                }
              </select>
            </div>
          }

          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            data-testid="toggle-create-roadmap-btn"
            (click)="toggleCreateForm()"
          >
            + Tạo Mục tiêu & Lộ trình mới
          </button>

          @if (selectedDetail(); as detail) {
            @if (detail.status !== 'ARCHIVED') {
              <button
                type="button"
                appButton
                variant="secondary"
                size="sm"
                data-testid="archive-roadmap-btn"
                [disabled]="roadmapService.saving()"
                (click)="onArchiveRoadmap(detail.id)"
              >
                Lưu trữ lộ trình (Archive)
              </button>
            }
          }

          <a routerLink="/workspace" appButton variant="default" size="sm">
            Vào Phiên học
          </a>
        </div>
      </div>

      <!-- Global Live SSE Progress Banner (ADR-005, aria-live="polite") -->
      @if (roadmapService.sseProgress().isStreaming || roadmapService.sseProgress().stage === 'VALIDATING_TIER_1_2_3') {
        <div
          role="status"
          aria-live="polite"
          aria-busy="true"
          data-testid="sse-progress-banner"
          class="p-4 rounded-xl border border-[var(--primary)]/40 bg-[var(--primary)]/5 space-y-2.5"
        >
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="inline-block animate-spin text-sm" aria-hidden="true">⏳</span>
              <span class="text-xs sm:text-sm font-semibold text-[var(--foreground)]">
                Tiến trình AI 2-Stage SSE ({{ roadmapService.sseProgress().stage }})
              </span>
            </div>
            <div class="flex items-center gap-2">
              @if (roadmapService.sseProgress().retryCount > 0) {
                <span
                  appBadge
                  variant="secondary"
                  data-testid="sse-retry-badge"
                  class="font-mono text-[11px]"
                >
                  Tự sửa lỗi (Self-Correction): Vòng #{{ roadmapService.sseProgress().retryCount }}
                </span>
              }
              <span class="font-mono text-xs font-bold text-[var(--primary)]">
                {{ roadmapService.sseProgress().progress }}%
              </span>
            </div>
          </div>

          <p class="text-xs text-[var(--muted-foreground)]" data-testid="sse-progress-message">
            {{ roadmapService.sseProgress().message }}
          </p>

          <div class="w-full h-2 rounded-full bg-[var(--muted)] overflow-hidden">
            <div
              class="h-full bg-[var(--primary)] transition-all duration-300"
              [style.width.%]="roadmapService.sseProgress().progress"
            ></div>
          </div>
        </div>
      }

      <!-- Alert Banners (Error & Success, aria-live="polite") -->
      @if (roadmapService.errorMessage()) {
        <div
          role="alert"
          aria-live="polite"
          data-testid="roadmap-error-alert"
          class="p-3.5 rounded-xl border border-[var(--destructive)]/40 bg-[var(--destructive)]/10 text-xs sm:text-sm text-[var(--destructive)] flex items-center justify-between gap-3"
        >
          <div class="flex items-center gap-2 font-medium">
            <span aria-hidden="true">⚠️</span>
            <span>{{ roadmapService.errorMessage() }}</span>
          </div>
          <button
            type="button"
            (click)="roadmapService.clearMessages()"
            aria-label="Đóng thông báo lỗi"
            class="text-xs underline shrink-0"
          >
            Đóng
          </button>
        </div>
      }

      @if (roadmapService.successMessage()) {
        <div
          role="status"
          aria-live="polite"
          data-testid="roadmap-success-banner"
          class="p-3.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 text-xs sm:text-sm text-emerald-600 flex items-center justify-between gap-3"
        >
          <div class="flex items-center gap-2 font-medium">
            <span aria-hidden="true">✅</span>
            <span>{{ roadmapService.successMessage() }}</span>
          </div>
          <button
            type="button"
            (click)="roadmapService.clearMessages()"
            aria-label="Đóng thông báo thành công"
            class="text-xs underline shrink-0"
          >
            Đóng
          </button>
        </div>
      }

      <!-- 3-Step Planning Stepper Navigation -->
      <div
        role="tablist"
        aria-label="Các bước lập kế hoạch lộ trình học tập"
        class="grid grid-cols-1 sm:grid-cols-3 gap-2 p-1.5 rounded-xl bg-[var(--muted)] border border-[var(--border)]"
      >
        <button
          type="button"
          role="tab"
          data-testid="step-tab-1"
          [attr.aria-selected]="roadmapService.activeStep() === 1"
          (click)="roadmapService.setActiveStep(1)"
          class="px-4 py-2.5 rounded-lg text-left transition-all flex items-center justify-between"
          [ngClass]="
            roadmapService.activeStep() === 1
              ? 'bg-[var(--card)] text-[var(--foreground)] shadow-xs font-bold'
              : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
          "
        >
          <div>
            <div class="text-[11px] uppercase tracking-wider opacity-75">Bước 1 (UC-07)</div>
            <div class="text-xs sm:text-sm">Mục tiêu & Cột mốc</div>
          </div>
          @if (roadmapService.areMilestonesApproved()) {
            <span appBadge variant="success" class="text-[10px]">APPROVED</span>
          }
        </button>

        <button
          type="button"
          role="tab"
          data-testid="step-tab-2"
          [attr.aria-selected]="roadmapService.activeStep() === 2"
          (click)="roadmapService.setActiveStep(2)"
          class="px-4 py-2.5 rounded-lg text-left transition-all flex items-center justify-between"
          [ngClass]="
            roadmapService.activeStep() === 2
              ? 'bg-[var(--card)] text-[var(--foreground)] shadow-xs font-bold'
              : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
          "
        >
          <div>
            <div class="text-[11px] uppercase tracking-wider opacity-75">Bước 2 (UC-08 / UC-12)</div>
            <div class="text-xs sm:text-sm">Đề xuất Lịch học & Kiểm định</div>
          </div>
          @if (roadmapService.currentProposal()) {
            <span appBadge variant="outline" class="text-[10px]">DRAFT</span>
          }
        </button>

        <button
          type="button"
          role="tab"
          data-testid="step-tab-3"
          [attr.aria-selected]="roadmapService.activeStep() === 3"
          (click)="roadmapService.setActiveStep(3)"
          class="px-4 py-2.5 rounded-lg text-left transition-all flex items-center justify-between"
          [ngClass]="
            roadmapService.activeStep() === 3
              ? 'bg-[var(--card)] text-[var(--foreground)] shadow-xs font-bold'
              : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
          "
        >
          <div>
            <div class="text-[11px] uppercase tracking-wider opacity-75">Bước 3 (UC-08 / UC-10)</div>
            <div class="text-xs sm:text-sm">Lịch học Chính thức</div>
          </div>
          @if (selectedDetail()?.official_schedule) {
            <span appBadge variant="success" class="text-[10px]">ACTIVE</span>
          }
        </button>
      </div>

      <!-- =================================================================== -->
      <!-- STEP 1: MỤC TIÊU & CỘT MỐC (UC-07 / FR-PLAN-001)                    -->
      <!-- =================================================================== -->
      @switch (roadmapService.activeStep()) {
        @case (1) {
          <div class="space-y-6" data-testid="step-1-panel">
            <!-- Create New Goal & Roadmap Card -->
            @if (showCreateForm() || !selectedDetail()) {
              <app-card>
                <div appCardHeader>
                  <h2 appCardTitle class="text-base sm:text-lg font-semibold">
                    Khởi Tạo Mục Tiêu Học Tập Mới (Goal & Roadmap — UC-07)
                  </h2>
                  <p appCardDescription class="text-xs">
                    Nhập mục tiêu học tập cụ thể và ngày hoàn thành dự kiến để AI phân rã thành 3–7 cột mốc tuần tự.
                  </p>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div class="sm:col-span-2">
                    <label
                      for="new-goal-title"
                      class="block text-xs font-medium text-[var(--muted-foreground)] mb-1"
                    >
                      Tiêu đề mục tiêu học tập *
                    </label>
                    <input
                      id="new-goal-title"
                      data-testid="new-goal-title-input"
                      type="text"
                      appInput
                      placeholder="VD: Chinh phục FastAPI, Hexagonal Architecture & Angular 21"
                      [ngModel]="newGoalTitle()"
                      (ngModelChange)="newGoalTitle.set($event)"
                    />
                  </div>

                  <div class="sm:col-span-2">
                    <label
                      for="new-goal-description"
                      class="block text-xs font-medium text-[var(--muted-foreground)] mb-1"
                    >
                      Mô tả chi tiết & Trình độ hiện tại
                    </label>
                    <textarea
                      id="new-goal-description"
                      data-testid="new-goal-description-input"
                      rows="3"
                      placeholder="Mô tả kiến thức nền tảng hiện có, tài liệu ưu tiên hoặc mục tiêu đầu ra..."
                      [ngModel]="newGoalDescription()"
                      (ngModelChange)="newGoalDescription.set($event)"
                      class="flex w-full rounded-md border border-[var(--input)] bg-transparent px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)]"
                    ></textarea>
                  </div>

                  <div>
                    <label
                      for="new-goal-start-date"
                      class="block text-xs font-medium text-[var(--muted-foreground)] mb-1"
                    >
                      Ngày bắt đầu (start_date)
                    </label>
                    <input
                      id="new-goal-start-date"
                      data-testid="new-goal-start-date-input"
                      type="date"
                      appInput
                      [ngModel]="newStartDate()"
                      (ngModelChange)="newStartDate.set($event)"
                    />
                  </div>

                  <div>
                    <label
                      for="new-goal-target-date"
                      class="block text-xs font-medium text-[var(--muted-foreground)] mb-1"
                    >
                      Ngày hoàn thành mục tiêu (target_date)
                    </label>
                    <input
                      id="new-goal-target-date"
                      data-testid="new-goal-target-date-input"
                      type="date"
                      appInput
                      [ngModel]="newTargetDate()"
                      (ngModelChange)="newTargetDate.set($event)"
                    />
                  </div>
                </div>

                <div class="flex flex-wrap items-center justify-end gap-2.5 pt-2">
                  @if (selectedDetail()) {
                    <button
                      type="button"
                      appButton
                      variant="ghost"
                      size="sm"
                      (click)="showCreateForm.set(false)"
                    >
                      Hủy
                    </button>
                  }
                  <button
                    type="button"
                    appButton
                    variant="default"
                    data-testid="submit-create-roadmap-btn"
                    [disabled]="!newGoalTitle().trim() || roadmapService.saving()"
                    (click)="onCreateRoadmap()"
                  >
                    Tạo Mục tiêu & Lộ trình
                  </button>
                </div>
              </app-card>
            }

            <!-- Level-1 Milestone Generation & Interactive Editor -->
            @if (selectedDetail(); as detail) {
              <app-card>
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div appCardHeader>
                    <h2 appCardTitle class="text-base sm:text-lg font-semibold">
                      Cột Mốc Học Tập Cấp 1 (Milestones — FR-PLAN-001)
                    </h2>
                    <p appCardDescription class="text-xs">
                      Sinh tự động 3–7 cột mốc bằng AI hoặc tự thêm/chỉnh sửa/sắp xếp trước khi bấm Phê duyệt Cột mốc.
                    </p>
                  </div>

                  <div class="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      appButton
                      variant="default"
                      size="sm"
                      data-testid="generate-milestones-ai-btn"
                      [disabled]="
                        roadmapService.isReadOnlyRoadmap() ||
                        roadmapService.sseProgress().isStreaming ||
                        roadmapService.saving()
                      "
                      (click)="roadmapService.generateMilestonesWithAi(detail.id)"
                    >
                      ✨ Sinh Cột Mốc bằng AI
                    </button>

                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      data-testid="add-milestone-btn"
                      [disabled]="roadmapService.isReadOnlyRoadmap()"
                      (click)="roadmapService.addEditableMilestone()"
                    >
                      + Thêm cột mốc
                    </button>
                  </div>
                </div>

                <!-- Editable Milestones List -->
                @if (roadmapService.editableMilestones().length === 0) {
                  <div
                    data-testid="empty-milestones-state"
                    class="p-6 rounded-xl border border-dashed border-[var(--border)] text-center space-y-2 text-xs sm:text-sm text-[var(--muted-foreground)]"
                  >
                    <p>Chưa có cột mốc nào cho lộ trình này.</p>
                    <p>
                      Hãy nhấn <strong>"Sinh Cột Mốc bằng AI"</strong> hoặc
                      <strong>"+ Thêm cột mốc"</strong> để bắt đầu.
                    </p>
                  </div>
                } @else {
                  <div class="space-y-3 pt-2">
                    @for (ms of roadmapService.editableMilestones(); track $index) {
                      @let idx = $index;
                      @let savedMs = roadmapService.milestones()[idx];
                      <div
                        [attr.data-testid]="'milestone-item-' + idx"
                        class="p-4 rounded-xl border border-[var(--border)] bg-[var(--muted)]/20 space-y-3"
                      >
                        <div class="flex flex-wrap items-center justify-between gap-2">
                          <div class="flex items-center gap-2">
                            <span
                              appBadge
                              variant="outline"
                              class="font-mono text-xs"
                            >
                              Chặng #{{ ms.sequence_order }}
                            </span>
                            @if (savedMs) {
                              <span
                                appBadge
                                [variant]="savedMs.status === 'APPROVED' ? 'success' : 'secondary'"
                                class="text-[11px]"
                              >
                                {{ savedMs.status }}
                              </span>
                            }
                          </div>

                          <div class="flex items-center gap-1.5">
                            <button
                              type="button"
                              appButton
                              variant="outline"
                              size="sm"
                              [attr.data-testid]="'move-milestone-up-' + idx"
                              [attr.aria-label]="'Di chuyển lên cột mốc ' + (idx + 1)"
                              [disabled]="idx === 0 || roadmapService.isReadOnlyRoadmap()"
                              (click)="roadmapService.moveEditableMilestone(idx, 'UP')"
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              appButton
                              variant="outline"
                              size="sm"
                              [attr.data-testid]="'move-milestone-down-' + idx"
                              [attr.aria-label]="'Di chuyển xuống cột mốc ' + (idx + 1)"
                              [disabled]="
                                idx === roadmapService.editableMilestones().length - 1 ||
                                roadmapService.isReadOnlyRoadmap()
                              "
                              (click)="roadmapService.moveEditableMilestone(idx, 'DOWN')"
                            >
                              ↓
                            </button>
                            <button
                              type="button"
                              appButton
                              variant="ghost"
                              size="sm"
                              [attr.data-testid]="'delete-milestone-' + idx"
                              [attr.aria-label]="'Xóa cột mốc ' + (idx + 1)"
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              (click)="roadmapService.removeEditableMilestone(idx)"
                              class="text-[var(--destructive)]"
                            >
                              ✕ Xóa
                            </button>
                          </div>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
                          <div class="sm:col-span-5">
                            <label
                              [attr.for]="'ms-title-' + idx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Tên cột mốc
                            </label>
                            <input
                              [id]="'ms-title-' + idx"
                              [attr.data-testid]="'milestone-title-input-' + idx"
                              type="text"
                              appInput
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="ms.title"
                              (ngModelChange)="roadmapService.updateEditableMilestone(idx, { title: $event })"
                            />
                          </div>

                          <div class="sm:col-span-7">
                            <label
                              [attr.for]="'ms-desc-' + idx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Mô tả mục tiêu chặng
                            </label>
                            <input
                              [id]="'ms-desc-' + idx"
                              [attr.data-testid]="'milestone-desc-input-' + idx"
                              type="text"
                              appInput
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="ms.description"
                              (ngModelChange)="roadmapService.updateEditableMilestone(idx, { description: $event })"
                            />
                          </div>
                        </div>
                      </div>
                    }
                  </div>

                  <!-- Milestone Action Footer -->
                  <div class="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-[var(--border)]">
                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      data-testid="manual-planning-fallback-btn"
                      [disabled]="roadmapService.isReadOnlyRoadmap()"
                      (click)="roadmapService.enableManualPlanningMode()"
                    >
                      🛠️ Lập kế hoạch thủ công (Không tốn Quota AI — UC-09)
                    </button>

                    <div class="flex flex-wrap items-center gap-2.5">
                      <button
                        type="button"
                        appButton
                        variant="secondary"
                        data-testid="save-milestones-btn"
                        [disabled]="
                          roadmapService.isReadOnlyRoadmap() ||
                          roadmapService.saving() ||
                          roadmapService.editableMilestones().length === 0
                        "
                        (click)="roadmapService.saveMilestones(detail.id)"
                      >
                        Lưu chỉnh sửa cột mốc
                      </button>

                      <button
                        type="button"
                        appButton
                        variant="default"
                        data-testid="approve-milestones-btn"
                        [disabled]="
                          roadmapService.isReadOnlyRoadmap() ||
                          roadmapService.saving() ||
                          roadmapService.editableMilestones().length === 0
                        "
                        (click)="roadmapService.approveMilestones(detail.id)"
                      >
                        ✓ Phê duyệt Cột mốc (Approve Milestones)
                      </button>
                    </div>
                  </div>
                }
              </app-card>
            } @else {
              <!-- Legacy Fallback View when no backend roadmap is loaded yet -->
              @if (roadmapService.currentRoadmap(); as legacy) {
                <div class="space-y-3" data-testid="legacy-milestones-preview">
                  <h2 class="text-base font-semibold">Các Chặng Kiến Thức Mẫu (Milestones)</h2>
                  @for (milestone of legacy.milestones; track milestone.id) {
                    <app-card>
                      <div class="flex items-start justify-between gap-3">
                        <div>
                          <span class="text-xs font-mono text-[var(--muted-foreground)]">
                            Chặng {{ milestone.orderIndex }}
                          </span>
                          <h3 class="text-sm font-semibold">{{ milestone.title }}</h3>
                          <p class="text-xs text-[var(--muted-foreground)]">{{ milestone.description }}</p>
                        </div>
                        <span appBadge variant="outline">
                          {{ milestone.completedPomodoros }} / {{ milestone.totalPomodoros }} Pomodoro
                        </span>
                      </div>
                    </app-card>
                  }
                </div>
              }
            }
          </div>
        }

        <!-- =================================================================== -->
        <!-- STEP 2: ĐỀ XUẤT LỊCH HỌC & KIỂM ĐỊNH (UC-08, UC-09, UC-12)          -->
        <!-- =================================================================== -->
        @case (2) {
          <div class="space-y-6" data-testid="step-2-panel">
            @if (selectedDetail(); as detail) {
              <!-- FR-PLAN-001 Gate Warning if Milestones not yet APPROVED -->
              @if (!roadmapService.areMilestonesApproved() && !roadmapService.manualPlanningMode()) {
                <div
                  role="alert"
                  data-testid="unapproved-milestones-guard"
                  class="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 space-y-3"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="space-y-1">
                      <h3 class="text-sm font-bold text-amber-700 dark:text-amber-300">
                        Chốt chặn FR-PLAN-001: Cột mốc Cấp 1 chưa được phê duyệt (APPROVED)
                      </h3>
                      <p class="text-xs text-[var(--muted-foreground)]">
                        Để sinh Đề xuất Lịch học bằng AI (Cấp 2), bạn cần phê duyệt danh sách Cột mốc ở Bước 1 trước, hoặc chuyển sang chế độ Lập kế hoạch thủ công (UC-09).
                      </p>
                    </div>
                  </div>
                  <div class="flex flex-wrap items-center gap-2.5">
                    <button
                      type="button"
                      appButton
                      variant="default"
                      size="sm"
                      (click)="roadmapService.setActiveStep(1)"
                    >
                      ← Quay lại Bước 1 để Phê duyệt Cột mốc
                    </button>
                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      data-testid="guard-manual-plan-btn"
                      (click)="roadmapService.enableManualPlanningMode()"
                    >
                      🛠️ Lập kế hoạch thủ công (Không tốn Quota AI)
                    </button>
                  </div>
                </div>
              }

              <!-- Header Toolbar for Step 2 -->
              <app-card>
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div appCardHeader>
                    <h2 appCardTitle class="text-base sm:text-lg font-semibold">
                      Đề Xuất Lịch Học Chi Tiết (ScheduleProposal — DRAFT)
                    </h2>
                    <p appCardDescription class="text-xs">
                      Mọi đề xuất AI đều ở trạng thái DRAFT (BUSR-02). Bạn có thể chỉnh sửa thời lượng [15–240 phút], ngày/giờ học và kiểm định trước khi Apply.
                    </p>
                  </div>

                  <div class="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      appButton
                      variant="default"
                      size="sm"
                      data-testid="generate-proposal-ai-btn"
                      [disabled]="
                        !roadmapService.areMilestonesApproved() ||
                        roadmapService.isReadOnlyRoadmap() ||
                        roadmapService.sseProgress().isStreaming ||
                        roadmapService.saving()
                      "
                      (click)="roadmapService.generateScheduleProposalWithAi(detail.id)"
                    >
                      ✨ Sinh Đề xuất Lịch học AI (Schedule Proposal)
                    </button>

                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      data-testid="enable-manual-plan-btn"
                      [disabled]="roadmapService.isReadOnlyRoadmap()"
                      (click)="roadmapService.enableManualPlanningMode()"
                    >
                      🛠️ Lập kế hoạch thủ công (Không tốn Quota AI)
                    </button>

                    <button
                      type="button"
                      appButton
                      variant="secondary"
                      size="sm"
                      data-testid="add-proposal-task-btn"
                      [disabled]="roadmapService.isReadOnlyRoadmap()"
                      (click)="roadmapService.addEditableTask()"
                    >
                      + Thêm nhiệm vụ
                    </button>
                  </div>
                </div>

                <!-- Editable Tasks Table / Cards -->
                @if (roadmapService.editableTasks().length === 0) {
                  <div
                    data-testid="empty-proposal-tasks-state"
                    class="p-6 rounded-xl border border-dashed border-[var(--border)] text-center space-y-2 text-xs sm:text-sm text-[var(--muted-foreground)]"
                  >
                    <p>Chưa có bản nháp đề xuất lịch học nào.</p>
                    <p>
                      Nhấn <strong>"Sinh Đề xuất Lịch học AI (Schedule Proposal)"</strong> hoặc
                      <strong>"Lập kế hoạch thủ công"</strong> để tạo danh sách nhiệm vụ.
                    </p>
                  </div>
                } @else {
                  <div class="space-y-3 pt-2">
                    @for (task of roadmapService.editableTasks(); track $index) {
                      @let tIdx = $index;
                      <div
                        [attr.data-testid]="'proposal-task-row-' + tIdx"
                        class="p-4 rounded-xl border border-[var(--border)] bg-[var(--muted)]/20 space-y-3"
                      >
                        <div class="flex items-center justify-between gap-2">
                          <span class="text-xs font-mono font-bold text-[var(--muted-foreground)]">
                            Nhiệm vụ #{{ tIdx + 1 }}
                          </span>
                          <button
                            type="button"
                            appButton
                            variant="ghost"
                            size="sm"
                            [attr.data-testid]="'remove-proposal-task-' + tIdx"
                            [attr.aria-label]="'Xóa nhiệm vụ ' + (tIdx + 1)"
                            [disabled]="roadmapService.isReadOnlyRoadmap()"
                            (click)="roadmapService.removeEditableTask(tIdx)"
                            class="text-[var(--destructive)]"
                          >
                            ✕ Xóa nhiệm vụ
                          </button>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
                          <div class="sm:col-span-5">
                            <label
                              [attr.for]="'task-title-' + tIdx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Tiêu đề nhiệm vụ
                            </label>
                            <input
                              [id]="'task-title-' + tIdx"
                              [attr.data-testid]="'task-title-input-' + tIdx"
                              type="text"
                              appInput
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="task.title"
                              (ngModelChange)="roadmapService.updateEditableTask(tIdx, { title: $event })"
                            />
                          </div>

                          <div class="sm:col-span-4">
                            <label
                              [attr.for]="'task-milestone-' + tIdx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Thuộc Cột mốc
                            </label>
                            <select
                              [id]="'task-milestone-' + tIdx"
                              [attr.data-testid]="'task-milestone-select-' + tIdx"
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="task.milestone_id"
                              (ngModelChange)="roadmapService.updateEditableTask(tIdx, { milestone_id: $event })"
                              class="flex h-9 w-full rounded-md border border-[var(--input)] bg-[var(--card)] px-2.5 py-1 text-xs shadow-xs"
                            >
                              @for (m of roadmapService.milestones(); track m.id) {
                                <option [value]="m.id">
                                  Chặng #{{ m.sequence_order }}: {{ m.title }}
                                </option>
                              }
                            </select>
                          </div>

                          <div class="sm:col-span-3">
                            <label
                              [attr.for]="'task-minutes-' + tIdx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Thời lượng (15–240 phút)
                            </label>
                            <input
                              [id]="'task-minutes-' + tIdx"
                              [attr.data-testid]="'task-minutes-input-' + tIdx"
                              type="number"
                              min="15"
                              max="240"
                              step="5"
                              appInput
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="task.estimated_minutes"
                              (ngModelChange)="
                                roadmapService.updateEditableTask(tIdx, {
                                  estimated_minutes: Number($event)
                                })
                              "
                            />
                          </div>

                          <div class="sm:col-span-4">
                            <label
                              [attr.for]="'task-date-' + tIdx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Ngày học (scheduled_date)
                            </label>
                            <input
                              [id]="'task-date-' + tIdx"
                              [attr.data-testid]="'task-date-input-' + tIdx"
                              type="date"
                              appInput
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="task.scheduled_date"
                              (ngModelChange)="roadmapService.updateEditableTask(tIdx, { scheduled_date: $event })"
                            />
                          </div>

                          <div class="sm:col-span-4">
                            <label
                              [attr.for]="'task-start-' + tIdx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Giờ bắt đầu (scheduled_start)
                            </label>
                            <input
                              [id]="'task-start-' + tIdx"
                              [attr.data-testid]="'task-start-input-' + tIdx"
                              type="time"
                              appInput
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="task.scheduled_start"
                              (ngModelChange)="roadmapService.updateEditableTask(tIdx, { scheduled_start: $event })"
                            />
                          </div>

                          <div class="sm:col-span-4">
                            <label
                              [attr.for]="'task-end-' + tIdx"
                              class="block text-[11px] font-medium text-[var(--muted-foreground)] mb-1"
                            >
                              Giờ kết thúc (scheduled_end)
                            </label>
                            <input
                              [id]="'task-end-' + tIdx"
                              [attr.data-testid]="'task-end-input-' + tIdx"
                              type="time"
                              appInput
                              [disabled]="roadmapService.isReadOnlyRoadmap()"
                              [ngModel]="task.scheduled_end"
                              (ngModelChange)="roadmapService.updateEditableTask(tIdx, { scheduled_end: $event })"
                            />
                          </div>
                        </div>
                      </div>
                    }
                  </div>

                  <!-- Save / Validate Draft Action -->
                  <div class="flex flex-wrap items-center justify-end gap-2.5 pt-3 border-t border-[var(--border)]">
                    <button
                      type="button"
                      appButton
                      variant="secondary"
                      data-testid="validate-and-save-draft-btn"
                      [disabled]="roadmapService.isReadOnlyRoadmap() || roadmapService.saving()"
                      (click)="onSaveAndValidateDraft(detail.id)"
                    >
                      🔍 Kiểm định & Lưu Bản nháp (UC-12)
                    </button>
                  </div>
                }
              </app-card>

              <!-- Validation, Diff Summary & Soft Overflow Gate Panel -->
              @if (roadmapService.currentProposal(); as proposal) {
                <app-card data-testid="validation-and-diff-panel">
                  <div appCardHeader>
                    <h3 appCardTitle class="text-base font-semibold">
                      Bảng Đối Chiếu Thay Đổi (OS-03 Merge) & Cổng Kiểm Định UC-12
                    </h3>
                    <p appCardDescription class="text-xs">
                      Kiểm tra tóm tắt thay đổi lịch học, các vi phạm ràng buộc cứng và xác nhận cảnh báo Tràn mềm trước khi Apply.
                    </p>
                  </div>

                  <!-- OS-03 Diff Summary Metrics -->
                  <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div class="p-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/30">
                      <div class="text-[11px] text-[var(--muted-foreground)]">
                        Phiên đã hoàn thành được giữ nguyên (OS-03)
                      </div>
                      <div
                        data-testid="diff-preserved-count"
                        class="text-lg font-bold font-mono text-emerald-600"
                      >
                        {{ roadmapService.diffSummary().preserved_completed_tasks_count }} nhiệm vụ
                      </div>
                    </div>

                    <div class="p-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/30">
                      <div class="text-[11px] text-[var(--muted-foreground)]">
                        Phiên chưa hoàn thành được thay thế
                      </div>
                      <div
                        data-testid="diff-replaced-count"
                        class="text-lg font-bold font-mono text-[var(--foreground)]"
                      >
                        {{ roadmapService.diffSummary().replaced_tasks_count }} nhiệm vụ
                      </div>
                    </div>

                    <div class="p-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/30">
                      <div class="text-[11px] text-[var(--muted-foreground)]">
                        Tổng số nhiệm vụ mới trong đề xuất
                      </div>
                      <div
                        data-testid="diff-inserted-count"
                        class="text-lg font-bold font-mono text-[var(--primary)]"
                      >
                        {{ roadmapService.diffSummary().inserted_tasks_count }} nhiệm vụ
                      </div>
                    </div>
                  </div>

                  <!-- Hard Violations Alert (Tier 1 / Tier 2) -->
                  @if (roadmapService.proposalViolations().length > 0) {
                    <div
                      role="alert"
                      aria-live="polite"
                      data-testid="hard-violations-panel"
                      class="p-4 rounded-xl border border-[var(--destructive)]/50 bg-[var(--destructive)]/10 space-y-2"
                    >
                      <div class="text-xs sm:text-sm font-bold text-[var(--destructive)]">
                        ❌ Phát hiện {{ roadmapService.proposalViolations().length }} vi phạm ràng buộc cứng (Không thể Apply):
                      </div>
                      <ul class="space-y-1.5 text-xs text-[var(--destructive)] list-disc pl-5">
                        @for (v of roadmapService.proposalViolations(); track $index) {
                          <li [attr.data-testid]="'violation-item-' + $index">
                            <span class="font-mono font-semibold">[{{ v.rule_code }}]</span>
                            @if (v.task_index !== null && v.task_index !== undefined) {
                              <span> (Nhiệm vụ #{{ v.task_index + 1 }}) </span>
                            }
                            <span>— {{ v.suggested_fix }}</span>
                            <span class="opacity-80">
                              (Kỳ vọng: {{ v.expected_bound }}, Thực tế: {{ v.actual_value }})
                            </span>
                          </li>
                        }
                      </ul>
                    </div>
                  }

                  <!-- Soft Overflow Warning & Mandatory Confirmation Checkbox (BUSR-04) -->
                  @if (roadmapService.hasSoftOverflow()) {
                    <div
                      role="alert"
                      aria-live="polite"
                      data-testid="soft-overflow-warning-panel"
                      class="p-4 rounded-xl border border-amber-500/50 bg-amber-500/10 space-y-3"
                    >
                      <div class="space-y-1">
                        <div class="text-xs sm:text-sm font-bold text-amber-700 dark:text-amber-300">
                          ⚠️ Cảnh báo Tràn mềm (Soft Overflow ≤ 30 phút cuối ngày Mode B — BUSR-04)
                        </div>
                        <ul class="space-y-1 text-xs text-[var(--foreground)] list-disc pl-5">
                          @for (w of roadmapService.softOverflowWarnings(); track $index) {
                            <li>
                              <strong>{{ w.task_title }}</strong> ({{ w.scheduled_date }}):
                              tràn <strong>+{{ w.overflow_minutes }} phút</strong> — {{ w.message }}
                            </li>
                          }
                        </ul>
                      </div>

                      <label
                        for="confirm-soft-overflow-checkbox"
                        class="flex items-center gap-2.5 text-xs sm:text-sm font-semibold cursor-pointer select-none"
                      >
                        <input
                          id="confirm-soft-overflow-checkbox"
                          data-testid="confirm-soft-overflow-checkbox"
                          type="checkbox"
                          [checked]="roadmapService.confirmSoftOverflow()"
                          (change)="onToggleSoftOverflow($event)"
                          class="h-4 w-4 rounded border-[var(--input)]"
                        />
                        <span>
                          Tôi xác nhận đồng ý học lố thời gian cho phép (≤ 30 phút) cho các nhiệm vụ cuối ngày trên.
                        </span>
                      </label>
                    </div>
                  }

                  <!-- Explicit Human-in-the-Loop Apply Button (BUSR-02) -->
                  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-3 border-t border-[var(--border)]">
                    <div class="text-xs text-[var(--muted-foreground)]">
                      @if (roadmapService.canApplyProposal()) {
                        <span class="text-emerald-600 font-semibold">
                          ✓ Bản nháp đã đạt chuẩn kiểm định. Sẵn sàng kích hoạt Lịch học Chính thức.
                        </span>
                      } @else if (roadmapService.hasHardViolations()) {
                        <span class="text-[var(--destructive)] font-medium">
                          Vui lòng sửa các vi phạm ràng buộc cứng và bấm "Kiểm định & Lưu Bản nháp" trước khi Apply.
                        </span>
                      } @else if (roadmapService.hasSoftOverflow() && !roadmapService.confirmSoftOverflow()) {
                        <span class="text-amber-600 font-medium">
                          Vui lòng tích chọn xác nhận Cảnh báo Tràn mềm (Soft Overflow) để mở khóa nút Apply.
                        </span>
                      }
                    </div>

                    <button
                      type="button"
                      appButton
                      variant="default"
                      size="lg"
                      data-testid="apply-proposal-btn"
                      [disabled]="!roadmapService.canApplyProposal()"
                      (click)="roadmapService.applyProposal(detail.id, proposal.id)"
                    >
                      🚀 Áp dụng vào Lịch học Chính thức (Apply)
                    </button>
                  </div>
                </app-card>
              }
            }
          </div>
        }

        <!-- =================================================================== -->
        <!-- STEP 3: LỊCH HỌC CHÍNH THỨC (OfficialSchedule — UC-08, UC-10)       -->
        <!-- =================================================================== -->
        @case (3) {
          <div class="space-y-6" data-testid="step-3-panel">
            @if (selectedDetail(); as detail) {
              <!-- Official Schedule Summary Metrics -->
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <app-card>
                  <div class="text-xs text-[var(--muted-foreground)]">Trạng thái Lộ trình</div>
                  <div
                    data-testid="official-roadmap-status"
                    class="text-lg font-bold font-mono text-[var(--foreground)] flex items-center gap-2"
                  >
                    <span>{{ detail.status }}</span>
                    <span appBadge [variant]="getStatusBadgeVariant(detail.status)">
                      {{ getStatusLabel(detail.status) }}
                    </span>
                  </div>
                </app-card>

                <app-card>
                  <div class="text-xs text-[var(--muted-foreground)]">Tổng số phiên học chính thức</div>
                  <div
                    data-testid="official-total-sessions"
                    class="text-lg font-bold font-mono text-[var(--primary)]"
                  >
                    {{ detail.official_schedule?.total_sessions ?? (detail.scheduled_tasks?.length || 0) }} phiên học
                  </div>
                </app-card>

                <app-card>
                  <div class="text-xs text-[var(--muted-foreground)]">Tổng số phút hoạch định</div>
                  <div
                    data-testid="official-total-minutes"
                    class="text-lg font-bold font-mono text-[var(--foreground)]"
                  >
                    {{ detail.official_schedule?.total_planned_minutes ?? totalOfficialMinutes() }} phút
                  </div>
                </app-card>
              </div>

              <!-- Grouped Tasks by Milestone -->
              @if ((detail.scheduled_tasks?.length ?? 0) === 0) {
                <app-card data-testid="empty-official-schedule">
                  <div class="text-center py-6 space-y-2 text-xs sm:text-sm text-[var(--muted-foreground)]">
                    <p>Lộ trình này chưa có Lịch học Chính thức (OfficialSchedule).</p>
                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      (click)="roadmapService.setActiveStep(2)"
                    >
                      ← Sang Bước 2 để Sinh & Áp dụng Đề xuất Lịch học
                    </button>
                  </div>
                </app-card>
              } @else {
                <div class="space-y-4">
                  @for (group of roadmapService.officialTasksGroupedByMilestone(); track group.milestone.id) {
                    <app-card [attr.data-testid]="'official-milestone-group-' + group.milestone.sequence_order">
                      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
                        <div>
                          <span class="text-xs font-mono text-[var(--muted-foreground)]">
                            Chặng #{{ group.milestone.sequence_order }}
                          </span>
                          <h3 class="text-sm sm:text-base font-semibold">
                            {{ group.milestone.title }}
                          </h3>
                        </div>
                        <span appBadge variant="outline" class="font-mono text-xs">
                          {{ group.tasks.length }} nhiệm vụ
                        </span>
                      </div>

                      <div class="space-y-2 pt-2">
                        @for (t of group.tasks; track t.task_id) {
                          <div
                            [attr.data-testid]="'official-task-item-' + t.task_id"
                            class="p-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
                          >
                            <div class="space-y-0.5">
                              <div class="text-xs sm:text-sm font-semibold">{{ t.title }}</div>
                              <div class="text-[11px] font-mono text-[var(--muted-foreground)]">
                                Ngày: {{ t.scheduled_date || 'Chưa xếp lịch' }} · Thời lượng: {{ t.estimated_minutes }} phút
                              </div>
                            </div>

                            <span
                              appBadge
                              [variant]="t.status === 'COMPLETED' ? 'success' : t.status === 'OVERDUE' ? 'destructive' : 'secondary'"
                              class="text-[11px] self-start sm:self-auto"
                            >
                              {{ t.status }}
                            </span>
                          </div>
                        }
                      </div>
                    </app-card>
                  }
                </div>
              }
            }
          </div>
        }
      }
    </div>
  `,
})
export class RoadmapPageComponent implements OnInit {
  readonly roadmapService = inject(RoadmapService);
  private readonly destroyRef = inject(DestroyRef);

  readonly Number = Number;

  // Local Form Signals for Creating a New Goal & Roadmap
  readonly showCreateForm = signal<boolean>(false);
  readonly newGoalTitle = signal<string>('');
  readonly newGoalDescription = signal<string>('');
  readonly newStartDate = signal<string>('2026-11-02');
  readonly newTargetDate = signal<string>('2026-12-30');

  readonly selectedDetail = computed(() => this.roadmapService.selectedRoadmapDetail());

  readonly totalOfficialMinutes = computed<number>(() => {
    const tasks = this.selectedDetail()?.scheduled_tasks ?? [];
    return tasks.reduce((acc, t) => acc + (t.estimated_minutes || 0), 0);
  });

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.roadmapService.closeActiveStream();
    });
  }

  ngOnInit(): void {
    this.roadmapService.loadRoadmaps();
  }

  toggleCreateForm(): void {
    this.showCreateForm.update(v => !v);
  }

  onSelectRoadmap(event: Event): void {
    const id = (event.target as HTMLSelectElement).value;
    if (id) {
      this.roadmapService.loadRoadmapDetail(id);
    }
  }

  onCreateRoadmap(): void {
    const title = this.newGoalTitle().trim();
    if (!title) {
      return;
    }
    this.roadmapService.createRoadmap({
      title,
      description: this.newGoalDescription().trim() || null,
      goal_title: title,
      goal_description: this.newGoalDescription().trim() || null,
      start_date: this.newStartDate() || null,
      target_date: this.newTargetDate() || null,
    });
    this.newGoalTitle.set('');
    this.newGoalDescription.set('');
    this.showCreateForm.set(false);
  }

  onSaveAndValidateDraft(roadmapId: string): void {
    const prop = this.roadmapService.currentProposal();
    if (prop) {
      this.roadmapService.updateProposal(roadmapId, prop.id);
    } else {
      this.roadmapService.saveManualPlan(roadmapId);
    }
  }

  onToggleSoftOverflow(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.roadmapService.setConfirmSoftOverflow(checked);
  }

  onArchiveRoadmap(roadmapId: string): void {
    this.roadmapService.archiveRoadmap(roadmapId);
  }

  getStatusBadgeVariant(status: string): BadgeVariant {
    switch (status) {
      case 'ACTIVE':
      case 'COMPLETED':
        return 'success';
      case 'INITIALIZED':
        return 'default';
      case 'PAUSED':
        return 'outline';
      case 'ARCHIVED':
        return 'secondary';
      default:
        return 'secondary';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'INITIALIZED':
        return 'Khởi tạo (INITIALIZED)';
      case 'ACTIVE':
        return 'Đang thực thi (ACTIVE)';
      case 'PAUSED':
        return 'Tạm dừng (PAUSED)';
      case 'COMPLETED':
        return 'Hoàn thành (COMPLETED)';
      case 'ARCHIVED':
        return 'Đã lưu trữ (ARCHIVED)';
      default:
        return status;
    }
  }
}
