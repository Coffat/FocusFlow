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
  BookOpen,
  Calendar,
  Check,
  Clock,
  LUCIDE_ICONS,
  ListTodo,
  Lock,
  LucideAngularModule,
  LucideIconProvider,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Trash2,
  X,
} from 'lucide-angular';
import { TaskService } from '../services/task.service';
import { TaskFilterTab, TaskResponse } from '../models/task.model';
import { evaluateTakeawayCheck } from '../../../core/services/workspace-session.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { BadgeDirective } from '../../../shared/ui/badge/badge.directive';

function toLocalIsoDateTime(dateStr: string, timeStr: string): string | null {
  if (!dateStr || !timeStr) return null;
  const candidate = new Date(`${dateStr}T${timeStr}:00`);
  if (Number.isNaN(candidate.getTime())) return null;
  return candidate.toISOString();
}

@Component({
  selector: 'app-tasks-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    LucideAngularModule,
    ButtonDirective,
    BadgeDirective,
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        BookOpen,
        Calendar,
        Check,
        Clock,
        ListTodo,
        Lock,
        Play,
        Plus,
        RefreshCw,
        RotateCcw,
        Trash2,
        X,
      }),
    },
  ],
  host: {
    '(document:keydown.escape)': 'onEscape()',
  },
  template: `
    <div class="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight text-[var(--foreground)]">
            Hàng Đợi Công Việc (Task Queue)
          </h1>
          <p class="text-xs sm:text-sm text-[var(--muted-foreground)] mt-0.5">
            Quản lý nhiệm vụ học tập, hàng đợi phục hồi Backlog và xử lý cảnh báo đình trệ
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            appButton
            variant="outline"
            size="sm"
            [disabled]="taskService.isLoading()"
            (click)="refreshAll()"
          >
            <lucide-icon name="refresh-cw" [size]="14" aria-hidden="true"></lucide-icon>
            <span>Làm mới</span>
          </button>

          <button
            type="button"
            appButton
            variant="default"
            size="sm"
            data-testid="open-create-task-btn"
            (click)="openCreateModal()"
          >
            <lucide-icon name="plus" [size]="14" aria-hidden="true"></lucide-icon>
            <span>+ Thêm việc mới</span>
          </button>
        </div>
      </div>

      <!-- Error Banner -->
      @if (pageError(); as err) {
        <div
          role="alert"
          data-testid="tasks-error-banner"
          class="p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-900 dark:text-red-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div class="space-y-0.5 text-xs sm:text-sm">
            <div class="font-bold flex items-center gap-1.5">
              <lucide-icon name="alert-triangle" [size]="14" aria-hidden="true"></lucide-icon>
              <span>{{ err.message }}</span>
              @if (err.code) {
                <span class="font-mono px-1.5 py-0.5 rounded bg-red-500/15 text-[11px]">{{ err.code }}</span>
              }
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button type="button" appButton variant="outline" size="sm" (click)="refreshAll()">Thử lại</button>
            <button type="button" appButton variant="ghost" size="sm" (click)="taskService.clearError()">Đóng</button>
          </div>
        </div>
      }

      <!-- Filter Tabs & Roadmap Filter -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div class="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Bộ lọc nhiệm vụ">
          @for (tab of filterTabs; track tab.key) {
            <button
              type="button"
              role="tab"
              [attr.aria-selected]="activeTab() === tab.key"
              [attr.data-testid]="'tab-' + tab.key.toLowerCase()"
              (click)="selectTab(tab.key)"
              class="px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-colors cursor-pointer"
              [class]="activeTab() === tab.key
                ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                : 'bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:bg-[var(--muted)]'"
            >
              {{ tab.label }} ({{ tabCount(tab.key) }})
            </button>
          }
        </div>

        @if (taskService.roadmaps().length > 0) {
          <div class="flex items-center gap-2">
            <label for="roadmap-filter-select" class="text-xs text-[var(--muted-foreground)] shrink-0">
              Lộ trình:
            </label>
            <select
              id="roadmap-filter-select"
              [ngModel]="selectedRoadmapFilter()"
              (ngModelChange)="onRoadmapFilterChange($event)"
              class="h-8 rounded-lg border border-[var(--input)] bg-[var(--card)] px-2.5 text-xs text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="">Tất cả lộ trình</option>
              @for (rm of taskService.roadmaps(); track rm.id) {
                <option [value]="rm.id">{{ rm.title }}</option>
              }
            </select>
          </div>
        }
      </div>

      <!-- Loading State -->
      @if (taskService.isLoading() && taskService.tasks().length === 0) {
        <div class="p-10 rounded-2xl border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center gap-3 text-center">
          <lucide-icon name="refresh-cw" [size]="22" class="animate-spin text-[var(--primary)]" aria-hidden="true"></lucide-icon>
          <p class="text-sm text-[var(--muted-foreground)]">Đang tải danh sách nhiệm vụ...</p>
        </div>
      } @else {
        <!-- Task List -->
        <div class="space-y-3">
          @if (filteredTasks().length === 0) {
            <div class="p-10 sm:p-12 text-center flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--card)]">
              <div class="w-12 h-12 rounded-2xl bg-[var(--muted)] text-[var(--muted-foreground)] flex items-center justify-center mb-3">
                <lucide-icon name="list-todo" [size]="24" aria-hidden="true"></lucide-icon>
              </div>
              <h2 class="text-base font-semibold text-[var(--foreground)] mb-1">
                Hàng đợi nhiệm vụ đang trống
              </h2>
              <p class="text-xs sm:text-sm text-[var(--muted-foreground)] max-w-md mb-5 leading-relaxed">
                @if (activeTab() === 'BACKLOG') {
                  Không có nhiệm vụ nào đang chờ trong Hàng đợi Phục hồi (Backlog).
                } @else {
                  Bạn chưa có nhiệm vụ học tập nào trong mục này. Các nhiệm vụ sẽ tự động được tạo ra khi bạn kích hoạt hoặc tiếp tục Lộ trình học tập, hoặc bấm "+ Thêm việc mới".
                }
              </p>
              <a
                routerLink="/roadmaps"
                appButton
                variant="default"
                size="sm"
              >
                Xem Lộ trình học tập
              </a>
            </div>
          } @else {
            @for (task of filteredTasks(); track task.id) {
              <article
                data-testid="task-card"
                class="p-4 sm:p-5 rounded-xl border border-[var(--border)] bg-[var(--card)] flex flex-col lg:flex-row lg:items-center justify-between gap-4 shadow-xs"
              >
                <div class="space-y-2 min-w-0 flex-1">
                  <!-- Title & Status Badges -->
                  <div class="flex flex-wrap items-center gap-2">
                    <h3 class="font-semibold text-sm sm:text-base text-[var(--foreground)]">
                      {{ task.title }}
                    </h3>

                    @if (task.status === 'COMPLETED') {
                      <span appBadge variant="success">Hoàn thành</span>
                    } @else if (task.status === 'IN_PROGRESS') {
                      <span appBadge variant="default">Đang học</span>
                    } @else if (task.scheduled_date) {
                      <span appBadge variant="outline">Đã lên lịch</span>
                    } @else {
                      <span appBadge variant="outline">Backlog</span>
                    }

                    @if (task.is_overdue) {
                      <span
                        appBadge
                        variant="destructive"
                        title="Nhiệm vụ đã quá hạn dự kiến và cần được hoàn thành hoặc dời lịch."
                      >
                        <lucide-icon name="alert-triangle" [size]="11" class="mr-1" aria-hidden="true"></lucide-icon>
                        Quá hạn
                      </span>
                    }

                    @if (task.is_blocked) {
                      <span
                        appBadge
                        variant="outline"
                        class="border-amber-500/60 text-amber-800 dark:text-amber-300"
                        title="Cần hoàn thành các nhiệm vụ tiền đề trước khi hoàn tất nhiệm vụ này."
                      >
                        <lucide-icon name="lock" [size]="11" class="mr-1" aria-hidden="true"></lucide-icon>
                        Bị chặn
                      </span>
                    }

                    @if (task.is_stalled || task.reschedule_count >= 3) {
                      <span
                        appBadge
                        variant="outline"
                        class="border-purple-500/60 text-purple-800 dark:text-purple-300"
                        [title]="'Nhiệm vụ đã bị dời lịch ' + task.reschedule_count + ' lần. Cần can thiệp cam kết lại hoặc đưa về Backlog.'"
                      >
                        Đình trệ ({{ task.reschedule_count }} lần)
                      </span>
                    }
                  </div>

                  @if (task.description) {
                    <p class="text-xs sm:text-sm text-[var(--muted-foreground)] leading-relaxed">
                      {{ task.description }}
                    </p>
                  }

                  <!-- Meta row -->
                  <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--muted-foreground)]">
                    @if (task.roadmap_title) {
                      <span class="font-medium text-[var(--foreground)]">{{ task.roadmap_title }}</span>
                      <span>&bull;</span>
                    }
                    <span class="inline-flex items-center gap-1 font-mono">
                      <lucide-icon name="clock" [size]="12" aria-hidden="true"></lucide-icon>
                      {{ task.estimated_minutes }} phút
                    </span>
                    @if (task.scheduled_date) {
                      <span>&bull;</span>
                      <span class="inline-flex items-center gap-1">
                        <lucide-icon name="calendar" [size]="12" aria-hidden="true"></lucide-icon>
                        {{ formatScheduledInfo(task) }}
                      </span>
                    }
                    @if (activeTab() === 'BACKLOG' && task.priority_rank !== null && task.priority_rank !== undefined) {
                      <span>&bull;</span>
                      <span class="font-mono text-[var(--primary)] font-semibold">
                        Ưu tiên #{{ task.priority_rank }}
                      </span>
                    }
                  </div>

                  <!-- Learning Resources Chips -->
                  @if (getTaskResources(task).length > 0) {
                    <div class="flex flex-wrap gap-1.5 pt-1">
                      @for (res of getTaskResources(task); track $index) {
                        @if (res.url) {
                          <a
                            [href]="res.url"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] bg-[var(--muted)] text-[var(--primary)] border border-[var(--border)] hover:underline"
                          >
                            <lucide-icon name="book-open" [size]="11" aria-hidden="true"></lucide-icon>
                            <span>{{ res.label }}</span>
                          </a>
                        } @else {
                          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] bg-[var(--muted)] text-[var(--foreground)] border border-[var(--border)]">
                            <lucide-icon name="book-open" [size]="11" aria-hidden="true"></lucide-icon>
                            <span>{{ res.label }}</span>
                          </span>
                        }
                      }
                    </div>
                  }
                </div>

                <!-- Actions -->
                <div class="flex flex-wrap items-center gap-2 shrink-0">
                  @if (task.status !== 'COMPLETED' && task.status !== 'CANCELLED') {
                    <a
                      [routerLink]="['/workspace']"
                      [queryParams]="{ taskId: task.id }"
                      appButton
                      variant="default"
                      size="sm"
                      class="no-underline"
                    >
                      <lucide-icon name="play" [size]="13" aria-hidden="true"></lucide-icon>
                      <span>Vào học</span>
                    </a>

                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      [disabled]="task.is_blocked"
                      [title]="task.is_blocked ? 'Cần hoàn thành nhiệm vụ tiền đề trước' : 'Đánh dấu hoàn thành'"
                      (click)="openCompleteModal(task)"
                    >
                      <lucide-icon name="check" [size]="13" aria-hidden="true"></lucide-icon>
                      <span>Hoàn thành</span>
                    </button>

                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      (click)="openRescheduleModal(task)"
                    >
                      <lucide-icon name="calendar" [size]="13" aria-hidden="true"></lucide-icon>
                      <span>{{ task.is_stalled || task.reschedule_count >= 3 ? 'Can thiệp / Dời lịch' : 'Dời lịch' }}</span>
                    </button>

                    <button
                      type="button"
                      appButton
                      variant="ghost"
                      size="sm"
                      class="text-red-700 dark:text-red-400"
                      (click)="confirmDeleteTask(task)"
                      aria-label="Hủy nhiệm vụ"
                    >
                      <lucide-icon name="trash-2" [size]="13" aria-hidden="true"></lucide-icon>
                      <span>Hủy</span>
                    </button>
                  } @else if (task.status === 'COMPLETED') {
                    <button
                      type="button"
                      appButton
                      variant="outline"
                      size="sm"
                      [disabled]="taskService.isSubmitting()"
                      (click)="reopenTask(task)"
                    >
                      <lucide-icon name="rotate-ccw" [size]="13" aria-hidden="true"></lucide-icon>
                      <span>Mở lại</span>
                    </button>
                  }
                </div>
              </article>
            }
          }
        </div>
      }
    </div>

    <!-- Create Task Modal -->
    @if (createModalOpen()) {
      <div
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs"
        (click)="closeCreateModal()"
        aria-hidden="true"
      ></div>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-task-title"
        data-testid="create-task-dialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
      >
        <div
          class="pointer-events-auto w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] shadow-2xl p-5 sm:p-6 space-y-4"
          (click)="$event.stopPropagation()"
        >
          <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <h2 id="create-task-title" class="text-lg font-bold">Thêm nhiệm vụ học tập mới</h2>
            <button
              type="button"
              appButton
              variant="ghost"
              size="icon"
              (click)="closeCreateModal()"
              aria-label="Đóng"
            >
              <lucide-icon name="x" [size]="18" aria-hidden="true"></lucide-icon>
            </button>
          </div>

          @if (modalError(); as mErr) {
            <div role="alert" class="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-xs text-red-900 dark:text-red-200 space-y-0.5">
              @if (mErr.code) {
                <div class="font-mono font-bold">{{ mErr.code }}</div>
              }
              <div>{{ mErr.message }}</div>
            </div>
          }

          @if (taskService.roadmaps().length === 0) {
            <div class="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 text-xs space-y-2">
              <p>Bạn cần có ít nhất một Lộ trình học tập trước khi tạo nhiệm vụ thủ công.</p>
              <a routerLink="/roadmaps" appButton variant="default" size="sm">Đi tới Lộ trình học tập</a>
            </div>
          } @else {
            <div class="space-y-3">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="space-y-1">
                  <label for="new-task-roadmap" class="block text-xs font-semibold">Lộ trình *</label>
                  <select
                    id="new-task-roadmap"
                    [ngModel]="newTaskRoadmapId()"
                    (ngModelChange)="onNewTaskRoadmapChange($event)"
                    class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-2.5 text-sm"
                  >
                    @for (rm of taskService.roadmaps(); track rm.id) {
                      <option [value]="rm.id">{{ rm.title }}</option>
                    }
                  </select>
                </div>

                <div class="space-y-1">
                  <label for="new-task-milestone" class="block text-xs font-semibold">Cột mốc (Milestone) *</label>
                  <select
                    id="new-task-milestone"
                    [ngModel]="newTaskMilestoneId()"
                    (ngModelChange)="newTaskMilestoneId.set($event)"
                    class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-2.5 text-sm"
                  >
                    @for (ms of currentRoadmapMilestones(); track ms.id) {
                      <option [value]="ms.id">{{ ms.sequence_order }}. {{ ms.title }}</option>
                    }
                  </select>
                </div>
              </div>

              <div class="space-y-1">
                <label for="new-task-title-input" class="block text-xs font-semibold">Tiêu đề nhiệm vụ *</label>
                <input
                  id="new-task-title-input"
                  type="text"
                  [ngModel]="newTaskTitle()"
                  (ngModelChange)="newTaskTitle.set($event)"
                  placeholder="Ví dụ: Ôn tập SQL Indexing và B-Tree"
                  class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                />
              </div>

              <div class="space-y-1">
                <label for="new-task-desc-input" class="block text-xs font-semibold">Mô tả (tùy chọn)</label>
                <textarea
                  id="new-task-desc-input"
                  rows="2"
                  [ngModel]="newTaskDescription()"
                  (ngModelChange)="newTaskDescription.set($event)"
                  placeholder="Ghi chú nội dung hoặc mục tiêu cần đạt..."
                  class="w-full rounded-lg border border-[var(--input)] bg-[var(--background)] p-2.5 text-sm"
                ></textarea>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="space-y-1">
                  <label for="new-task-minutes" class="block text-xs font-semibold">Thời lượng (15–240 phút) *</label>
                  <input
                    id="new-task-minutes"
                    type="number"
                    min="15"
                    max="240"
                    [ngModel]="newTaskMinutes()"
                    (ngModelChange)="newTaskMinutes.set(+$event)"
                    class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                  />
                </div>

                <div class="space-y-1">
                  <label for="new-task-date" class="block text-xs font-semibold">Ngày học (để trống = Backlog)</label>
                  <input
                    id="new-task-date"
                    type="date"
                    [ngModel]="newTaskDate()"
                    (ngModelChange)="newTaskDate.set($event)"
                    class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                  />
                </div>
              </div>

              @if (newTaskDate()) {
                <div class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label for="new-task-start" class="block text-xs font-semibold">Giờ bắt đầu</label>
                    <input
                      id="new-task-start"
                      type="time"
                      [ngModel]="newTaskStartTime()"
                      (ngModelChange)="newTaskStartTime.set($event)"
                      class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                    />
                  </div>
                  <div class="space-y-1">
                    <label for="new-task-end" class="block text-xs font-semibold">Giờ kết thúc</label>
                    <input
                      id="new-task-end"
                      type="time"
                      [ngModel]="newTaskEndTime()"
                      (ngModelChange)="newTaskEndTime.set($event)"
                      class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                    />
                  </div>
                </div>
              }

              <label class="flex items-center gap-2 text-xs cursor-pointer pt-1">
                <input
                  type="checkbox"
                  [checked]="newTaskConfirmSoftOverflow()"
                  (change)="newTaskConfirmSoftOverflow.set($any($event.target).checked)"
                  class="h-4 w-4 accent-[var(--primary)]"
                />
                <span>Cho phép Soft Overflow (&le; 30 phút vượt khung giờ ngày) nếu cần</span>
              </label>
            </div>
          }

          <div class="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
            <button type="button" appButton variant="outline" (click)="closeCreateModal()">Hủy</button>
            <button
              type="button"
              appButton
              variant="default"
              data-testid="submit-create-task-btn"
              [disabled]="
                taskService.isSubmitting() ||
                !newTaskRoadmapId() ||
                !newTaskMilestoneId() ||
                !newTaskTitle().trim() ||
                newTaskMinutes() < 15 ||
                newTaskMinutes() > 240
              "
              (click)="submitCreateTask()"
            >
              {{ taskService.isSubmitting() ? 'Đang tạo...' : 'Tạo nhiệm vụ' }}
            </button>
          </div>
        </div>
      </div>
    }

    <!-- Complete Task Modal -->
    @if (completingTask(); as taskToComplete) {
      <div
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs"
        (click)="closeCompleteModal()"
        aria-hidden="true"
      ></div>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="complete-task-title"
        data-testid="complete-task-dialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
      >
        <div
          class="pointer-events-auto w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] shadow-2xl p-5 sm:p-6 space-y-4"
          (click)="$event.stopPropagation()"
        >
          <div class="flex items-start justify-between gap-2 border-b border-[var(--border)] pb-3">
            <div>
              <h2 id="complete-task-title" class="text-base font-bold">Hoàn thành nhiệm vụ</h2>
              <p class="text-xs text-[var(--muted-foreground)] mt-0.5">{{ taskToComplete.title }}</p>
            </div>
            <button type="button" appButton variant="ghost" size="icon" (click)="closeCompleteModal()" aria-label="Đóng">
              <lucide-icon name="x" [size]="18" aria-hidden="true"></lucide-icon>
            </button>
          </div>

          @if (modalError(); as mErr) {
            <div role="alert" class="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-xs text-red-900 dark:text-red-200">
              @if (mErr.code) {
                <div class="font-mono font-bold">{{ mErr.code }}</div>
              }
              <div>{{ mErr.message }}</div>
            </div>
          }

          <div class="space-y-1.5">
            <label for="complete-takeaway-input" class="block text-xs font-semibold">
              Key Takeaway (tùy chọn — nếu nhập phải &ge; 30 ký tự &amp; 6 từ)
            </label>
            <textarea
              id="complete-takeaway-input"
              rows="3"
              [ngModel]="completeTakeaway()"
              (ngModelChange)="completeTakeaway.set($event)"
              placeholder="Để trống để hoàn thành nhanh, hoặc ghi tóm tắt kiến thức bạn đã nắm vững..."
              class="w-full rounded-xl border border-[var(--input)] bg-[var(--background)] p-3 text-sm"
            ></textarea>
            @if (completeTakeaway().trim().length > 0) {
              <div class="text-[11px] text-[var(--muted-foreground)]">
                {{ completeTakeawayCheck().charCount }}/30 ký tự &bull; {{ completeTakeawayCheck().distinctWordCount }}/6 từ
              </div>
            }
          </div>

          <div class="space-y-1.5">
            <span class="block text-xs font-semibold">Mức độ tự tin (1–5)</span>
            <div class="flex items-center gap-2">
              @for (score of [1, 2, 3, 4, 5]; track score) {
                <button
                  type="button"
                  (click)="completeConfidence.set(score)"
                  class="flex-1 h-8 rounded-lg text-xs font-bold border cursor-pointer"
                  [class]="completeConfidence() === score
                    ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]'
                    : 'bg-[var(--background)] border-[var(--border)]'"
                >
                  {{ score }}
                </button>
              }
            </div>
          </div>

          <div class="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
            <button type="button" appButton variant="outline" (click)="closeCompleteModal()">Hủy</button>
            <button
              type="button"
              appButton
              variant="default"
              data-testid="submit-complete-task-btn"
              [disabled]="
                taskService.isSubmitting() ||
                (completeTakeaway().trim().length > 0 && !completeTakeawayCheck().isValid)
              "
              (click)="submitCompleteTask()"
            >
              {{ taskService.isSubmitting() ? 'Đang lưu...' : 'Xác nhận hoàn thành' }}
            </button>
          </div>
        </div>
      </div>
    }

    <!-- Reschedule / Backlog Modal -->
    @if (reschedulingTask(); as taskToMove) {
      <div
        class="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs"
        (click)="closeRescheduleModal()"
        aria-hidden="true"
      ></div>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reschedule-task-title"
        data-testid="reschedule-task-dialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
      >
        <div
          class="pointer-events-auto w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] shadow-2xl p-5 sm:p-6 space-y-4"
          (click)="$event.stopPropagation()"
        >
          <div class="flex items-start justify-between gap-2 border-b border-[var(--border)] pb-3">
            <div>
              <h2 id="reschedule-task-title" class="text-base font-bold">Dời lịch hoặc đưa về Backlog</h2>
              <p class="text-xs text-[var(--muted-foreground)] mt-0.5">{{ taskToMove.title }}</p>
            </div>
            <button type="button" appButton variant="ghost" size="icon" (click)="closeRescheduleModal()" aria-label="Đóng">
              <lucide-icon name="x" [size]="18" aria-hidden="true"></lucide-icon>
            </button>
          </div>

          @if (taskToMove.is_stalled || taskToMove.reschedule_count >= 3) {
            <div class="p-3 rounded-xl border border-purple-500/40 bg-purple-500/10 text-xs text-purple-900 dark:text-purple-200 space-y-2">
              <div class="font-bold">Can thiệp STALLED (đã dời {{ taskToMove.reschedule_count }} lần)</div>
              <p>Để tiếp tục xếp lịch mới, bạn cần xác nhận cam kết thực hiện (Re-commit) hoặc chuyển về Backlog.</p>
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  [checked]="allowStalledCommitment()"
                  (change)="allowStalledCommitment.set($any($event.target).checked)"
                  class="h-4 w-4 accent-[var(--primary)]"
                />
                <span>Tôi cam kết hoàn thành nhiệm vụ trong khung giờ mới</span>
              </label>
            </div>
          }

          @if (modalError(); as mErr) {
            <div role="alert" class="p-3 rounded-xl border border-red-500/40 bg-red-500/10 text-xs text-red-900 dark:text-red-200 space-y-1">
              @if (mErr.code) {
                <div class="font-mono font-bold">{{ mErr.code }}</div>
              }
              <div>{{ mErr.message }}</div>
            </div>
          }

          <div class="space-y-3">
            <div class="space-y-1">
              <label for="reschedule-date-input" class="block text-xs font-semibold">Ngày mới</label>
              <input
                id="reschedule-date-input"
                type="date"
                [ngModel]="rescheduleDate()"
                (ngModelChange)="rescheduleDate.set($event)"
                class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
              />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <label for="reschedule-start-input" class="block text-xs font-semibold">Giờ bắt đầu</label>
                <input
                  id="reschedule-start-input"
                  type="time"
                  [ngModel]="rescheduleStartTime()"
                  (ngModelChange)="rescheduleStartTime.set($event)"
                  class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                />
              </div>
              <div class="space-y-1">
                <label for="reschedule-end-input" class="block text-xs font-semibold">Giờ kết thúc</label>
                <input
                  id="reschedule-end-input"
                  type="time"
                  [ngModel]="rescheduleEndTime()"
                  (ngModelChange)="rescheduleEndTime.set($event)"
                  class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
                />
              </div>
            </div>

            <div class="space-y-1">
              <label for="reschedule-reason-input" class="block text-xs font-semibold">Lý do (tùy chọn)</label>
              <input
                id="reschedule-reason-input"
                type="text"
                [ngModel]="rescheduleReason()"
                (ngModelChange)="rescheduleReason.set($event)"
                placeholder="Ví dụ: Đổi sang tối mai để tập trung hơn"
                class="w-full h-9 rounded-lg border border-[var(--input)] bg-[var(--background)] px-3 text-sm"
              />
            </div>

            <label class="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                [checked]="rescheduleConfirmSoftOverflow()"
                (change)="rescheduleConfirmSoftOverflow.set($any($event.target).checked)"
                class="h-4 w-4 accent-[var(--primary)]"
              />
              <span>Xác nhận Soft Overflow (&le; 30 phút) nếu vượt khung giờ rảnh</span>
            </label>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border)]">
            <button
              type="button"
              appButton
              variant="outline"
              size="sm"
              data-testid="move-to-backlog-btn"
              [disabled]="taskService.isSubmitting()"
              (click)="submitMoveToBacklog()"
            >
              Đưa về Backlog
            </button>

            <div class="flex items-center gap-2">
              <button type="button" appButton variant="ghost" size="sm" (click)="closeRescheduleModal()">Hủy</button>
              <button
                type="button"
                appButton
                variant="default"
                size="sm"
                data-testid="submit-reschedule-btn"
                [disabled]="taskService.isSubmitting() || !rescheduleDate()"
                (click)="submitRescheduleDate()"
              >
                {{ taskService.isSubmitting() ? 'Đang lưu...' : 'Lưu lịch mới' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    }
  `,
})
export class TasksPageComponent implements OnInit {
  readonly taskService = inject(TaskService);
  private readonly destroyRef = inject(DestroyRef);

  readonly filterTabs: ReadonlyArray<{ key: TaskFilterTab; label: string }> = [
    { key: 'ALL', label: 'Tất cả' },
    { key: 'SCHEDULED', label: 'Đã lên lịch' },
    { key: 'BACKLOG', label: 'Hàng đợi Phục hồi (Backlog)' },
    { key: 'COMPLETED', label: 'Đã hoàn thành' },
  ];

  readonly activeTab = signal<TaskFilterTab>('ALL');
  readonly selectedRoadmapFilter = signal<string>('');

  // Create modal state
  readonly createModalOpen = signal<boolean>(false);
  readonly newTaskRoadmapId = signal<string>('');
  readonly newTaskMilestoneId = signal<string>('');
  readonly newTaskTitle = signal<string>('');
  readonly newTaskDescription = signal<string>('');
  readonly newTaskMinutes = signal<number>(30);
  readonly newTaskDate = signal<string>('');
  readonly newTaskStartTime = signal<string>('19:00');
  readonly newTaskEndTime = signal<string>('19:30');
  readonly newTaskConfirmSoftOverflow = signal<boolean>(false);

  // Complete modal state
  readonly completingTask = signal<TaskResponse | null>(null);
  readonly completeTakeaway = signal<string>('');
  readonly completeConfidence = signal<number>(4);
  readonly completeTakeawayCheck = computed(() => evaluateTakeawayCheck(this.completeTakeaway()));

  // Reschedule modal state
  readonly reschedulingTask = signal<TaskResponse | null>(null);
  readonly rescheduleDate = signal<string>('');
  readonly rescheduleStartTime = signal<string>('19:00');
  readonly rescheduleEndTime = signal<string>('19:30');
  readonly rescheduleReason = signal<string>('');
  readonly allowStalledCommitment = signal<boolean>(false);
  readonly rescheduleConfirmSoftOverflow = signal<boolean>(false);

  readonly anyModalOpen = computed(
    () =>
      this.createModalOpen() ||
      this.completingTask() !== null ||
      this.reschedulingTask() !== null
  );
  readonly pageError = computed(() => (this.anyModalOpen() ? null : this.taskService.errorState()));
  readonly modalError = computed(() => (this.anyModalOpen() ? this.taskService.errorState() : null));

  readonly currentRoadmapMilestones = computed(() => {
    const rid = this.newTaskRoadmapId();
    return rid ? (this.taskService.milestonesByRoadmap()[rid] ?? []) : [];
  });

  readonly filteredTasks = computed<TaskResponse[]>(() => {
    const tab = this.activeTab();
    const rmFilter = this.selectedRoadmapFilter();
    const matchRoadmap = (t: TaskResponse) => !rmFilter || t.roadmap_id === rmFilter;

    if (tab === 'BACKLOG') {
      return this.taskService.backlogTasks().filter(matchRoadmap);
    }

    const all = this.taskService.tasks().filter((t) => t.status !== 'CANCELLED' && matchRoadmap(t));
    if (tab === 'SCHEDULED') {
      return all.filter((t) => !!t.scheduled_date && t.status !== 'COMPLETED');
    }
    if (tab === 'COMPLETED') {
      return all.filter((t) => t.status === 'COMPLETED');
    }
    return all;
  });

  ngOnInit(): void {
    this.refreshAll();
  }

  refreshAll(): void {
    const rmId = this.selectedRoadmapFilter() || null;
    forkJoin([
      this.taskService.loadTasks(rmId),
      this.taskService.loadBacklogTasks(rmId),
      this.taskService.loadRoadmaps(),
    ])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  selectTab(tab: TaskFilterTab): void {
    this.activeTab.set(tab);
  }

  onRoadmapFilterChange(roadmapId: string): void {
    this.selectedRoadmapFilter.set(roadmapId);
    this.refreshAll();
  }

  tabCount(tab: TaskFilterTab): number {
    const rmFilter = this.selectedRoadmapFilter();
    const matchRoadmap = (t: TaskResponse) => !rmFilter || t.roadmap_id === rmFilter;

    if (tab === 'BACKLOG') {
      return this.taskService.backlogTasks().filter(matchRoadmap).length;
    }
    const nonCancelled = this.taskService
      .tasks()
      .filter((t) => t.status !== 'CANCELLED' && matchRoadmap(t));
    if (tab === 'SCHEDULED') {
      return nonCancelled.filter((t) => !!t.scheduled_date && t.status !== 'COMPLETED').length;
    }
    if (tab === 'COMPLETED') {
      return nonCancelled.filter((t) => t.status === 'COMPLETED').length;
    }
    return nonCancelled.length;
  }

  openCreateModal(): void {
    this.taskService.clearError();
    this.newTaskTitle.set('');
    this.newTaskDescription.set('');
    this.newTaskMinutes.set(30);
    this.newTaskDate.set('');
    this.newTaskStartTime.set('19:00');
    this.newTaskEndTime.set('19:30');
    this.newTaskConfirmSoftOverflow.set(false);

    const roadmaps = this.taskService.roadmaps();
    const defaultRmId = this.selectedRoadmapFilter() || roadmaps[0]?.id || '';
    if (defaultRmId) {
      this.onNewTaskRoadmapChange(defaultRmId);
    }
    this.createModalOpen.set(true);
  }

  closeCreateModal(): void {
    this.createModalOpen.set(false);
    this.taskService.clearError();
  }

  onNewTaskRoadmapChange(roadmapId: string): void {
    this.newTaskRoadmapId.set(roadmapId);
    this.newTaskMilestoneId.set('');
    if (!roadmapId) return;

    this.taskService
      .loadRoadmapMilestones(roadmapId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((milestones) => {
        if (milestones.length > 0 && !this.newTaskMilestoneId()) {
          this.newTaskMilestoneId.set(milestones[0].id);
        }
      });
  }

  submitCreateTask(): void {
    const roadmapId = this.newTaskRoadmapId();
    const milestoneId = this.newTaskMilestoneId();
    const title = this.newTaskTitle().trim();
    if (!roadmapId || !milestoneId || !title) return;

    const scheduledDate = this.newTaskDate().trim() || null;
    const scheduledStart = scheduledDate
      ? toLocalIsoDateTime(scheduledDate, this.newTaskStartTime())
      : null;
    const scheduledEnd = scheduledDate
      ? toLocalIsoDateTime(scheduledDate, this.newTaskEndTime())
      : null;

    this.taskService
      .createTask({
        roadmap_id: roadmapId,
        milestone_id: milestoneId,
        title,
        description: this.newTaskDescription().trim() || null,
        estimated_minutes: this.newTaskMinutes(),
        scheduled_date: scheduledDate,
        scheduled_start: scheduledStart,
        scheduled_end: scheduledEnd,
        confirm_soft_overflow: this.newTaskConfirmSoftOverflow(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closeCreateModal();
        },
      });
  }

  openCompleteModal(task: TaskResponse): void {
    this.taskService.clearError();
    this.completeTakeaway.set('');
    this.completeConfidence.set(4);
    this.completingTask.set(task);
  }

  closeCompleteModal(): void {
    this.completingTask.set(null);
    this.taskService.clearError();
  }

  submitCompleteTask(): void {
    const task = this.completingTask();
    if (!task) return;

    const trimmed = this.completeTakeaway().trim();
    this.taskService
      .completeTask(
        task.id,
        trimmed.length > 0
          ? { takeaway: trimmed, self_confidence: this.completeConfidence() }
          : null
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closeCompleteModal();
        },
      });
  }

  reopenTask(task: TaskResponse): void {
    this.taskService
      .reopenTask(task.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  openRescheduleModal(task: TaskResponse): void {
    this.taskService.clearError();
    this.rescheduleDate.set(task.scheduled_date ?? '');
    this.rescheduleStartTime.set(this.extractLocalHHmm(task.scheduled_start) || '19:00');
    this.rescheduleEndTime.set(this.extractLocalHHmm(task.scheduled_end) || '19:30');
    this.rescheduleReason.set('');
    this.allowStalledCommitment.set(false);
    this.rescheduleConfirmSoftOverflow.set(false);
    this.reschedulingTask.set(task);
  }

  closeRescheduleModal(): void {
    this.reschedulingTask.set(null);
    this.taskService.clearError();
  }

  submitRescheduleDate(): void {
    const task = this.reschedulingTask();
    const dateStr = this.rescheduleDate().trim();
    if (!task || !dateStr) return;

    this.taskService
      .rescheduleTask(task.id, {
        scheduled_date: dateStr,
        scheduled_start: toLocalIsoDateTime(dateStr, this.rescheduleStartTime()),
        scheduled_end: toLocalIsoDateTime(dateStr, this.rescheduleEndTime()),
        reason: this.rescheduleReason().trim() || null,
        allow_stalled_commitment: this.allowStalledCommitment(),
        confirm_soft_overflow: this.rescheduleConfirmSoftOverflow(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closeRescheduleModal();
        },
      });
  }

  submitMoveToBacklog(): void {
    const task = this.reschedulingTask();
    if (!task) return;

    this.taskService
      .rescheduleTask(task.id, {
        scheduled_date: null,
        scheduled_start: null,
        scheduled_end: null,
        reason: this.rescheduleReason().trim() || 'Chuyển về Hàng đợi Phục hồi Backlog',
        allow_stalled_commitment: this.allowStalledCommitment(),
        confirm_soft_overflow: false,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closeRescheduleModal();
        },
      });
  }

  confirmDeleteTask(task: TaskResponse): void {
    if (confirm(`Bạn có chắc muốn hủy nhiệm vụ "${task.title}"?`)) {
      this.taskService
        .deleteTask(task.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe();
    }
  }

  onEscape(): void {
    if (this.createModalOpen()) {
      this.closeCreateModal();
    } else if (this.completingTask()) {
      this.closeCompleteModal();
    } else if (this.reschedulingTask()) {
      this.closeRescheduleModal();
    }
  }

  getTaskResources(task: TaskResponse): Array<{ label: string; url: string | null }> {
    return (task.learning_resources ?? []).map((raw, idx) => {
      const labelCandidate = raw['title'] ?? raw['name'] ?? raw['label'] ?? raw['url'];
      const label =
        typeof labelCandidate === 'string' && labelCandidate.trim().length > 0
          ? labelCandidate.trim()
          : `Học liệu #${idx + 1}`;
      const urlCandidate = raw['url'] ?? raw['href'];
      const url =
        typeof urlCandidate === 'string' && /^https?:\/\//i.test(urlCandidate.trim())
          ? urlCandidate.trim()
          : null;
      return { label, url };
    });
  }

  formatScheduledInfo(task: TaskResponse): string {
    if (!task.scheduled_date) return 'Chưa lên lịch';
    const start = this.extractLocalHHmm(task.scheduled_start);
    const end = this.extractLocalHHmm(task.scheduled_end);
    return start && end ? `${task.scheduled_date} (${start}–${end})` : task.scheduled_date;
  }

  private extractLocalHHmm(iso: string | null | undefined): string {
    if (!iso) return '';
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return '';
    return dt.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }
}
