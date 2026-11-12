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
import { ActivatedRoute, RouterLink } from '@angular/router';
import { RoadmapService } from '../../services/roadmap.service';
import { AvailabilityService } from '../../../../core/services/availability.service';
import { BadgeDirective, BadgeVariant } from '../../../../shared/ui/badge/badge.directive';
import {
  ClarificationAnswerItem,
  PriorKnowledgeLevel,
  ProposedTaskItemSchema,
} from '../../models/roadmap.model';

@Component({
  selector: 'app-roadmap-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    BadgeDirective,
  ],
  templateUrl: './roadmap-page.component.html',
  styleUrl: './roadmap-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoadmapPageComponent implements OnInit {
  readonly roadmapService = inject(RoadmapService);
  readonly availabilityService = inject(AvailabilityService);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  readonly Number = Number;

  // Local Form Signals for Creating a New Goal & Roadmap
  readonly showCreateForm = signal<boolean>(false);
  readonly showOnboardingModal = signal<boolean>(false);
  readonly newGoalTitle = signal<string>('');
  readonly newGoalDescription = signal<string>('');
  readonly newPriorKnowledgeLevel = signal<PriorKnowledgeLevel>('BEGINNER');
  readonly newStartDate = signal<string>('');
  readonly newTargetDate = signal<string>('');
  readonly resourceEditorTaskIndex = signal<number | null>(null);
  readonly resourceTitle = signal<string>('');
  readonly resourceUrl = signal<string>('');
  readonly resourceError = signal<string | null>(null);

  // AI Diagnostic Clarification Questionnaire State (FR-GOAL-002)
  readonly userAnswers = signal<Record<string, string>>({});

  readonly knowledgeLevels: Array<{ value: PriorKnowledgeLevel; label: string; desc: string }> = [
    { value: 'BEGINNER', label: 'Mới bắt đầu', desc: 'Chưa có kiến thức nền tảng, cần đi từ số 0' },
    { value: 'INTERMEDIATE', label: 'Đã có nền tảng', desc: 'Đã nắm cơ bản, muốn thực hành & áp dụng' },
    { value: 'ADVANCED', label: 'Nâng cao chuyên sâu', desc: 'Đã có kinh nghiệm, tập trung tối ưu & chuyên sâu' },
  ];

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
    this.availabilityService.loadMyAvailability();

    // 1. Check Route Param (:id)
    const routeId = this.route.snapshot.paramMap.get('id');
    if (routeId && routeId !== 'new') {
      this.roadmapService.loadRoadmapDetail(routeId);
    } else {
      this.roadmapService.loadRoadmaps();
    }

    if (routeId === 'new') {
      this.showCreateForm.set(true);
      this.roadmapService.setActiveStep(1);
    }

    // 2. Check Query Param (?goal=...)
    const queryGoal = this.route.snapshot.queryParamMap.get('goal');
    if (queryGoal) {
      this.newGoalTitle.set(queryGoal);
      const lower = queryGoal.toLowerCase();
      const now = new Date();
      if (lower.includes('fastapi')) {
        this.newPriorKnowledgeLevel.set('INTERMEDIATE');
        const targetDate = new Date(now.getTime() + 12 * 7 * 24 * 60 * 60 * 1000);
        this.newTargetDate.set(targetDate.toISOString().split('T')[0]);
      } else if (lower.includes('aws')) {
        this.newPriorKnowledgeLevel.set('BEGINNER');
        const targetDate = new Date(now.getTime() + 8 * 7 * 24 * 60 * 60 * 1000);
        this.newTargetDate.set(targetDate.toISOString().split('T')[0]);
      } else if (lower.includes('ielts')) {
        this.newPriorKnowledgeLevel.set('INTERMEDIATE');
        const targetDate = new Date(now.getTime() + 10 * 7 * 24 * 60 * 60 * 1000);
        this.newTargetDate.set(targetDate.toISOString().split('T')[0]);
      }
      if (!this.newStartDate()) {
        this.newStartDate.set(now.toISOString().split('T')[0]);
      }
      this.showCreateForm.set(true);
      this.roadmapService.setActiveStep(1);
    }

    // React to route parameter changes if navigation happens within component
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id && id !== 'new' && id !== this.roadmapService.selectedRoadmapDetail()?.id) {
        this.roadmapService.loadRoadmapDetail(id);
      }
    });
  }

  toggleCreateForm(): void {
    if (this.showCreateForm()) {
      this.showCreateForm.set(false);
      return;
    }

    const checkAndOpen = () => {
      if (!this.availabilityService.hasConfiguredAvailability()) {
        this.showOnboardingModal.set(true);
      } else {
        this.showCreateForm.set(true);
      }
    };

    if (!this.availabilityService.profile()) {
      this.availabilityService.loadMyAvailability(() => {
        checkAndOpen();
      });
    } else {
      checkAndOpen();
    }
  }

  closeOnboardingModal(): void {
    this.showOnboardingModal.set(false);
  }

  onConnectGoogleCalendar(): void {
    this.availabilityService.setCalendarIntegrationMode('CONNECTED');
    this.availabilityService.saveMyAvailability((res) => {
      if (res) {
        this.roadmapService.successMessage.set('Đã liên kết Google Calendar thành công!');
        this.showOnboardingModal.set(false);
        this.showCreateForm.set(true);
      }
    });
  }

  onSelectPreset(presetId: 'BUSY_PRO' | 'UNI_STUDENT' | 'BOOTCAMPER'): void {
    this.availabilityService.applyPreset(presetId);
    this.availabilityService.saveMyAvailability((res) => {
      if (res) {
        this.roadmapService.successMessage.set('Đã áp dụng mẫu quỹ giờ rảnh thành công!');
        this.showOnboardingModal.set(false);
        this.showCreateForm.set(true);
      }
    });
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
    if (!this.availabilityService.hasConfiguredAvailability()) {
      this.showOnboardingModal.set(true);
      return;
    }
    this.roadmapService.createRoadmap({
      title,
      description: this.newGoalDescription().trim() || null,
      goal_title: title,
      goal_description: this.newGoalDescription().trim() || null,
      prior_knowledge_level: this.newPriorKnowledgeLevel(),
      start_date: this.newStartDate() || null,
      target_date: this.newTargetDate() || null,
    });
    this.newGoalTitle.set('');
    this.newGoalDescription.set('');
    this.newPriorKnowledgeLevel.set('BEGINNER');
    this.userAnswers.set({});
    this.showCreateForm.set(false);
  }

  onSelectOption(questionId: string, option: string): void {
    this.userAnswers.update(curr => ({ ...curr, [questionId]: option }));
  }

  onAnswerTextChange(questionId: string, text: string): void {
    this.userAnswers.update(curr => ({ ...curr, [questionId]: text }));
  }

  onSubmitClarification(goalId: string): void {
    const questions = this.roadmapService.clarificationQuestions();
    const map = this.userAnswers();
    const answers: ClarificationAnswerItem[] = questions.map(q => ({
      question_id: q.question_id,
      question_text: q.text,
      answer: (map[q.question_id] || '').trim() || (q.options?.[0] ?? 'Không có ý kiến cụ thể'),
    }));
    this.roadmapService.submitClarificationAnswers(goalId, answers);
  }

  onSkipClarification(): void {
    const goalId = this.selectedDetail()?.goal_id;
    this.roadmapService.skipClarification(goalId);
  }

  onTriggerClarification(goalId: string): void {
    this.roadmapService.generateClarificationQuestions(goalId);
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

  getTaskGlobalIndex(task: ProposedTaskItemSchema): number {
    return this.roadmapService.editableTasks().indexOf(task);
  }

  onAddTaskToMilestone(milestoneId?: string | null, sequenceOrder?: number): void {
    const defaultDate = this.selectedDetail()?.start_date ?? null;
    this.roadmapService.addEditableTask({
      milestone_id: milestoneId ?? null,
      milestone_sequence_order: sequenceOrder ?? 1,
      title: `Nhiệm vụ mới chặng #${sequenceOrder ?? 1}`,
      task_type: 'PRACTICE',
      estimated_minutes: 60,
      scheduled_date: defaultDate,
      scheduled_start: '19:30',
      scheduled_end: '20:30',
      learning_objective: 'Nắm vững kiến thức trọng tâm và thực hành ứng dụng',
      completion_criteria: 'Hoàn thành bài tập mẫu và giải thích được nguyên lý',
      learning_resources: [],
    });
  }

  onConfirmTasksToStep4(roadmapId: string): void {
    this.roadmapService.setActiveStep(4);
    const prop = this.roadmapService.currentProposal();
    if (prop && this.roadmapService.proposalDirty()) {
      this.roadmapService.updateProposal(roadmapId, prop.id);
    }
  }

  onAddQuickResource(taskGlobalIndex: number): void {
    this.resourceEditorTaskIndex.set(taskGlobalIndex);
    this.resourceTitle.set('');
    this.resourceUrl.set('');
    this.resourceError.set(null);
  }

  onSaveResource(): void {
    const taskIndex = this.resourceEditorTaskIndex();
    const title = this.resourceTitle().trim();
    const url = this.resourceUrl().trim();
    if (taskIndex === null || !title) {
      this.resourceError.set('Vui lòng nhập tên tài liệu.');
      return;
    }
    try {
      const parsed = new URL(url);
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('invalid protocol');
    } catch {
      this.resourceError.set('Vui lòng nhập URL http hoặc https hợp lệ.');
      return;
    }
    this.roadmapService.addResourceToTask(taskIndex, { title, url, type: 'DOCS' });
    this.resourceEditorTaskIndex.set(null);
    this.resourceError.set(null);
  }

  getBlockTaskTitle(taskId: string): string {
    return this.roadmapService.editableTasks().find(task => task.task_id === taskId)?.title ?? 'Nhiệm vụ học tập';
  }

  onRemoveResource(taskGlobalIndex: number, resIndex: number): void {
    this.roadmapService.removeResourceFromTask(taskGlobalIndex, resIndex);
  }

  getTaskTypeLabel(type: string | null | undefined): string {
    switch (type) {
      case 'THEORY':
        return 'Lý thuyết (THEORY)';
      case 'PRACTICE':
        return 'Thực hành (PRACTICE)';
      case 'REVIEW':
        return 'Ôn tập (REVIEW)';
      case 'PROJECT':
        return 'Dự án (PROJECT)';
      default:
        return 'Thực hành (PRACTICE)';
    }
  }

  getResourceTypeBadgeVariant(type: string): BadgeVariant {
    switch (type) {
      case 'DOCS':
        return 'default';
      case 'TUTORIAL':
        return 'success';
      case 'VIDEO':
        return 'outline';
      case 'BOOK':
        return 'secondary';
      case 'PRACTICE':
        return 'destructive';
      default:
        return 'secondary';
    }
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
