import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, Subscription, catchError, finalize, of, tap } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { AiSseService, AiStreamChunkEvent } from '../../../core/services/ai-sse.service';
import {
  ApplyScheduleProposalRequest,
  ApplyScheduleProposalResponse,
  ClarificationAnswerItem,
  ClarificationQuestion,
  ClarificationQuestionsResponse,
  ConstraintViolationSchema,
  CreateManualRoadmapPlanRequest,
  CreateRoadmapRequest,
  MilestoneListResponse,
  MilestoneResponse,
  MilestoneUpsertItemSchema,
  PlanningStep,
  PriorKnowledgeLevel,
  ProposedDependencyItemSchema,
  ProposedTaskItemSchema,
  Roadmap,
  RoadmapDetailResponse,
  RoadmapResponse,
  ScheduleProposalResponse,
  SoftOverflowWarningSchema,
  SseProgressState,
  SubmitClarificationAnswersRequest,
  SubmitClarificationAnswersResponse,
  UpdateMilestonesRequest,
  UpdateScheduleProposalRequest,
} from '../models/roadmap.model';

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeTimeInput(raw: unknown, fallback: string): string {
  if (typeof raw !== 'string' || !raw.trim()) {
    return fallback;
  }
  const trimmed = raw.trim();
  // Extract HH:mm from ISO datetime or HH:mm:ss
  const isoMatch = trimmed.match(/T(\d{2}:\d{2})/);
  if (isoMatch) {
    return isoMatch[1];
  }
  const timeMatch = trimmed.match(/^(\d{2}:\d{2})/);
  if (timeMatch) {
    return timeMatch[1];
  }
  return fallback;
}

function buildIsoDateTime(dateStr: string | null | undefined, timeOrIso: string | null | undefined): string | null {
  if (!timeOrIso || !timeOrIso.trim()) {
    return null;
  }
  const trimmed = timeOrIso.trim();
  if (trimmed.includes('T')) {
    return trimmed;
  }
  const effDate = dateStr && dateStr.trim() ? dateStr.trim() : '2026-11-02';
  const hhmm = normalizeTimeInput(trimmed, '19:30');
  return `${effDate}T${hhmm}:00Z`;
}

export function mapRawTasksToProposedItems(
  rawTasks: Record<string, unknown>[] | undefined,
  defaultMilestoneId?: string | null
): ProposedTaskItemSchema[] {
  if (!Array.isArray(rawTasks)) {
    return [];
  }
  return rawTasks.map((t, index) => {
    const scheduledDate =
      typeof t['scheduled_date'] === 'string' && t['scheduled_date']
        ? t['scheduled_date']
        : '2026-11-02';
    const rawStart = typeof t['scheduled_start'] === 'string' ? t['scheduled_start'] : '19:30';
    const rawEnd = typeof t['scheduled_end'] === 'string' ? t['scheduled_end'] : '20:30';
    const prereqs = Array.isArray(t['prerequisite_ids'])
      ? t['prerequisite_ids'].map(p => String(p))
      : [];
    const rawResources = Array.isArray(t['learning_resources']) ? t['learning_resources'] : [];
    const learningResources = rawResources
      .filter((r): r is Record<string, unknown> => typeof r === 'object' && r !== null)
      .map(r => ({
        title: typeof r['title'] === 'string' && r['title'] ? r['title'] : 'Tài liệu hướng dẫn học tập',
        url: typeof r['url'] === 'string' && r['url'] ? r['url'] : 'https://docs.python.org/3/',
        type: typeof r['type'] === 'string' && r['type'] ? r['type'] : 'DOCS',
        description: typeof r['description'] === 'string' ? r['description'] : null,
      }));

    return {
      task_id: typeof t['task_id'] === 'string' ? t['task_id'] : `task-${index + 1}`,
      milestone_id:
        typeof t['milestone_id'] === 'string' && t['milestone_id']
          ? t['milestone_id']
          : (defaultMilestoneId ?? null),
      milestone_sequence_order:
        typeof t['milestone_sequence_order'] === 'number' ? t['milestone_sequence_order'] : index + 1,
      title: typeof t['title'] === 'string' && t['title'] ? t['title'] : `Nhiệm vụ học tập #${index + 1}`,
      description: typeof t['description'] === 'string' ? t['description'] : null,
      task_type: typeof t['task_type'] === 'string' ? t['task_type'] : 'PRACTICE',
      learning_objective:
        typeof t['learning_objective'] === 'string' ? t['learning_objective'] : null,
      completion_criteria:
        typeof t['completion_criteria'] === 'string' ? t['completion_criteria'] : null,
      concept_ids: Array.isArray(t['concept_ids']) ? t['concept_ids'].map(String) : [],
      learning_resources: learningResources,
      estimated_minutes:
        typeof t['estimated_minutes'] === 'number' && !Number.isNaN(t['estimated_minutes'])
          ? t['estimated_minutes']
          : 60,
      scheduled_date: scheduledDate,
      scheduled_start: normalizeTimeInput(rawStart, '19:30'),
      scheduled_end: normalizeTimeInput(rawEnd, '20:30'),
      prerequisite_ids: prereqs,
    };
  });
}

export function mapRawDependenciesToProposedItems(
  rawDeps: Record<string, unknown>[] | undefined
): ProposedDependencyItemSchema[] {
  if (!Array.isArray(rawDeps)) {
    return [];
  }
  return rawDeps
    .filter(d => typeof d['predecessor_id'] === 'string' && typeof d['successor_id'] === 'string')
    .map(d => ({
      predecessor_id: String(d['predecessor_id']),
      successor_id: String(d['successor_id']),
      is_mandatory: d['is_mandatory'] !== false,
    }));
}

@Injectable({
  providedIn: 'root',
})
export class RoadmapService {
  private readonly http = inject(HttpClient);
  private readonly aiSseService = inject(AiSseService);

  private activeSseSubscription: Subscription | null = null;

  // Core Planning Store Signals (WBS 6.3)
  readonly roadmaps = signal<RoadmapResponse[]>([]);
  readonly selectedRoadmapDetail = signal<RoadmapDetailResponse | null>(null);
  readonly milestones = signal<MilestoneResponse[]>([]);
  readonly editableMilestones = signal<MilestoneUpsertItemSchema[]>([]);
  readonly currentProposal = signal<ScheduleProposalResponse | null>(null);
  readonly editableTasks = signal<ProposedTaskItemSchema[]>([]);
  readonly editableDependencies = signal<ProposedDependencyItemSchema[]>([]);

  readonly loading = signal<boolean>(false);
  readonly saving = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  readonly activeStep = signal<PlanningStep>(1);
  readonly manualPlanningMode = signal<boolean>(false);
  readonly confirmSoftOverflow = signal<boolean>(false);
  readonly lastApplyResult = signal<ApplyScheduleProposalResponse | null>(null);

  // AI Diagnostic Clarification Signals (FR-GOAL-002)
  readonly clarificationQuestions = signal<ClarificationQuestion[]>([]);
  readonly isGeneratingQuestions = signal<boolean>(false);
  readonly isSubmittingAnswers = signal<boolean>(false);
  readonly clarificationContext = signal<string | null>(null);

  readonly sseProgress = signal<SseProgressState>({
    stage: 'IDLE',
    progress: 0,
    message: '',
    retryCount: 0,
    isStreaming: false,
  });

  // Legacy signal kept for backward compatibility
  readonly currentRoadmap = signal<Roadmap | null>({
    id: 'rd-01',
    userId: 'usr-01',
    title: 'Chinh phục Lập trình Web Fullstack với FastAPI & Angular 21',
    targetGoal: 'Hoàn thành Khóa luận Tốt nghiệp Đạt Xuất sắc tại HCMUTE',
    status: 'ACTIVE',
    hoursPerWeek: 15,
    createdAt: '2026-10-01T08:00:00Z',
    milestones: [
      {
        id: 'ms-01',
        roadmapId: 'rd-01',
        title: 'Chặng 1: Nền tảng Kiến trúc Lục giác & SRS ISO 29148',
        orderIndex: 1,
        description: 'Hoàn thiện hồ sơ yêu cầu phần mềm và ma trận truy vết',
        totalPomodoros: 20,
        completedPomodoros: 20,
        tasksCount: 6,
      },
      {
        id: 'ms-02',
        roadmapId: 'rd-01',
        title: 'Chặng 2: Xây dựng Backend FastAPI & CSDL PostgreSQL 16',
        orderIndex: 2,
        description: 'Triển khai Domain Entities, Use Cases và Repository Adapters',
        totalPomodoros: 35,
        completedPomodoros: 15,
        tasksCount: 10,
      },
      {
        id: 'ms-03',
        roadmapId: 'rd-01',
        title: 'Chặng 3: Xây dựng Frontend Angular 21 Standalone & PrimeNG',
        orderIndex: 3,
        description: 'Hiện thực giao diện người dùng theo chuẩn WCAG 2.2 AA',
        totalPomodoros: 40,
        completedPomodoros: 5,
        tasksCount: 12,
      },
    ],
  });

  readonly isGeneratingStream = computed<boolean>(() => this.sseProgress().isStreaming);

  // Computed Domain & UI State Signals
  readonly areMilestonesApproved = computed<boolean>(() => {
    const list = this.milestones();
    return (
      list.length > 0 &&
      list.every(
        m => m.status === 'APPROVED' || m.status === 'IN_PROGRESS' || m.status === 'COMPLETED'
      )
    );
  });

  readonly isReadOnlyRoadmap = computed<boolean>(() => {
    const status = this.selectedRoadmapDetail()?.status;
    return status === 'COMPLETED' || status === 'ARCHIVED';
  });

  readonly proposalViolations = computed<ConstraintViolationSchema[]>(() => {
    return this.currentProposal()?.violations ?? [];
  });

  readonly softOverflowWarnings = computed<SoftOverflowWarningSchema[]>(() => {
    return this.currentProposal()?.soft_overflow_warnings ?? [];
  });

  readonly hasSoftOverflow = computed<boolean>(() => {
    const prop = this.currentProposal();
    return Boolean(prop?.has_soft_overflow || (prop?.soft_overflow_warnings?.length ?? 0) > 0);
  });

  readonly hasHardViolations = computed<boolean>(() => {
    const prop = this.currentProposal();
    if (!prop) return false;
    return (prop.violations?.length ?? 0) > 0 || prop.is_valid === false;
  });

  readonly diffSummary = computed<{
    preserved_completed_tasks_count: number;
    replaced_tasks_count: number;
    inserted_tasks_count: number;
  }>(() => {
    const raw = this.currentProposal()?.diff_summary ?? {};
    return {
      preserved_completed_tasks_count: Number(raw['preserved_completed_tasks_count'] ?? 0),
      replaced_tasks_count: Number(raw['replaced_tasks_count'] ?? 0),
      inserted_tasks_count: Number(
        raw['inserted_tasks_count'] ?? this.editableTasks().length
      ),
    };
  });

  readonly canApplyProposal = computed<boolean>(() => {
    const prop = this.currentProposal();
    if (!prop || prop.status !== 'DRAFT') {
      return false;
    }
    if (this.isReadOnlyRoadmap() || this.loading() || this.saving() || this.sseProgress().isStreaming) {
      return false;
    }
    if (this.hasHardViolations()) {
      return false;
    }
    if (this.hasSoftOverflow() && !this.confirmSoftOverflow()) {
      return false;
    }
    return this.editableTasks().length > 0;
  });

  readonly officialTasksGroupedByMilestone = computed<
    Array<{
      milestone: MilestoneResponse;
      tasks: NonNullable<RoadmapDetailResponse['scheduled_tasks']>;
    }>
  >(() => {
    const detail = this.selectedRoadmapDetail();
    const msList = this.milestones();
    const allTasks = detail?.scheduled_tasks ?? [];

    return msList.map(m => ({
      milestone: m,
      tasks: allTasks.filter(t => t.milestone_id === m.id),
    }));
  });

  readonly tasksByMilestone = computed<
    Array<{
      milestone: MilestoneResponse | MilestoneUpsertItemSchema;
      milestoneIndex: number;
      tasks: ProposedTaskItemSchema[];
    }>
  >(() => {
    const msList = this.milestones();
    const editableMs = this.editableMilestones();
    const tasks = this.editableTasks();

    const sourceMilestones = msList.length > 0 ? msList : editableMs;
    if (sourceMilestones.length === 0) {
      if (tasks.length === 0) return [];
      return [
        {
          milestone: {
            id: null,
            milestone_id: null,
            sequence_order: 1,
            title: 'Chặng kiến thức chung',
            description: '',
          },
          milestoneIndex: 0,
          tasks,
        },
      ];
    }

    const assignedTasks = new Set<ProposedTaskItemSchema>();
    const groups = sourceMilestones.map((m, idx) => {
      const mid =
        'id' in m && m.id
          ? String(m.id)
          : 'milestone_id' in m && m.milestone_id
            ? String(m.milestone_id)
            : null;
      const groupTasks = tasks.filter(t => {
        if (mid && t.milestone_id && String(t.milestone_id) === mid) {
          assignedTasks.add(t);
          return true;
        }
        const mSeq = 'sequence_order' in m ? m.sequence_order : idx + 1;
        if (!t.milestone_id && t.milestone_sequence_order === mSeq) {
          assignedTasks.add(t);
          return true;
        }
        return false;
      });
      return {
        milestone: m,
        milestoneIndex: idx,
        tasks: groupTasks,
      };
    });

    const unassigned = tasks.filter(t => !assignedTasks.has(t));
    if (unassigned.length > 0 && groups.length > 0) {
      groups[0].tasks = [...groups[0].tasks, ...unassigned];
    }

    return groups;
  });

  // ===========================================================================
  // State Helpers & Interactive Mutators
  // ===========================================================================

  setActiveStep(step: PlanningStep): void {
    this.activeStep.set(step);
    this.errorMessage.set(null);
  }

  enableManualPlanningMode(): void {
    this.manualPlanningMode.set(true);
    this.activeStep.set(3);
    if (this.editableTasks().length === 0) {
      const firstMilestoneId = this.milestones()[0]?.id ?? null;
      this.editableTasks.set([
        {
          task_id: null,
          milestone_id: firstMilestoneId,
          milestone_sequence_order: 1,
          title: 'Phiên tự học #1',
          description: 'Nghiên cứu lý thuyết và ghi chú trọng tâm',
          task_type: 'PRACTICE',
          learning_objective: 'Nắm vững kiến thức nền tảng',
          completion_criteria: 'Hoàn thành ghi chú và bài tập mẫu',
          concept_ids: [],
          learning_resources: [],
          estimated_minutes: 60,
          scheduled_date: this.selectedRoadmapDetail()?.start_date ?? '2026-11-02',
          scheduled_start: '19:30',
          scheduled_end: '20:30',
          prerequisite_ids: [],
        },
      ]);
    }
  }

  setConfirmSoftOverflow(confirmed: boolean): void {
    this.confirmSoftOverflow.set(confirmed);
  }

  clearMessages(): void {
    this.errorMessage.set(null);
    this.successMessage.set(null);
  }

  closeActiveStream(): void {
    if (this.activeSseSubscription) {
      this.activeSseSubscription.unsubscribe();
      this.activeSseSubscription = null;
    }
    if (this.sseProgress().isStreaming) {
      this.sseProgress.update(prev => ({ ...prev, isStreaming: false }));
    }
  }

  // Interactive Milestone Edits (Step 1)
  addEditableMilestone(title = 'Chặng kiến thức mới', description = ''): void {
    this.editableMilestones.update(list => {
      const nextSeq = list.length + 1;
      return [
        ...list,
        {
          id: null,
          milestone_id: null,
          sequence_order: nextSeq,
          title,
          description,
        },
      ];
    });
  }

  updateEditableMilestone(index: number, patch: Partial<MilestoneUpsertItemSchema>): void {
    this.editableMilestones.update(list =>
      list.map((item, idx) => (idx === index ? { ...item, ...patch } : item))
    );
  }

  removeEditableMilestone(index: number): void {
    this.editableMilestones.update(list =>
      list
        .filter((_, idx) => idx !== index)
        .map((item, idx) => ({
          ...item,
          sequence_order: idx + 1,
        }))
    );
  }

  moveEditableMilestone(index: number, direction: 'UP' | 'DOWN'): void {
    this.editableMilestones.update(list => {
      const targetIndex = direction === 'UP' ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= list.length) {
        return list;
      }
      const copy = [...list];
      const temp = copy[index];
      copy[index] = copy[targetIndex];
      copy[targetIndex] = temp;
      return copy.map((item, idx) => ({
        ...item,
        sequence_order: idx + 1,
      }));
    });
  }

  // Interactive Task Edits (Step 3)
  addEditableTask(partial?: Partial<ProposedTaskItemSchema>): void {
    const defaultMid = this.milestones()[0]?.id ?? null;
    const defaultDate = this.selectedRoadmapDetail()?.start_date ?? '2026-11-02';
    this.editableTasks.update(list => [
      ...list,
      {
        task_id: partial?.task_id ?? null,
        milestone_id: partial?.milestone_id ?? defaultMid,
        milestone_sequence_order: partial?.milestone_sequence_order ?? 1,
        title: partial?.title ?? `Nhiệm vụ học tập #${list.length + 1}`,
        description: partial?.description ?? null,
        task_type: partial?.task_type ?? 'PRACTICE',
        learning_objective: partial?.learning_objective ?? null,
        completion_criteria: partial?.completion_criteria ?? null,
        concept_ids: partial?.concept_ids ?? [],
        learning_resources: partial?.learning_resources ?? [
          {
            title: 'Tài liệu hướng dẫn học tập',
            url: 'https://docs.python.org/3/',
            type: 'DOCS',
            description: 'Tài liệu học tập chính thức từ hệ thống.',
          },
        ],
        estimated_minutes: partial?.estimated_minutes ?? 60,
        scheduled_date: partial?.scheduled_date ?? defaultDate,
        scheduled_start: partial?.scheduled_start ?? '19:30',
        scheduled_end: partial?.scheduled_end ?? '20:30',
        prerequisite_ids: partial?.prerequisite_ids ?? [],
      },
    ]);
  }

  updateEditableTask(index: number, patch: Partial<ProposedTaskItemSchema>): void {
    this.editableTasks.update(list =>
      list.map((item, idx) => (idx === index ? { ...item, ...patch } : item))
    );
  }

  removeEditableTask(index: number): void {
    this.editableTasks.update(list => list.filter((_, idx) => idx !== index));
  }

  addResourceToTask(taskIndex: number, resource: { title: string; url: string; type: string; description?: string | null }): void {
    this.editableTasks.update(list =>
      list.map((task, idx) => {
        if (idx !== taskIndex) return task;
        const currentResources = task.learning_resources ?? [];
        return {
          ...task,
          learning_resources: [
            ...currentResources,
            {
              title: resource.title.trim(),
              url: resource.url.trim(),
              type: resource.type || 'DOCS',
              description: resource.description ?? null,
            },
          ],
        };
      })
    );
  }

  removeResourceFromTask(taskIndex: number, resourceIndex: number): void {
    this.editableTasks.update(list =>
      list.map((task, idx) => {
        if (idx !== taskIndex) return task;
        const currentResources = task.learning_resources ?? [];
        return {
          ...task,
          learning_resources: currentResources.filter((_, rIdx) => rIdx !== resourceIndex),
        };
      })
    );
  }

  private syncMilestonesState(msList: MilestoneResponse[]): void {
    const sorted = [...msList].sort((a, b) => a.sequence_order - b.sequence_order);
    this.milestones.set(sorted);
    this.editableMilestones.set(
      sorted.map((m, idx) => ({
        id: m.id,
        milestone_id: m.id,
        sequence_order: m.sequence_order || idx + 1,
        title: m.title,
        description: m.description ?? '',
      }))
    );
  }

  private syncProposalState(proposal: ScheduleProposalResponse | null): void {
    const previousId = this.currentProposal()?.id;
    this.currentProposal.set(proposal);
    if (!proposal) {
      if (!this.manualPlanningMode()) {
        this.editableTasks.set([]);
        this.editableDependencies.set([]);
      }
      this.confirmSoftOverflow.set(false);
      return;
    }
    if (proposal.id !== previousId) {
      this.confirmSoftOverflow.set(false);
    }
    const defaultMid = this.milestones()[0]?.id ?? null;
    this.editableTasks.set(mapRawTasksToProposedItems(proposal.tasks, defaultMid));
    this.editableDependencies.set(mapRawDependenciesToProposedItems(proposal.dependencies));
  }

  private extractErrorMessage(err: HttpErrorResponse, fallback: string): string {
    const body = err.error as Record<string, unknown> | undefined;
    if (body && typeof body['message'] === 'string') {
      return body['message'];
    }
    if (body && typeof body['detail'] === 'string') {
      return body['detail'];
    }
    return err.message || fallback;
  }

  // ===========================================================================
  // REST & 2-Stage SSE API Methods (UC-07, UC-08, UC-09, UC-10, UC-12)
  // ===========================================================================

  loadRoadmaps(statusFilter?: string): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    const url = statusFilter
      ? `${API_ENDPOINTS.ROADMAPS.BASE}?status=${encodeURIComponent(statusFilter)}`
      : API_ENDPOINTS.ROADMAPS.BASE;

    this.http
      .get<RoadmapResponse[]>(url, { withCredentials: true })
      .pipe(
        tap(list => {
          this.roadmaps.set(list);
          if (list.length > 0 && !this.selectedRoadmapDetail()) {
            this.loadRoadmapDetail(list[0].id);
          }
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể tải danh sách lộ trình học tập.')
          );
          return of([]);
        }),
        finalize(() => {
          this.loading.set(false);
        })
      )
      .subscribe();
  }

  loadRoadmapDetail(roadmapId: string): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.http
      .get<RoadmapDetailResponse>(API_ENDPOINTS.ROADMAPS.DETAIL(roadmapId), {
        withCredentials: true,
      })
      .pipe(
        tap(detail => {
          this.selectedRoadmapDetail.set(detail);
          this.syncMilestonesState(detail.milestones ?? []);
          this.syncProposalState(detail.current_draft_proposal ?? null);

          if (detail.goal?.clarification_context) {
            this.clarificationContext.set(detail.goal.clarification_context);
          }

          if (detail.official_schedule && !detail.current_draft_proposal) {
            this.activeStep.set(4);
          } else if (
            detail.current_draft_proposal ||
            ((detail.milestones?.length ?? 0) > 0 &&
              detail.milestones?.every(m => m.status === 'APPROVED'))
          ) {
            this.activeStep.set(3);
          } else if ((detail.milestones?.length ?? 0) > 0) {
            this.activeStep.set(2);
          } else {
            this.activeStep.set(1);
          }
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể tải chi tiết lộ trình học tập.')
          );
          return of(null);
        }),
        finalize(() => {
          this.loading.set(false);
        })
      )
      .subscribe();
  }

  createRoadmap(payload: CreateRoadmapRequest): void {
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.clarificationQuestions.set([]);
    this.clarificationContext.set(null);

    this.http
      .post<RoadmapResponse>(API_ENDPOINTS.ROADMAPS.BASE, payload, { withCredentials: true })
      .pipe(
        tap(created => {
          this.roadmaps.update(list => [created, ...list.filter(r => r.id !== created.id)]);
          const emptyDetail: RoadmapDetailResponse = {
            ...created,
            milestones: [],
            official_schedule: null,
            scheduled_tasks: [],
            current_draft_proposal: null,
          };
          this.selectedRoadmapDetail.set(emptyDetail);
          this.syncMilestonesState([]);
          this.syncProposalState(null);
          this.activeStep.set(1);
          this.successMessage.set('Đã khởi tạo mục tiêu và lộ trình học tập mới!');

          if (created.goal_id) {
            this.generateClarificationQuestions(created.goal_id);
          }
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể khởi tạo lộ trình học tập.')
          );
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  generateClarificationQuestions(goalId: string): void {
    this.isGeneratingQuestions.set(true);
    this.errorMessage.set(null);

    this.http
      .post<ClarificationQuestionsResponse>(
        API_ENDPOINTS.ROADMAPS.CLARIFY_QUESTIONS(goalId),
        {},
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.clarificationQuestions.set(res.questions ?? []);
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể tạo bộ câu hỏi phỏng vấn chẩn đoán.')
          );
          return of(null);
        }),
        finalize(() => {
          this.isGeneratingQuestions.set(false);
        })
      )
      .subscribe();
  }

  submitClarificationAnswers(goalId: string, answers: ClarificationAnswerItem[]): void {
    this.isSubmittingAnswers.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const body: SubmitClarificationAnswersRequest = {
      answers,
      skipped: false,
    };

    this.http
      .post<SubmitClarificationAnswersResponse>(
        API_ENDPOINTS.ROADMAPS.CLARIFY_ANSWERS(goalId),
        body,
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.clarificationContext.set(res.clarification_context);
          this.clarificationQuestions.set([]);
          this.successMessage.set('Đã lưu chẩn đoán mục tiêu thành công!');
          this.activeStep.set(2);
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể lưu câu trả lời phỏng vấn chẩn đoán.')
          );
          return of(null);
        }),
        finalize(() => {
          this.isSubmittingAnswers.set(false);
        })
      )
      .subscribe();
  }

  skipClarification(goalId?: string): void {
    const targetGoalId = goalId ?? this.selectedRoadmapDetail()?.goal_id;
    const skippedIds = this.clarificationQuestions().map(q => q.question_id);

    if (!targetGoalId) {
      this.activeStep.set(2);
      return;
    }

    this.isSubmittingAnswers.set(true);
    this.http
      .post<SubmitClarificationAnswersResponse>(
        API_ENDPOINTS.ROADMAPS.CLARIFY_SKIP(targetGoalId),
        { skipped_question_ids: skippedIds },
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.clarificationContext.set(res.clarification_context);
          this.clarificationQuestions.set([]);
          this.activeStep.set(2);
        }),
        catchError(() => {
          this.activeStep.set(2);
          return of(null);
        }),
        finalize(() => {
          this.isSubmittingAnswers.set(false);
        })
      )
      .subscribe();
  }

  generateMilestonesWithAi(roadmapId: string, additionalContext?: string): void {
    this.closeActiveStream();
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const idemKey = createIdempotencyKey();
    this.sseProgress.set({
      stage: 'RESERVED',
      progress: 10,
      message: 'Đang giữ chỗ hạn ngạch AI và khởi tạo tiến trình phân rã cột mốc...',
      retryCount: 0,
      isStreaming: true,
    });

    const body = additionalContext ? { additional_context: additionalContext } : {};
    this.aiSseService
      .initiateStreamJob(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(roadmapId), body, idemKey)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          const msg = this.extractErrorMessage(
            err,
            'Không thể khởi tạo tiến trình sinh cột mốc bằng AI.'
          );
          this.errorMessage.set(msg);
          this.sseProgress.set({
            stage: 'FAILED',
            progress: 100,
            message: msg,
            retryCount: 0,
            isStreaming: false,
          });
          return of(null);
        })
      )
      .subscribe(ticket => {
        if (!ticket) {
          return;
        }
        const streamUrl =
          ticket.stream_url || ticket.streamUrl || API_ENDPOINTS.ROADMAPS.JOB_STREAM(ticket.job_id);

        this.activeSseSubscription = this.aiSseService
          .observeJobStream<{ roadmap_id?: string; milestones?: MilestoneResponse[] }>(streamUrl)
          .subscribe({
            next: (evt: AiStreamChunkEvent<{ roadmap_id?: string; milestones?: MilestoneResponse[] }>) => {
              this.handleSseChunk(evt, roadmapId, 'MILESTONES');
            },
            error: () => {
              const failMsg = 'Mất kết nối luồng SSE khi đang sinh cột mốc học tập.';
              this.errorMessage.set(failMsg);
              this.sseProgress.update(prev => ({
                ...prev,
                stage: 'FAILED',
                isStreaming: false,
                message: failMsg,
              }));
            },
          });
      });
  }

  saveMilestones(roadmapId: string, items: MilestoneUpsertItemSchema[] = this.editableMilestones()): void {
    if (items.length === 0) {
      this.errorMessage.set('Vui lòng giữ ít nhất 1 cột mốc trong lộ trình.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const payload: UpdateMilestonesRequest = {
      milestones: items.map((m, idx) => ({
        id: m.id ?? null,
        milestone_id: m.milestone_id ?? m.id ?? null,
        sequence_order: idx + 1,
        title: m.title.trim(),
        description: m.description ?? null,
      })),
    };

    this.http
      .put<MilestoneListResponse>(API_ENDPOINTS.ROADMAPS.MILESTONES(roadmapId), payload, {
        withCredentials: true,
      })
      .pipe(
        tap(res => {
          this.syncMilestonesState(res.milestones ?? []);
          this.selectedRoadmapDetail.update(detail =>
            detail ? { ...detail, milestones: res.milestones } : detail
          );
          this.successMessage.set('Đã lưu chỉnh sửa danh sách cột mốc!');
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể lưu danh sách cột mốc.')
          );
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  approveMilestones(roadmapId: string): void {
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.http
      .post<MilestoneListResponse>(
        API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(roadmapId),
        {},
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.syncMilestonesState(res.milestones ?? []);
          this.selectedRoadmapDetail.update(detail =>
            detail ? { ...detail, milestones: res.milestones } : detail
          );
          this.activeStep.set(3);
          this.successMessage.set(
            'Đã phê duyệt Cột mốc Cấp 1! Bạn có thể sinh Đề xuất Lịch học Chi tiết (Cấp 2).'
          );
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể phê duyệt cột mốc học tập.')
          );
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  generateScheduleProposalWithAi(roadmapId: string): void {
    this.closeActiveStream();
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const idemKey = createIdempotencyKey();
    this.sseProgress.set({
      stage: 'RESERVED',
      progress: 10,
      message: 'Đang giữ chỗ hạn ngạch AI và khởi tạo đề xuất lịch học Cấp 2...',
      retryCount: 0,
      isStreaming: true,
    });

    this.aiSseService
      .initiateStreamJob(API_ENDPOINTS.ROADMAPS.PROPOSALS_GENERATE_JOBS(roadmapId), {}, idemKey)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          const msg = this.extractErrorMessage(
            err,
            'Không thể khởi tạo tiến trình sinh đề xuất lịch học bằng AI.'
          );
          this.errorMessage.set(msg);
          this.sseProgress.set({
            stage: 'FAILED',
            progress: 100,
            message: msg,
            retryCount: 0,
            isStreaming: false,
          });
          return of(null);
        })
      )
      .subscribe(ticket => {
        if (!ticket) {
          return;
        }
        const streamUrl =
          ticket.stream_url || ticket.streamUrl || API_ENDPOINTS.ROADMAPS.JOB_STREAM(ticket.job_id);

        this.activeSseSubscription = this.aiSseService
          .observeJobStream<Record<string, unknown>>(streamUrl)
          .subscribe({
            next: (evt: AiStreamChunkEvent<Record<string, unknown>>) => {
              this.handleSseChunk(evt, roadmapId, 'PROPOSAL');
            },
            error: () => {
              const failMsg = 'Mất kết nối luồng SSE khi đang sinh đề xuất lịch học.';
              this.errorMessage.set(failMsg);
              this.sseProgress.update(prev => ({
                ...prev,
                stage: 'FAILED',
                isStreaming: false,
                message: failMsg,
              }));
            },
          });
      });
  }

  loadCurrentProposal(roadmapId: string): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.http
      .get<ScheduleProposalResponse>(API_ENDPOINTS.ROADMAPS.PROPOSALS_CURRENT(roadmapId), {
        withCredentials: true,
      })
      .pipe(
        tap(proposal => {
          this.syncProposalState(proposal);
          this.selectedRoadmapDetail.update(detail =>
            detail ? { ...detail, current_draft_proposal: proposal } : detail
          );
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không tìm thấy bản nháp đề xuất lịch học hiện hành.')
          );
          return of(null);
        }),
        finalize(() => {
          this.loading.set(false);
        })
      )
      .subscribe();
  }

  private normalizeTasksForRequest(tasks: ProposedTaskItemSchema[]): ProposedTaskItemSchema[] {
    return tasks.map(t => ({
      ...t,
      title: t.title.trim(),
      estimated_minutes: Number(t.estimated_minutes),
      scheduled_start: buildIsoDateTime(t.scheduled_date, t.scheduled_start),
      scheduled_end: buildIsoDateTime(t.scheduled_date, t.scheduled_end),
    }));
  }

  updateProposal(
    roadmapId: string,
    proposalId: string,
    payload?: UpdateScheduleProposalRequest
  ): void {
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const effectivePayload: UpdateScheduleProposalRequest = payload ?? {
      tasks: this.normalizeTasksForRequest(this.editableTasks()),
      dependencies: this.editableDependencies(),
      reject_invalid: false,
    };

    this.http
      .put<ScheduleProposalResponse>(
        API_ENDPOINTS.ROADMAPS.PROPOSAL_UPDATE(roadmapId, proposalId),
        effectivePayload,
        { withCredentials: true }
      )
      .pipe(
        tap(updated => {
          this.syncProposalState(updated);
          this.selectedRoadmapDetail.update(detail =>
            detail ? { ...detail, current_draft_proposal: updated } : detail
          );
          if (updated.is_valid) {
            this.successMessage.set('Đã kiểm định (UC-12) và lưu bản nháp đề xuất lịch học!');
          } else {
            this.errorMessage.set(
              'Bản nháp đã lưu nhưng còn vi phạm ràng buộc cứng. Vui lòng xem chi tiết bên dưới.'
            );
          }
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể cập nhật bản nháp đề xuất lịch học.')
          );
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  saveManualPlan(roadmapId: string, payload?: CreateManualRoadmapPlanRequest): void {
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const effectivePayload: CreateManualRoadmapPlanRequest = payload ?? {
      milestones:
        this.editableMilestones().length > 0
          ? this.editableMilestones().map((m, idx) => ({
              id: m.id ?? null,
              milestone_id: m.milestone_id ?? m.id ?? null,
              sequence_order: idx + 1,
              title: m.title.trim(),
              description: m.description ?? null,
            }))
          : null,
      tasks: this.normalizeTasksForRequest(this.editableTasks()),
      dependencies: this.editableDependencies(),
    };

    this.http
      .post<ScheduleProposalResponse>(
        API_ENDPOINTS.ROADMAPS.PROPOSALS_MANUAL(roadmapId),
        effectivePayload,
        { withCredentials: true }
      )
      .pipe(
        tap(proposal => {
          this.manualPlanningMode.set(false);
          this.syncProposalState(proposal);
          this.loadRoadmapDetail(roadmapId);
          this.activeStep.set(3);
          this.successMessage.set(
            'Đã lưu kế hoạch học tập thủ công (UC-09) không tốn hạn ngạch AI!'
          );
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể lưu kế hoạch học tập thủ công.')
          );
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  applyProposal(
    roadmapId: string,
    proposalId: string,
    confirmSoftOverflow: boolean = this.confirmSoftOverflow()
  ): void {
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const payload: ApplyScheduleProposalRequest = {
      confirm_soft_overflow: confirmSoftOverflow,
    };

    this.http
      .post<ApplyScheduleProposalResponse>(
        API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(roadmapId, proposalId),
        payload,
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.lastApplyResult.set(res);
          this.confirmSoftOverflow.set(false);
          this.activeStep.set(4);
          this.successMessage.set(
            `Đã áp dụng lịch học chính thức thành công (${res.total_sessions} phiên, ${res.total_planned_minutes} phút)!`
          );
          this.loadRoadmapDetail(roadmapId);
          this.loadRoadmaps();
        }),
        catchError((err: HttpErrorResponse) => {
          const body = err.error as Record<string, unknown> | undefined;
          const msg = this.extractErrorMessage(
            err,
            'Không thể áp dụng đề xuất lịch học vào Lịch học Chính thức.'
          );
          this.errorMessage.set(msg);

          if (body && Array.isArray(body['violations'])) {
            const violations = body['violations'] as ConstraintViolationSchema[];
            this.currentProposal.update(prev =>
              prev ? { ...prev, is_valid: false, violations } : prev
            );
          }
          if (body && Array.isArray(body['soft_overflow_warnings'])) {
            const warnings = body['soft_overflow_warnings'] as SoftOverflowWarningSchema[];
            this.currentProposal.update(prev =>
              prev
                ? {
                    ...prev,
                    has_soft_overflow: warnings.length > 0,
                    soft_overflow_warnings: warnings,
                  }
                : prev
            );
          }
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  archiveRoadmap(roadmapId: string): void {
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    this.http
      .post<RoadmapResponse>(
        API_ENDPOINTS.ROADMAPS.ARCHIVE(roadmapId),
        {},
        { withCredentials: true }
      )
      .pipe(
        tap(archived => {
          this.roadmaps.update(list =>
            list.map(r => (r.id === archived.id ? archived : r))
          );
          this.selectedRoadmapDetail.update(detail =>
            detail && detail.id === archived.id
              ? { ...detail, status: archived.status }
              : detail
          );
          this.successMessage.set('Đã lưu trữ lộ trình (ARCHIVED — chế độ chỉ đọc).');
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể lưu trữ lộ trình học tập.')
          );
          return of(null);
        }),
        finalize(() => {
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  private handleSseChunk(
    evt: AiStreamChunkEvent<unknown>,
    roadmapId: string,
    mode: 'MILESTONES' | 'PROPOSAL'
  ): void {
    const text = evt.deltaText ?? evt.delta_text ?? '';
    const isRetry = evt.eventType === 'validation_retry' || typeof evt.retry_attempt === 'number';
    const isCompleted = evt.eventType === 'completed' || evt.stage === 'COMPLETED';
    const isFailed = evt.eventType === 'failed' || evt.stage === 'FAILED';

    this.sseProgress.update(prev => ({
      stage: isCompleted
        ? 'COMPLETED'
        : isFailed
          ? 'FAILED'
          : (evt.stage ?? prev.stage),
      progress: typeof evt.progress === 'number' ? evt.progress : prev.progress,
      message: isFailed ? (evt.error ?? 'Tiến trình AI gặp lỗi.') : (text || prev.message),
      retryCount: isRetry
        ? (evt.retry_attempt ?? prev.retryCount + 1)
        : prev.retryCount,
      isStreaming: !isCompleted && !isFailed,
    }));

    if (isCompleted) {
      if (mode === 'MILESTONES') {
        const payload = evt.payload as { milestones?: MilestoneResponse[] } | undefined;
        if (payload && Array.isArray(payload.milestones)) {
          this.syncMilestonesState(payload.milestones);
        }
        this.successMessage.set(
          'AI đã phân rã xong danh sách Cột mốc! Hãy kiểm tra và bấm Phê duyệt Cột mốc.'
        );
        this.loadRoadmapDetail(roadmapId);
      } else {
        this.successMessage.set(
          'AI đã sinh xong Bản nháp Đề xuất Lịch học (DRAFT) qua cổng kiểm định 3 tầng!'
        );
        this.activeStep.set(3);
        this.loadCurrentProposal(roadmapId);
        this.loadRoadmapDetail(roadmapId);
      }
    } else if (isFailed) {
      this.errorMessage.set(
        evt.error ?? 'Tiến trình sinh lộ trình bằng AI thất bại. Vui lòng thử lại hoặc lập kế hoạch thủ công.'
      );
    }
  }

  // Legacy methods kept for backward compatibility
  pauseRoadmap(id: string): Observable<Roadmap> {
    return this.http
      .post<Roadmap>(API_ENDPOINTS.ROADMAPS.PAUSE(id), {}, { withCredentials: true })
      .pipe(tap(updated => this.currentRoadmap.set(updated)));
  }

  resumeRoadmap(id: string): Observable<Roadmap> {
    return this.http
      .post<Roadmap>(API_ENDPOINTS.ROADMAPS.RESUME(id), {}, { withCredentials: true })
      .pipe(tap(updated => this.currentRoadmap.set(updated)));
  }
}

export { RoadmapService as RoadmapPlanningStore };
