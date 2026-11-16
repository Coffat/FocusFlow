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
  DraftKnowledgeAttachment,
  MilestoneUpsertItemSchema,
  PlanningStep,
  PriorKnowledgeLevel,
} from '../../../models/roadmap.model';
import {
  WizardDialogShellComponent,
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
  readonly initialStep = input<PlanningStep>(1);
  readonly initialTitle = input<string>('');
  readonly initialLevel = input<PriorKnowledgeLevel>('BEGINNER');
  readonly initialWeeklyHours = input<number>(12);

  readonly closeWizard = output<void>();
  readonly roadmapApplied = output<string>();

  readonly currentStep = signal<PlanningStep>(1);
  readonly draftTitle = signal<string>('');
  readonly draftLevel = signal<PriorKnowledgeLevel>('BEGINNER');
  readonly draftWeeklyHours = signal<number>(12);
  readonly draftDeadline = signal<string>('');
  private readonly resumedClarificationGoalId = signal<string | null>(null);
  private lastSeenProposalCompletedCount = 0;

  readonly shellMaxWidthClass = computed<string>(() => 'max-w-[1040px]');

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
    effect(() => {
      if (!this.open() || this.initialStep() !== 2) return;
      const goalId =
        typeof this.roadmapService.selectedRoadmapDetail === 'function'
          ? this.roadmapService.selectedRoadmapDetail()?.goal_id
          : null;
      if (goalId && this.resumedClarificationGoalId() !== goalId) {
        this.resumedClarificationGoalId.set(goalId);
        this.roadmapService.resumeClarification?.(goalId);
      }
    });
    effect(() => {
      const count =
        typeof this.roadmapService.proposalCompletedCount === 'function'
          ? this.roadmapService.proposalCompletedCount()
          : 0;
      if (count > this.lastSeenProposalCompletedCount) {
        this.lastSeenProposalCompletedCount = count;
        this.currentStep.set(4);
      }
    });
  }

  onStepChange(step: PlanningStep): void {
    this.roadmapService.clearMessages?.();
    this.currentStep.set(step);
  }

  onClose(): void {
    this.roadmapService.closeActiveStream?.();
    this.roadmapService.clearMessages?.();
    this.closeWizard.emit();
  }

  // =========================================================================
  // Step 1 -> Step 2 (POST /api/v1/roadmaps)
  // =========================================================================
  onAttachmentsSelected(items: DraftKnowledgeAttachment[]): void {
    this.roadmapService.draftAttachments?.set(items);
  }

  onGoalSubmit(payload: CreateRoadmapRequest): void {
    this.draftTitle.set(payload.title);
    this.draftLevel.set((payload.prior_knowledge_level as PriorKnowledgeLevel) || 'BEGINNER');
    this.draftDeadline.set(payload.target_date ?? '');

    const pendingAttachments =
      typeof this.roadmapService.draftAttachments === 'function'
        ? this.roadmapService.draftAttachments()
        : [];
    const hasAttachments = pendingAttachments.length > 0;

    this.roadmapService.createRoadmap(
      payload,
      created => {
        if (created?.goal_id && hasAttachments) {
          const upload$ = this.roadmapService.uploadKnowledgeAttachments?.(
            created.goal_id,
            pendingAttachments
          );
          if (upload$) {
            upload$.subscribe({
              complete: () => this.roadmapService.generateClarificationQuestions(created.goal_id),
              error: () => this.roadmapService.generateClarificationQuestions(created.goal_id),
            });
          } else {
            this.roadmapService.generateClarificationQuestions(created.goal_id);
          }
        }
        this.currentStep.set(2);
      },
      { skipAutoClarify: hasAttachments }
    );
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
    this.roadmapService.submitClarificationAnswers(goalId, answers, res => {
      if (res.status === 'WAITING_FOLLOW_UP') {
        this.currentStep.set(2);
        return;
      }
      this.currentStep.set(3);
      this.onGenerateMilestones();
    });
  }

  onClarificationReady(): void {
    this.currentStep.set(3);
    this.onGenerateMilestones();
  }

  onSkipInterview(): void {
    const goalId = this.roadmapService.selectedRoadmapDetail()?.goal_id;
    this.roadmapService.skipClarification(goalId, () => {
      this.currentStep.set(3);
      this.onGenerateMilestones();
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
      this.onGenerateProposal();
    });
  }

  // =========================================================================
  // Step 4: Official Schedule Proposal (Generate / Update / Apply / Manual)
  // =========================================================================
  onGenerateProposal(): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    if (!roadmapId) {
      this.roadmapService.errorMessage.set(
        'Chưa tìm thấy lộ trình học tập (Roadmap ID) trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      return;
    }
    this.currentStep.set(4);
    this.roadmapService.generateScheduleProposalWithAi(roadmapId, () => {
      this.currentStep.set(4);
    });
  }

  onRegenerateRoadmapFitCapacity(): void {
    const roadmapId = this.roadmapService.selectedRoadmapDetail()?.id;
    if (!roadmapId) {
      this.roadmapService.errorMessage.set('Không tìm thấy Roadmap để tạo lại theo quỹ giờ.');
      return;
    }
    this.currentStep.set(3);
    this.roadmapService.generateMilestonesWithAi(
      roadmapId,
      'Thu hẹp phạm vi theo quỹ giờ hiện tại và liệt kê rõ nội dung bị hoãn.',
      'FIT_CAPACITY'
    );
  }

  onManualScheduleFallback(): void {
    this.roadmapService.clearMessages?.();
    this.roadmapService.enableManualPlanningMode?.();
    this.currentStep.set(4);
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
