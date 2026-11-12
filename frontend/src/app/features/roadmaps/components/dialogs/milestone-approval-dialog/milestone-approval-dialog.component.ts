import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoadmapService } from '../../../services/roadmap.service';
import { MilestoneUpsertItemSchema } from '../../../models/roadmap.model';

@Component({
  selector: 'app-milestone-approval-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './milestone-approval-dialog.component.html',
  styleUrl: './milestone-approval-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MilestoneApprovalDialogComponent {
  readonly roadmapService = inject(RoadmapService);

  readonly targetCapacityHours = input<number>(120);

  readonly backToStep2 = output<void>();
  readonly generateMilestones = output<string | undefined>();
  readonly saveMilestones = output<MilestoneUpsertItemSchema[]>();
  readonly approveMilestones = output<void>();

  readonly additionalContext = signal<string>('');
  readonly milestoneEstimatedHoursMap = signal<Record<number, number>>({});

  readonly editableMilestones = computed<MilestoneUpsertItemSchema[]>(() =>
    this.roadmapService.editableMilestones()
  );

  readonly sseProgress = computed(() => this.roadmapService.sseProgress());

  readonly totalEstimatedHours = computed<number>(() => {
    const list = this.editableMilestones();
    const hoursMap = this.milestoneEstimatedHoursMap();
    return list.reduce((sum, _, idx) => sum + (hoursMap[idx] ?? 24), 0);
  });

  getMilestoneHours(index: number): number {
    return this.milestoneEstimatedHoursMap()[index] ?? 24;
  }

  onMilestoneHoursChange(index: number, value: number | string): void {
    const parsed = Number(value);
    if (!Number.isNaN(parsed) && parsed > 0) {
      this.milestoneEstimatedHoursMap.update(prev => ({
        ...prev,
        [index]: Math.min(200, Math.max(1, parsed)),
      }));
    }
  }

  onTitleChange(index: number, title: string): void {
    this.roadmapService.updateEditableMilestone(index, { title });
  }

  onDescriptionChange(index: number, description: string): void {
    this.roadmapService.updateEditableMilestone(index, { description });
  }

  onMoveMilestone(index: number, direction: 'UP' | 'DOWN'): void {
    this.roadmapService.moveEditableMilestone(index, direction);
  }

  onRemoveMilestone(index: number): void {
    this.roadmapService.removeEditableMilestone(index);
  }

  onAddMilestone(): void {
    const nextNum = this.editableMilestones().length + 1;
    this.roadmapService.addEditableMilestone(
      `Cột mốc #${nextNum}: Chuyên đề học tập mới`,
      'Nắm vững lý thuyết trọng tâm và hoàn thành bài tập thực hành.'
    );
  }

  onGenerateMilestones(): void {
    const ctx = this.additionalContext().trim();
    this.generateMilestones.emit(ctx || undefined);
  }

  onSaveMilestones(): void {
    this.saveMilestones.emit(this.editableMilestones());
  }

  onApproveMilestones(): void {
    this.approveMilestones.emit();
  }

  onBack(): void {
    this.backToStep2.emit();
  }
}
