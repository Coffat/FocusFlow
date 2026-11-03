import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { WorkspaceSessionService } from '../../core/services/workspace-session.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-workspace',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  template: `
    <div class="max-w-4xl mx-auto w-full p-8 flex flex-col items-center gap-8">
      <!-- Title & Context -->
      <div class="text-center space-y-2">
        <span class="text-xs uppercase tracking-wider font-semibold text-[var(--muted-foreground)]">Study Workspace (Pomodoro)</span>
        <h1 class="text-3xl font-bold tracking-tight">Phiên Học Tập Trung</h1>
        <p class="text-sm text-[var(--muted-foreground)]">Thực thi công việc học tập với cơ chế bảo toàn nhịp tim và chống mất tập trung</p>
      </div>

      <!-- Main Pomodoro Card -->
      <div class="w-full max-w-md bg-[var(--card)] border border-[var(--border)] rounded-2xl p-8 flex flex-col items-center gap-6 shadow-sm">
        <!-- Progress Bar -->
        <div class="w-full bg-[var(--muted)] h-2 rounded-full overflow-hidden">
          <div class="bg-[var(--primary)] h-full transition-all duration-300" [style.width.%]="sessionService.progressPercentage()"></div>
        </div>

        <!-- Clock Face -->
        <div class="text-7xl font-mono font-bold tracking-tighter text-[var(--foreground)] select-none">
          {{ sessionService.formattedTime() }}
        </div>

        <!-- Mode Indicator -->
        <div class="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
          <span class="w-2 h-2 rounded-full" [class.bg-emerald-500]="sessionService.isRunning()" [class.bg-amber-500]="!sessionService.isRunning()"></span>
          <span>{{ sessionService.isRunning() ? 'Đang chạy (Heartbeat 60s active)' : 'Đang tạm dừng' }}</span>
        </div>

        <!-- Controls -->
        <div class="flex items-center gap-3">
          @if (!sessionService.isRunning()) {
            <button
              (click)="startOrResume()"
              class="px-6 py-2.5 rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)] font-medium text-sm hover:opacity-90 transition-opacity shadow-sm cursor-pointer">
              Bắt đầu / Tiếp tục
            </button>
          } @else {
            <button
              (click)="sessionService.pauseSession()"
              class="px-6 py-2.5 rounded-lg bg-[var(--secondary)] text-[var(--secondary-foreground)] font-medium text-sm hover:opacity-80 transition-opacity border border-[var(--border)] cursor-pointer">
              Tạm dừng
            </button>
          }
        </div>
      </div>

      <!-- Scratchpad Draft -->
      <div class="w-full max-w-md bg-[var(--card)] border border-[var(--border)] rounded-xl p-5 space-y-3 shadow-sm">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">Ghi chú nháp (Scratchpad)</span>
          <span class="text-[10px] text-[var(--muted-foreground)]">Tự lưu cục bộ</span>
        </div>
        <textarea
          [ngModel]="sessionService.scratchpadNote()"
          (ngModelChange)="sessionService.setScratchpadNote($event)"
          placeholder="Ghi nhanh suy nghĩ, thắc mắc hoặc việc đột xuất nảy sinh trong lúc học..."
          rows="3"
          class="w-full bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--ring)] resize-none"
        ></textarea>
      </div>
    </div>
  `
})
export class WorkspaceComponent {
  readonly sessionService = inject(WorkspaceSessionService);

  startOrResume(): void {
    if (!this.sessionService.sessionId()) {
      this.sessionService.startSession('session-demo-01', 'task-demo-01', 25);
    } else {
      this.sessionService.resumeSession();
    }
  }
}
