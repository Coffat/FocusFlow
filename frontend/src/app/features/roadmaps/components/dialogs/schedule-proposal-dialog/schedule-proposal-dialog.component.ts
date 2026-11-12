import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoadmapService } from '../../../services/roadmap.service';
import { ProposedTaskItemSchema } from '../../../models/roadmap.model';

@Component({
  selector: 'app-schedule-proposal-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './schedule-proposal-dialog.component.html',
  styleUrl: './schedule-proposal-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScheduleProposalDialogComponent {
  readonly roadmapService = inject(RoadmapService);

  readonly backToStep3 = output<void>();
  readonly generateProposal = output<void>();
  readonly updateProposal = output<void>();
  readonly applyProposal = output<boolean>();

  readonly editableTasks = computed<ProposedTaskItemSchema[]>(() =>
    this.roadmapService.editableTasks()
  );

  readonly diffSummary = computed(() => this.roadmapService.diffSummary());
  readonly violations = computed(() => this.roadmapService.proposalViolations());
  readonly softOverflowWarnings = computed(() => this.roadmapService.softOverflowWarnings());
  readonly hasSoftOverflow = computed(() => this.roadmapService.hasSoftOverflow());
  readonly hasHardViolations = computed(() => this.roadmapService.hasHardViolations());
  readonly confirmSoftOverflow = computed(() => this.roadmapService.confirmSoftOverflow());

  readonly totalPlannedMinutes = computed<number>(() =>
    this.editableTasks().reduce((sum, t) => sum + (Number(t.estimated_minutes) || 0), 0)
  );

  readonly totalPomodoroBlocks = computed<number>(() =>
    Math.max(0, Math.ceil(this.totalPlannedMinutes() / 25))
  );

  readonly isApplyDisabled = computed<boolean>(() => {
    if (this.roadmapService.saving() || this.roadmapService.isGeneratingStream()) {
      return true;
    }
    if (this.hasHardViolations()) {
      return true;
    }
    if (this.hasSoftOverflow() && !this.confirmSoftOverflow()) {
      return true;
    }
    return false;
  });

  getPomodoroCount(minutes: number | null | undefined): number {
    return Math.max(1, Math.ceil((Number(minutes) || 25) / 25));
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

  onGenerateProposal(): void {
    this.generateProposal.emit();
  }

  onUpdateProposal(): void {
    this.updateProposal.emit();
  }

  onApplyProposal(): void {
    if (this.isApplyDisabled()) return;
    this.applyProposal.emit(this.confirmSoftOverflow());
  }

  onBack(): void {
    this.backToStep3.emit();
  }
}
