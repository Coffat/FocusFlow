import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RoadmapService } from '../../../services/roadmap.service';
import {
  ClarificationAnswerItem,
  CreateRoadmapRequest,
  MilestoneUpsertItemSchema,
  PriorKnowledgeLevel,
} from '../../../models/roadmap.model';
import {
  WizardDialogShellComponent,
  WizardSseProgressBannerState,
} from '../../../../../shared/components/wizard-dialog-shell/wizard-dialog-shell.component';
import { GoalSetupDialogComponent } from '../goal-setup-dialog/goal-setup-dialog.component';
import { AiGrillMeDialogComponent } from '../ai-grill-me-dialog/ai-grill-me-dialog.component';
import { MilestoneApprovalDialogComponent } from '../milestone-approval-dialog/milestone-approval-dialog.component';
import { ScheduleProposalDialogComponent } from '../schedule-proposal-dialog/schedule-proposal-dialog.component';

@Component({
  selector: 'app-roadmap-wizard-host',
  standalone: true,
  imports: [
    CommonModule,
    WizardDialogShellComponent,
    GoalSetupDialogComponent,
    AiGrillMeDialogComponent,
    MilestoneApprovalDialogComponent,
    ScheduleProposalDialogComponent,
  ],
  templateUrl: './roadmap-wizard-host.component.html',
  styleUrl: './roadmap-wizard-host.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoadmapWizardHostComponent {
  readonly roadmapService = inject(RoadmapService);

  readonly open = input<boolean>(false);
  readonly initialStep = input<1 | 2 | 3 | 4>(1);
  readonly initialTitle = input<string>('');
  readonly initialLevel = input<PriorKnowledgeLevel>('BEGINNER');
  readonly initialWeeklyHours = input<number>(12);

  readonly closeWizard = output<void>();
  readonly roadmapApplied = output<string>();

  readonly currentStep = signal<1 | 2 | 3 | 4>(1);
  readonly draftTitle = signal<string>('');
  readonly draftLevel = signal<PriorKnowledgeLevel>('BEGINNER');
  readonly draftWeeklyHours = signal<number>(12);
  readonly draftDeadline = signal<string>('');

  readonly shellMaxWidthClass = computed<string>(() => {
    const step = this.currentStep();
    if (step === 1) return 'max-w-[780px]';
    return 'max-w-[1040px]';
  });

  readonly shellErrorMessage = computed<string | null>(() => {
    return typeof this.roadmapService.errorMessage === 'function'
      ? this.roadmapService.errorMessage()
      : null;
  });

  readonly isSaving = computed<boolean>(() => {
    return typeof this.roadmapService.saving === 'function'
      ? this.roadmapService.saving()
      : false;
  });

  readonly shellSseProgress = computed<WizardSseProgressBannerState | null>(() => {
    if (typeof this.roadmapService.sseProgress !== 'function') {
      return null;
    }
    const sse = this.roadmapService.sseProgress();
    if (!sse || !sse.isStreaming) {
      return null;
    }
    return {
      status: 'PROCESSING',
      progressPercent: sse.progress,
      message: sse.message,
      stage: sse.stage,
    };
  });

  constructor() {
    effect(() => {
      const isOpen = this.open();
      const step = this.initialStep();
      const title = this.initialTitle();
      const level = this.initialLevel();
      const hours = this.initialWeeklyHours();
      if (isOpen) {
        this.currentStep.set(step);
        this.draftTitle.set(title);
        this.draftLevel.set(level);
        this.draftWeeklyHours.set(hours);
        this.roadmapService.clearMessages?.();
      }
    });
  }

  onStepChange(step: 1 | 2 | 3 | 4): void {
    this.roadmapService.clearMessages?.();
    this.currentStep.set(step);
  }

  onClose(): void {
    this.roadmapService.closeActiveStream?.();
    this.roadmapService.clearMessages?.();
    this.closeWizard.emit();
  }

  onSaveDraftAndExit(): void {
    this.roadmapService.closeActiveStream?.();
    this.roadmapService.clearMessages?.();
    this.closeWizard.emit();
  }

  // =========================================================================
  // Step 1 -> Step 2 (POST /api/v1/roadmaps)
  // =========================================================================
  onGoalSubmit(payload: CreateRoadmapRequest): void {
    this.draftTitle.set(payload.title);
    this.draftLevel.set((payload.prior_knowledge_level as PriorKnowledgeLevel) || 'BEGINNER');
    this.draftDeadline.set(payload.target_date ?? '');

    this.roadmapService.createRoadmap(payload, () => {
      this.currentStep.set(2);
    });
  }

  // =========================================================================
  // Step 2 -> Step 3 (Clarification Questions / Answers / Skip)
  // =========================================================================
  onGenerateQuestions(): void {
    const goalId = this.roadmapService.selectedRoadmapDetail()?.goal_id;
    if (!goalId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy mục tiêu học tập (Goal ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    this.roadmapService.generateClarificationQuestions(goalId);
  }

  onSubmitInterviewAnswers(answers: ClarificationAnswerItem[]): void {
    const goalId = this.roadmapService.selectedRoadmapDetail()?.goal_id;
    if (!goalId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy mục tiêu học tập (Goal ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    this.roadmapService.submitClarificationAnswers(goalId, answers, () => {
      this.currentStep.set(3);
    });
  }

  onSkipInterview(): void {
    const goalId = this.roadmapService.selectedRoadmapDetail()?.goal_id;
    this.roadmapService.skipClarification(goalId, () => {
      this.currentStep.set(3);
    });
  }

  // =========================================================================
  // Step 3 -> Step 4 (Generate / Save / Approve Level-1 Milestones)
  // =========================================================================
  onGenerateMilestones(additionalContext?: string): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    if (!roadmapId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy lộ trình học tập (Roadmap ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    this.roadmapService.generateMilestonesWithAi(roadmapId, additionalContext);
  }

  onSaveMilestones(items: MilestoneUpsertItemSchema[]): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    if (!roadmapId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy lộ trình học tập (Roadmap ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    this.roadmapService.saveMilestones(roadmapId, items);
  }

  onApproveMilestones(): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    if (!roadmapId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy lộ trình học tập (Roadmap ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    this.roadmapService.approveMilestones(roadmapId, () => {
      this.currentStep.set(4);
    });
  }

  // =========================================================================
  // Step 4 -> Official Schedule (Generate / Update / Apply Proposal)
  // =========================================================================
  onGenerateProposal(): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    if (!roadmapId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy lộ trình học tập (Roadmap ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    this.roadmapService.generateScheduleProposalWithAi(roadmapId);
  }

  onUpdateProposal(): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    if (!roadmapId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy lộ trình học tập (Roadmap ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    const proposalId = this.roadmapService.currentProposal()?.id;
    if (proposalId) {
      this.roadmapService.updateProposal(roadmapId, proposalId);
    } else {
      this.roadmapService.saveManualPlan(roadmapId);
    }
  }

  onApplyProposal(confirmSoftOverflow: boolean): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    const proposalId = this.roadmapService.currentProposal()?.id;
    if (!roadmapId || !proposalId) {
      this.roadmapService.errorMessage.set(
        'Chưa có bản nháp đề xuất lịch học (Proposal ID) trên máy chủ. Vui lòng tạo hoặc lưu bản nháp đề xuất trước khi áp dụng.'
      );
      return;
    }
    this.roadmapService.applyProposal(roadmapId, proposalId, confirmSoftOverflow, () => {
      this.roadmapApplied.emit(roadmapId);
      this.closeWizard.emit();
    });
  }
}
