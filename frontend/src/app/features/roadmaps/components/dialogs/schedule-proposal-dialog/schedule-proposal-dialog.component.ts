import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoadmapService } from '../../../services/roadmap.service';
import { ProposedTaskItemSchema } from '../../../models/roadmap.model';
import { CalendarIntegrationService } from '../../../../../core/services/calendar-integration.service';
import { AvailabilityService } from '../../../../../core/services/availability.service';

export interface ScheduleViewResourceItem {
  title: string;
  url: string;
  resourceType: string;
}

export interface DailyScheduleGroup {
  date: string;
  dayOfWeekLabel: string;
  totalMinutes: number;
  totalHours: number;
  sessions: Array<{
    task: ProposedTaskItemSchema;
    globalIndex: number;
    milestoneTitle: string;
    timeSlotLabel: string;
  }>;
}

export interface WeeklyScheduleGroup {
  weekNumber: number;
  weekLabel: string;
  totalMinutes: number;
  totalHours: number;
  days: DailyScheduleGroup[];
}

const VIETNAMESE_WEEKDAYS = [
  'Chủ Nhật',
  'Thứ Hai',
  'Thứ Ba',
  'Thứ Tư',
  'Thứ Năm',
  'Thứ Sáu',
  'Thứ Bảy',
] as const;

function extractTimeHHmm(raw: string | null | undefined, fallback: string): string {
  if (!raw || !raw.trim()) return fallback;
  const trimmed = raw.trim();
  const isoMatch = trimmed.match(/T(\d{2}:\d{2})/);
  if (isoMatch) return isoMatch[1];
  const hhmmMatch = trimmed.match(/^(\d{2}:\d{2})/);
  if (hhmmMatch) return hhmmMatch[1];
  return fallback;
}

function getMondayKey(dateStr: string): string {
  const parts = dateStr.split('-').map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) {
    return dateStr;
  }
  const dt = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  const day = dt.getUTCDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  dt.setUTCDate(dt.getUTCDate() + diffToMonday);
  return dt.toISOString().slice(0, 10);
}

function getDayOfWeekLabel(dateStr: string): string {
  const parts = dateStr.split('-').map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) {
    return 'Chưa xếp ngày';
  }
  const dt = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  return VIETNAMESE_WEEKDAYS[dt.getUTCDay()] ?? 'Ngày học';
}

@Component({
  selector: 'app-schedule-proposal-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './schedule-proposal-dialog.component.html',
  styleUrl: './schedule-proposal-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScheduleProposalDialogComponent implements OnInit {
  readonly roadmapService = inject(RoadmapService);
  private readonly calendarService = inject(CalendarIntegrationService);
  private readonly availabilityService = inject(AvailabilityService);

  ngOnInit(): void {
    if (this.calendarService.connection() === null) {
      this.calendarService.loadStatus().subscribe();
    }
  }

  readonly backToStep3 = output<void>();
  readonly generateProposal = output<void>();
  readonly regenerateRoadmapFitCapacity = output<void>();
  readonly manualScheduleFallback = output<void>();
  readonly updateProposal = output<void>();
  readonly applyProposal = output<boolean>();

  readonly viewMode = signal<'TIMELINE' | 'CALENDAR'>('TIMELINE');

  readonly step4InlineStages = [
    { index: 1, label: '1. Phân rã bài học', threshold: 10 },
    { index: 2, label: '2. Kiểm định tính khả thi', threshold: 35 },
    { index: 3, label: '3. Xếp lịch vào giờ rảnh', threshold: 65 },
    { index: 4, label: '4. Hoàn thiện đề xuất', threshold: 90 },
  ] as const;

  readonly sseProgress = computed(() => this.roadmapService.sseProgress());
  readonly step4ProgressPercent = computed<number>(() => this.sseProgress().progress ?? 0);

  readonly isProposalFailed = computed<boolean>(() => {
    if (this.roadmapService.isGeneratingStream()) return false;
    if (typeof this.roadmapService.manualPlanningMode === 'function' && this.roadmapService.manualPlanningMode()) {
      return false;
    }
    const err =
      typeof this.roadmapService.errorMessage === 'function'
        ? this.roadmapService.errorMessage()
        : null;
    const sse = this.sseProgress();
    return (Boolean(err) || sse?.stage === 'FAILED') && this.editableTasks().length === 0;
  });

  readonly hasDiffNote = computed<boolean>(() => {
    const diff = this.diffSummary();
    return (diff.preserved_completed_tasks_count ?? 0) > 0 || (diff.replaced_tasks_count ?? 0) > 0;
  });

  readonly editableTasks = computed<ProposedTaskItemSchema[]>(() =>
    this.roadmapService.editableTasks()
  );

  readonly diffSummary = computed(() => this.roadmapService.diffSummary());
  readonly violations = computed(() => this.roadmapService.proposalViolations());
  readonly softOverflowWarnings = computed(() => this.roadmapService.softOverflowWarnings());
  readonly hasSoftOverflow = computed(() => this.roadmapService.hasSoftOverflow());
  readonly hasHardViolations = computed(() => this.roadmapService.hasHardViolations());
  readonly confirmSoftOverflow = computed(() => this.roadmapService.confirmSoftOverflow());
  readonly confirmPartialSchedule = computed(() =>
    this.roadmapService.confirmPartialSchedule()
  );
  readonly feasibility = computed(() => this.roadmapService.feasibility());
  readonly feasibilityStatus = computed(() => this.roadmapService.feasibilityStatus());

  readonly confirmWarnings = computed<boolean>(() =>
    typeof this.roadmapService.confirmWarnings === 'function'
      ? this.roadmapService.confirmWarnings()
      : false
  );

  readonly judgeStatus = computed<'PASSED' | 'NEEDS_REVIEW' | 'REVIEW_PENDING' | 'SKIPPED'>(() => {
    if (typeof this.roadmapService.judgeStatus === 'function') {
      return this.roadmapService.judgeStatus();
    }
    const prop = this.roadmapService.currentProposal();
    const raw = prop?.judge_status ?? prop?.proposal_data?.['judge_status'];
    if (raw === 'NEEDS_REVIEW' || raw === 'REVIEW_PENDING' || raw === 'SKIPPED') {
      return raw;
    }
    return 'PASSED';
  });

  readonly advisoryWarnings = computed<string[]>(() => {
    if (typeof this.roadmapService.advisoryWarnings === 'function') {
      return this.roadmapService.advisoryWarnings();
    }
    return this.roadmapService.currentProposal()?.advisory_warnings ?? [];
  });

  readonly needsJudgeConfirmation = computed<boolean>(() => {
    const status = this.judgeStatus();
    return status === 'REVIEW_PENDING' || status === 'NEEDS_REVIEW';
  });

  readonly unscheduledTasks = computed<ProposedTaskItemSchema[]>(() => {
    return this.roadmapService.unscheduledTasks();
  });

  readonly scheduledTasksCount = computed<number>(() => {
    if (typeof this.roadmapService.scheduledTasksCount === 'function') {
      return this.roadmapService.scheduledTasksCount();
    }
    return this.editableTasks().length;
  });

  readonly unscheduledTasksCount = computed<number>(() => {
    if (typeof this.roadmapService.unscheduledTasksCount === 'function') {
      return this.roadmapService.unscheduledTasksCount();
    }
    return this.unscheduledTasks().length;
  });

  readonly isPartialSchedule = computed<boolean>(() => {
    if (typeof this.roadmapService.isPartialSchedule === 'function') {
      return this.roadmapService.isPartialSchedule();
    }
    return Boolean(
      this.roadmapService.currentProposal()?.is_partial_schedule ||
        this.unscheduledTasksCount() > 0
    );
  });

  readonly availabilitySourceMetadata = computed<Record<string, unknown>>(() => {
    if (typeof this.roadmapService.availabilitySourceMetadata === 'function') {
      return this.roadmapService.availabilitySourceMetadata();
    }
    const prop = this.roadmapService.currentProposal();
    return (
      prop?.availability_source_metadata ??
      (prop?.proposal_data?.['availability_source_metadata'] as Record<string, unknown> | undefined) ??
      {}
    );
  });

  readonly isGoogleCalendarSource = computed<boolean>(() => {
    const meta = this.availabilitySourceMetadata();
    const syncStatus = String(meta['google_sync_status'] ?? '').toUpperCase();
    if (syncStatus === 'FAILED_OR_EXPIRED') {
      return false;
    }
    const sourceType = String(meta['source_type'] ?? '').toUpperCase();
    return (
      sourceType === 'GOOGLE_CALENDAR' ||
      meta['calendar_connected'] === true ||
      syncStatus === 'CONNECTED' ||
      this.calendarService.isConnected() ||
      this.availabilityService.profile()?.calendar_integration_mode === 'CONNECTED'
    );
  });

  readonly availabilitySourceLabel = computed<string>(() => {
    const meta = this.availabilitySourceMetadata();
    if (String(meta['google_sync_status'] ?? '').toUpperCase() === 'FAILED_OR_EXPIRED') {
      return 'Google Calendar gián đoạn (đang dùng giờ rảnh dự phòng)';
    }
    if (this.isGoogleCalendarSource()) {
      const busyCount = Number(meta['busy_intervals_count'] ?? 0);
      return busyCount > 0
        ? `Google Calendar (đã trừ ${busyCount} khoảng bận)`
        : 'Google Calendar (đã đồng bộ)';
    }
    return 'Giờ rảnh cá nhân';
  });

  readonly totalPlannedMinutes = computed<number>(() =>
    this.editableTasks().reduce((sum, t) => sum + (Number(t.estimated_minutes) || 0), 0)
  );

  readonly totalPlannedHours = computed<number>(() =>
    Math.round((this.totalPlannedMinutes() / 60) * 10) / 10
  );

  readonly totalPomodoroBlocks = computed<number>(() =>
    Math.max(0, Math.ceil(this.totalPlannedMinutes() / 25))
  );

  readonly weeklyBreakdown = computed<WeeklyScheduleGroup[]>(() => {
    const tasks = this.editableTasks();
    if (tasks.length === 0) return [];

    const byWeek = new Map<string, Map<string, Array<{
      task: ProposedTaskItemSchema;
      globalIndex: number;
      milestoneTitle: string;
      timeSlotLabel: string;
    }>>>();

    tasks.forEach((task, idx) => {
      const dateKey = task.scheduled_date?.trim() || 'UNASSIGNED';
      const weekKey = dateKey === 'UNASSIGNED' ? 'UNASSIGNED' : getMondayKey(dateKey);
      if (!byWeek.has(weekKey)) {
        byWeek.set(weekKey, new Map());
      }
      const dayMap = byWeek.get(weekKey)!;
      if (!dayMap.has(dateKey)) {
        dayMap.set(dateKey, []);
      }
      dayMap.get(dateKey)!.push({
        task,
        globalIndex: idx,
        milestoneTitle: this.getMilestoneTitle(task),
        timeSlotLabel: this.getTaskTimeSlotLabel(task),
      });
    });

    const sortedWeekKeys = Array.from(byWeek.keys()).sort();
    return sortedWeekKeys.map((weekKey, wIdx) => {
      const dayMap = byWeek.get(weekKey)!;
      const sortedDayKeys = Array.from(dayMap.keys()).sort();
      const days: DailyScheduleGroup[] = sortedDayKeys.map(dateKey => {
        const sessions = dayMap.get(dateKey)!;
        sessions.sort((a, b) => a.timeSlotLabel.localeCompare(b.timeSlotLabel));
        const dayMinutes = sessions.reduce(
          (acc, s) => acc + (Number(s.task.estimated_minutes) || 0),
          0
        );
        return {
          date: dateKey === 'UNASSIGNED' ? 'Chưa gán ngày' : dateKey,
          dayOfWeekLabel:
            dateKey === 'UNASSIGNED' ? 'Chưa phân bổ' : getDayOfWeekLabel(dateKey),
          totalMinutes: dayMinutes,
          totalHours: Math.round((dayMinutes / 60) * 10) / 10,
          sessions,
        };
      });

      const weekMinutes = days.reduce((acc, d) => acc + d.totalMinutes, 0);
      return {
        weekNumber: wIdx + 1,
        weekLabel:
          weekKey === 'UNASSIGNED'
            ? `Nhiệm vụ chưa gán ngày`
            : `Tuần ${wIdx + 1} (từ ${weekKey})`,
        totalMinutes: weekMinutes,
        totalHours: Math.round((weekMinutes / 60) * 10) / 10,
        days,
      };
    });
  });

  readonly averageWeeklyHours = computed<number>(() => {
    const weeksCount = Math.max(1, this.weeklyBreakdown().length);
    return Math.round((this.totalPlannedMinutes() / 60 / weeksCount) * 10) / 10;
  });

  readonly isApplyDisabled = computed<boolean>(() => {
    if (this.roadmapService.saving() || this.roadmapService.isGeneratingStream()) {
      return true;
    }
    if (this.roadmapService.proposalDirty()) {
      return true;
    }
    if (this.hasHardViolations()) {
      return true;
    }
    if (this.hasSoftOverflow() && !this.confirmSoftOverflow()) {
      return true;
    }
    if (this.needsJudgeConfirmation() && !this.confirmWarnings() && !this.confirmSoftOverflow()) {
      return true;
    }
    if (this.feasibilityStatus() === 'INFEASIBLE') {
      return true;
    }
    if (this.feasibilityStatus() === 'PARTIAL' && !this.confirmPartialSchedule()) {
      return true;
    }
    return false;
  });

  setViewMode(mode: 'TIMELINE' | 'CALENDAR'): void {
    this.viewMode.set(mode);
  }

  getPomodoroCount(minutes: number | null | undefined): number {
    return Math.max(1, Math.ceil((Number(minutes) || 25) / 25));
  }

  getMilestoneTitle(task: ProposedTaskItemSchema): string {
    const milestones =
      typeof this.roadmapService.milestones === 'function'
        ? this.roadmapService.milestones()
        : [];
    const editableMs =
      typeof this.roadmapService.editableMilestones === 'function'
        ? this.roadmapService.editableMilestones()
        : [];

    if (task.milestone_id) {
      const found = milestones.find(m => String(m.id) === String(task.milestone_id));
      if (found) return found.title;
      const foundEditable = editableMs.find(
        m => String(m.id ?? m.milestone_id) === String(task.milestone_id)
      );
      if (foundEditable) return foundEditable.title;
    }
    const seq = task.milestone_sequence_order || 1;
    const bySeq = milestones.find(m => m.sequence_order === seq);
    if (bySeq) return bySeq.title;
    return `Chặng #${seq}`;
  }

  getTaskTimeSlotLabel(task: ProposedTaskItemSchema): string {
    const start = extractTimeHHmm(task.scheduled_start, '19:00');
    const end = extractTimeHHmm(task.scheduled_end, '20:00');
    return `${start} – ${end}`;
  }

  getTaskResources(task: ProposedTaskItemSchema): ScheduleViewResourceItem[] {
    const learningRes = task.learning_resources ?? [];
    const altRes = task.resources ?? [];
    const combined = [...learningRes, ...altRes];
    const seen = new Set<string>();
    const result: ScheduleViewResourceItem[] = [];

    for (const item of combined) {
      if (!item || typeof item !== 'object') continue;
      const rec = item as Record<string, unknown>;
      const title = typeof rec['title'] === 'string' ? rec['title'].trim() : '';
      const url = typeof rec['url'] === 'string' ? rec['url'].trim() : '';
      if (!title || !url) continue;
      const key = `${title}|${url}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const resourceType =
        typeof rec['resource_type'] === 'string' && rec['resource_type']
          ? rec['resource_type']
          : typeof rec['type'] === 'string' && rec['type']
            ? rec['type']
            : 'DOCS';
      result.push({ title, url, resourceType });
    }
    return result;
  }

  formatUnscheduledReason(reason: string | null | undefined): string {
    if (!reason) {
      return 'Vượt quá quỹ thời gian rảnh trước ngày đích (deadline).';
    }
    const normalized = reason.trim().toUpperCase();
    if (normalized === 'OVER_CAPACITY' || normalized === 'INSUFFICIENT_AVAILABILITY') {
      return 'Vượt quá quỹ thời gian rảnh trước deadline (OVER_CAPACITY).';
    }
    if (normalized === 'DEADLINE_EXCEEDED') {
      return 'Không còn khung giờ trống hợp lệ trước ngày hoàn thành mục tiêu.';
    }
    return reason;
  }

  onTaskTitleChange(index: number, title: string): void {
    this.roadmapService.updateEditableTask(index, { title });
  }

  onTaskMinutesChange(index: number, value: number | string): void {
    const parsed = Number(value);
    if (!Number.isNaN(parsed) && parsed > 0) {
      this.roadmapService.updateEditableTask(index, {
        estimated_minutes: Math.min(240, Math.max(15, parsed)),
      });
    }
  }

  onTaskDateChange(index: number, scheduled_date: string): void {
    this.roadmapService.updateEditableTask(index, { scheduled_date: scheduled_date || null });
  }

  onTaskTypeChange(index: number, task_type: string): void {
    this.roadmapService.updateEditableTask(index, { task_type });
  }

  onMoveTask(index: number, direction: 'UP' | 'DOWN'): void {
    this.roadmapService.proposalDirty.set(true);
    this.roadmapService.editableTasks.update(list => {
      const targetIndex = direction === 'UP' ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= list.length) {
        return list;
      }
      const copy = [...list];
      const temp = copy[index];
      copy[index] = copy[targetIndex];
      copy[targetIndex] = temp;
      return copy;
    });
  }

  onRemoveTask(index: number): void {
    this.roadmapService.removeEditableTask(index);
  }

  onAddTask(): void {
    this.roadmapService.addEditableTask({
      title: `Phiên học Pomodoro #${this.editableTasks().length + 1}`,
      estimated_minutes: 50,
      task_type: 'PRACTICE',
    });
  }

  onToggleSoftOverflow(checked: boolean): void {
    this.roadmapService.setConfirmSoftOverflow(checked);
  }

  onToggleConfirmWarnings(checked: boolean): void {
    this.roadmapService.setConfirmWarnings?.(checked);
    if (this.hasSoftOverflow()) {
      this.roadmapService.setConfirmSoftOverflow(checked);
    }
  }

  onToggleConfirmPartialSchedule(checked: boolean): void {
    this.roadmapService.setConfirmPartialSchedule(checked);
  }

  onRemoveUnscheduledTask(task: ProposedTaskItemSchema): void {
    const taskIndex = this.editableTasks().findIndex(
      item => item.task_id === task.task_id && item.milestone_id === task.milestone_id
    );
    if (taskIndex >= 0) {
      this.roadmapService.removeEditableTask(taskIndex);
    }
  }

  onRegenerateRoadmapFitCapacity(): void {
    this.regenerateRoadmapFitCapacity.emit();
  }

  onManualScheduleFallback(): void {
    this.manualScheduleFallback.emit();
  }

  onGenerateProposal(): void {
    this.generateProposal.emit();
  }

  onUpdateProposal(): void {
    this.updateProposal.emit();
  }

  onApplyProposal(): void {
    if (this.isApplyDisabled()) return;
    if (this.needsJudgeConfirmation()) {
      this.roadmapService.setConfirmWarnings?.(true);
    }
    this.applyProposal.emit(this.confirmSoftOverflow() || this.confirmWarnings());
  }

  onBack(): void {
    this.backToStep3.emit();
  }
}
