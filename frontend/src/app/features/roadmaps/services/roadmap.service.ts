import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, Subscription, catchError, finalize, forkJoin, map, of, tap } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import {
  AiSseService,
  AiStreamChunkEvent,
  SseStreamError,
} from '../../../core/services/ai-sse.service';
import {
  ApplyScheduleProposalRequest,
  ApplyScheduleProposalResponse,
  ApproveMilestonesRequest,
  ClarificationAnswerItem,
  ClarificationQuestion,
  ClarificationQuestionsResponse,
  ConstraintViolationSchema,
  CreateKnowledgeUrlRequest,
  CreateManualRoadmapPlanRequest,
  CreateRoadmapRequest,
  DraftKnowledgeAttachment,
  FeasibilityScopeItem,
  KnowledgeSourceResponse,
  MilestoneGenerationRequest,
  MilestoneListResponse,
  MilestoneResponse,
  MilestoneUpsertItemSchema,
  PlanningConflictResponse,
  PlanningStep,
  PreliminaryFeasibility,
  PriorKnowledgeLevel,
  ProposedDependencyItemSchema,
  ProposedTaskItemSchema,
  Roadmap,
  RoadmapDetailResponse,
  RoadmapResponse,
  ScheduleProposalResponse,
  ScopeApprovalConflict,
  SoftOverflowWarningSchema,
  SseProgressState,
  SubmitClarificationAnswersRequest,
  SubmitClarificationAnswersResponse,
  UpdateMilestonesRequest,
  UpdateScheduleProposalRequest,
  parsePreliminaryFeasibility,
} from '../models/roadmap.model';

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function pickNonEmpty(...candidates: Array<string | null | undefined>): string {
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }
  return '';
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
  if (!dateStr?.trim()) return null;
  const effDate = dateStr.trim();
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
        : null;
    const rawStart = typeof t['scheduled_start'] === 'string' ? t['scheduled_start'] : null;
    const rawEnd = typeof t['scheduled_end'] === 'string' ? t['scheduled_end'] : null;
    const prereqs = Array.isArray(t['prerequisite_ids'])
      ? t['prerequisite_ids'].map(p => String(p))
      : [];
    const rawResources = Array.isArray(t['learning_resources'])
      ? t['learning_resources']
      : Array.isArray(t['resources'])
        ? t['resources']
        : [];
    const learningResources = rawResources
      .filter((r): r is Record<string, unknown> =>
        typeof r === 'object' && r !== null &&
        typeof (r as Record<string, unknown>)['title'] === 'string' &&
        typeof (r as Record<string, unknown>)['url'] === 'string' &&
        Boolean((r as Record<string, unknown>)['title']) &&
        Boolean((r as Record<string, unknown>)['url'])
      )
      .map(r => {
        const resType =
          typeof r['type'] === 'string' && r['type']
            ? r['type']
            : typeof r['resource_type'] === 'string' && r['resource_type']
              ? r['resource_type']
              : 'DOCS';
        return {
          title: String(r['title']),
          url: String(r['url']),
          type: resType,
          description: typeof r['description'] === 'string' ? r['description'] : null,
        };
      });

    const unscheduledReason =
      typeof t['unscheduled_reason'] === 'string' && t['unscheduled_reason']
        ? t['unscheduled_reason']
        : null;

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
      resources: learningResources.map(r => ({
        title: r.title,
        url: r.url,
        resource_type: r.type,
        type: r.type,
        description: r.description,
      })),
      estimated_minutes:
        typeof t['estimated_minutes'] === 'number' && !Number.isNaN(t['estimated_minutes'])
          ? t['estimated_minutes']
          : 60,
      scheduled_date: scheduledDate,
      scheduled_start: rawStart ? normalizeTimeInput(rawStart, '') : null,
      scheduled_end: rawEnd ? normalizeTimeInput(rawEnd, '') : null,
      unscheduled_reason: unscheduledReason,
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
  readonly proposalDirty = signal(false);
  readonly editableTasks = signal<ProposedTaskItemSchema[]>([]);
  readonly editableDependencies = signal<ProposedDependencyItemSchema[]>([]);

  readonly loading = signal<boolean>(false);
  readonly saving = signal<boolean>(false);
  readonly isApprovingMilestones = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  private readonly _lastErrorCode = signal<string | null>(null);
  private readonly _lastFailedStage = signal<'MILESTONES' | 'PROPOSAL' | null>(null);
  readonly lastErrorCode = this._lastErrorCode.asReadonly();
  readonly lastFailedStage = this._lastFailedStage.asReadonly();

  private readonly _lastMilestoneGenerationParams = signal<{
    roadmapId: string;
    additionalContext?: string;
    generationStrategy: 'FULL_SCOPE' | 'FIT_CAPACITY';
  } | null>(null);
  readonly lastMilestoneGenerationParams = this._lastMilestoneGenerationParams.asReadonly();
  private lastFailedRoadmapId: string | null = null;
  private readonly applyIdempotencyKeys = new Map<string, string>();
  readonly freshCalendarConflicts = signal<Record<string, unknown>[]>([]);

  readonly preliminaryFeasibility = signal<PreliminaryFeasibility | null>(null);
  readonly scopeApprovalConflict = signal<ScopeApprovalConflict | null>(null);

  readonly activeStep = signal<PlanningStep>(1);
  readonly manualPlanningMode = signal<boolean>(false);
  readonly confirmSoftOverflow = signal<boolean>(false);
  readonly confirmWarnings = signal<boolean>(false);
  readonly confirmPartialSchedule = signal<boolean>(false);
  readonly proposalCompletedCount = signal<number>(0);
  readonly lastApplyResult = signal<ApplyScheduleProposalResponse | null>(null);
  private onProposalCompletedCallback: (() => void) | null = null;

  // AI Diagnostic Clarification Signals (FR-GOAL-002)
  readonly clarificationQuestions = signal<ClarificationQuestion[]>([]);
  readonly isGeneratingQuestions = signal<boolean>(false);
  readonly isSubmittingAnswers = signal<boolean>(false);
  readonly clarificationContext = signal<string | null>(null);
  readonly clarificationSessionId = signal<string | null>(null);
  readonly clarificationRound = signal<number>(1);
  readonly clarificationStatus = signal<string>('ANALYZING');
  readonly clarificationInformationGaps = signal<Record<string, unknown>[]>([]);
  readonly clarificationNextTurnQuotaCost = signal<number>(0);
  readonly draftAttachments = signal<DraftKnowledgeAttachment[]>([]);
  readonly knowledgeSources = signal<KnowledgeSourceResponse[]>([]);

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

  // Preliminary Feasibility & FIT_CAPACITY Scope Signals (DEF-05)
  readonly scopeProposalVersion = computed<number | null>(() => {
    const pf = this.preliminaryFeasibility();
    if (pf && typeof pf.scope_proposal_version === 'number') {
      return pf.scope_proposal_version;
    }
    return this.scopeApprovalConflict()?.scope_proposal_version ?? null;
  });

  readonly keptScope = computed<FeasibilityScopeItem[]>(() => {
    return this.preliminaryFeasibility()?.kept_scope ?? [];
  });

  readonly deferredScope = computed<FeasibilityScopeItem[]>(() => {
    return this.preliminaryFeasibility()?.deferred_scope ?? [];
  });

  readonly isPreliminaryUnschedulable = computed<boolean>(() => {
    return (
      this.preliminaryFeasibility()?.status === 'PRELIMINARY_UNSCHEDULABLE' ||
      this.scopeApprovalConflict()?.code === 'PRELIMINARY_UNSCHEDULABLE'
    );
  });

  readonly isFitCapacityApproved = computed<boolean>(() => {
    const pf = this.preliminaryFeasibility();
    if (!pf || pf.status !== 'FIT_CAPACITY_REQUIRES_APPROVAL') {
      return false;
    }
    if (pf.scope_approval_status !== 'APPROVED_BY_LEARNER') {
      return false;
    }
    if (pf.approved_scope_version !== null && pf.approved_scope_version !== undefined) {
      return pf.approved_scope_version === pf.scope_proposal_version;
    }
    return true;
  });

  readonly requiresScopeApproval = computed<boolean>(() => {
    if (this.scopeApprovalConflict()?.code === 'SCOPE_APPROVAL_REQUIRED') {
      return true;
    }
    const pf = this.preliminaryFeasibility();
    if (!pf) {
      return false;
    }
    if (pf.status !== 'FIT_CAPACITY_REQUIRES_APPROVAL') {
      return false;
    }
    return !this.isFitCapacityApproved();
  });

  // Computed Domain & UI State Signals
  readonly areMilestonesApproved = computed<boolean>(() => {
    const list = this.milestones();
    if (list.length === 0) {
      return false;
    }
    if (this.isPreliminaryUnschedulable() || this.requiresScopeApproval()) {
      return false;
    }
    if (this.isFitCapacityApproved()) {
      return list.some(
        m => m.status === 'APPROVED' || m.status === 'IN_PROGRESS' || m.status === 'COMPLETED'
      );
    }
    return list.every(
      m => m.status === 'APPROVED' || m.status === 'IN_PROGRESS' || m.status === 'COMPLETED'
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

  readonly judgeStatus = computed<'PASSED' | 'NEEDS_REVIEW' | 'REVIEW_PENDING' | 'SKIPPED'>(() => {
    const prop = this.currentProposal();
    const raw = prop?.judge_status ?? prop?.proposal_data?.['judge_status'];
    if (raw === 'NEEDS_REVIEW' || raw === 'REVIEW_PENDING' || raw === 'SKIPPED') {
      return raw;
    }
    if (raw === 'FAILED' || raw === 'ERROR') {
      return 'NEEDS_REVIEW';
    }
    return 'PASSED';
  });

  readonly advisoryWarnings = computed<string[]>(() => {
    const prop = this.currentProposal();
    if (Array.isArray(prop?.advisory_warnings) && prop.advisory_warnings.length > 0) {
      return prop.advisory_warnings.map(String);
    }
    const raw = prop?.proposal_data?.['advisory_warnings'];
    return Array.isArray(raw) ? raw.map(String) : [];
  });

  readonly needsJudgeConfirmation = computed<boolean>(() => {
    const status = this.judgeStatus();
    return status === 'REVIEW_PENDING' || status === 'NEEDS_REVIEW';
  });

  readonly unscheduledTasks = computed<ProposedTaskItemSchema[]>(() => {
    const prop = this.currentProposal();
    if (!prop) return [];
    const rawList =
      (Array.isArray(prop.unscheduled_tasks) ? prop.unscheduled_tasks : null) ??
      (Array.isArray(prop.proposal_data?.['unscheduled_tasks'])
        ? (prop.proposal_data?.['unscheduled_tasks'] as Record<string, unknown>[])
        : []);
    if (rawList.length > 0) {
      return mapRawTasksToProposedItems(
        rawList as unknown as Record<string, unknown>[],
        this.milestones()[0]?.id ?? null
      );
    }
    return this.editableTasks().filter(t => Boolean(t.unscheduled_reason));
  });

  readonly unscheduledTasksCount = computed<number>(() => {
    const prop = this.currentProposal();
    const listLen = this.unscheduledTasks().length;
    if (listLen > 0) return listLen;
    if (typeof prop?.unscheduled_tasks_count === 'number') {
      return prop.unscheduled_tasks_count;
    }
    const rawCount = prop?.proposal_data?.['unscheduled_tasks_count'];
    return typeof rawCount === 'number' ? rawCount : 0;
  });

  readonly scheduledTasksCount = computed<number>(() => {
    const prop = this.currentProposal();
    const tasks = this.editableTasks();
    if (tasks.length > 0) {
      const withDate = tasks.filter(t => Boolean(t.scheduled_date)).length;
      if (withDate > 0) return withDate;
    }
    if (typeof prop?.scheduled_tasks_count === 'number' && prop.scheduled_tasks_count > 0) {
      return prop.scheduled_tasks_count;
    }
    const rawCount = prop?.proposal_data?.['scheduled_tasks_count'];
    if (typeof rawCount === 'number' && rawCount > 0) {
      return rawCount;
    }
    return tasks.length;
  });

  readonly isPartialSchedule = computed<boolean>(() => {
    const prop = this.currentProposal();
    return Boolean(
      prop?.is_partial_schedule ||
        prop?.proposal_data?.['is_partial_schedule'] ||
        prop?.schedule_completeness_status === 'PARTIAL' ||
        this.feasibilityStatus() === 'PARTIAL' ||
        this.unscheduledTasksCount() > 0
    );
  });

  readonly feasibility = computed(() => this.currentProposal()?.feasibility ?? null);

  readonly feasibilityStatus = computed<'FEASIBLE' | 'PARTIAL' | 'INFEASIBLE'>(() => {
    const status = this.feasibility()?.status;
    if (status === 'PARTIAL' || status === 'INFEASIBLE') return status;
    return 'FEASIBLE';
  });

  readonly availabilitySourceMetadata = computed<Record<string, unknown>>(() => {
    const prop = this.currentProposal();
    const meta =
      prop?.availability_source_metadata ??
      (prop?.proposal_data?.['availability_source_metadata'] as Record<string, unknown> | undefined);
    return meta && typeof meta === 'object' ? meta : {};
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
    if (this.needsJudgeConfirmation() && !this.confirmWarnings() && !this.confirmSoftOverflow()) {
      return false;
    }
    if (this.feasibilityStatus() === 'INFEASIBLE') {
      return false;
    }
    if ((this.isPartialSchedule() || this.feasibilityStatus() === 'PARTIAL') && !this.confirmPartialSchedule()) {
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
    this._lastErrorCode.set(null);
    this._lastFailedStage.set(null);
    this.freshCalendarConflicts.set([]);
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
          scheduled_date: this.selectedRoadmapDetail()?.start_date ?? null,
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

  setConfirmWarnings(confirmed: boolean): void {
    this.confirmWarnings.set(confirmed);
  }

  setConfirmPartialSchedule(confirmed: boolean): void {
    this.confirmPartialSchedule.set(confirmed);
  }

  clearMessages(): void {
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this._lastErrorCode.set(null);
    this._lastFailedStage.set(null);
    this.freshCalendarConflicts.set([]);
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
    this.proposalDirty.set(true);
    const defaultMid = this.milestones()[0]?.id ?? null;
    const defaultDate = this.selectedRoadmapDetail()?.start_date ?? null;
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
        learning_resources: partial?.learning_resources ?? [],
        estimated_minutes: partial?.estimated_minutes ?? 60,
        scheduled_date: partial?.scheduled_date ?? defaultDate,
        scheduled_start: partial?.scheduled_start ?? '19:30',
        scheduled_end: partial?.scheduled_end ?? '20:30',
        prerequisite_ids: partial?.prerequisite_ids ?? [],
      },
    ]);
  }

  updateEditableTask(index: number, patch: Partial<ProposedTaskItemSchema>): void {
    this.proposalDirty.set(true);
    this.editableTasks.update(list =>
      list.map((item, idx) => (idx === index ? { ...item, ...patch } : item))
    );
  }

  removeEditableTask(index: number): void {
    this.proposalDirty.set(true);
    this.editableTasks.update(list => list.filter((_, idx) => idx !== index));
  }

  addResourceToTask(taskIndex: number, resource: { title: string; url: string; type: string; description?: string | null }): void {
    this.proposalDirty.set(true);
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
    this.proposalDirty.set(true);
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
        learning_outcomes: m.learning_outcomes ?? [],
        completion_criteria: m.completion_criteria ?? null,
        estimated_effort_minutes: m.estimated_effort_minutes ?? null,
        required_concepts: m.required_concepts ?? [],
        unverified_concepts: m.unverified_concepts ?? [],
        prerequisite_milestone_ids: m.prerequisite_milestone_ids ?? [],
      }))
    );
  }

  private clearApplyIdempotencyKeysForProposal(roadmapId: string, proposalId: string): void {
    const prefix = `${roadmapId}:${proposalId}:`;
    for (const key of this.applyIdempotencyKeys.keys()) {
      if (key.startsWith(prefix)) {
        this.applyIdempotencyKeys.delete(key);
      }
    }
  }

  private syncProposalState(proposal: ScheduleProposalResponse | null): void {
    this.proposalDirty.set(false);
    const previous = this.currentProposal();
    const previousId = previous?.id;
    const normalizedProposal =
      proposal &&
      previous &&
      proposal.id === previous.id &&
      !proposal.availability_source_metadata &&
      previous.availability_source_metadata
        ? {
            ...proposal,
            availability_source_metadata: previous.availability_source_metadata,
          }
        : proposal;
    this.currentProposal.set(normalizedProposal);
    if (!normalizedProposal) {
      if (previous?.roadmap_id && previousId) {
        this.clearApplyIdempotencyKeysForProposal(previous.roadmap_id, previousId);
      }
      if (!this.manualPlanningMode()) {
        this.editableTasks.set([]);
        this.editableDependencies.set([]);
      }
      this.confirmSoftOverflow.set(false);
      this.confirmWarnings.set(false);
      this.confirmPartialSchedule.set(false);
      this.freshCalendarConflicts.set([]);
      return;
    }
    if (normalizedProposal.id !== previousId) {
      if (previous?.roadmap_id && previousId) {
        this.clearApplyIdempotencyKeysForProposal(previous.roadmap_id, previousId);
      }
      this.confirmSoftOverflow.set(false);
      this.confirmWarnings.set(false);
      this.confirmPartialSchedule.set(false);
      this.freshCalendarConflicts.set([]);
    }
    const defaultMid = this.milestones()[0]?.id ?? null;
    this.editableTasks.set(mapRawTasksToProposedItems(normalizedProposal.tasks, defaultMid));
    this.editableDependencies.set(mapRawDependenciesToProposedItems(normalizedProposal.dependencies));
  }

  private extractErrorCode(err: HttpErrorResponse): string | null {
    const body = err.error as Record<string, unknown> | undefined;
    if (body && typeof body['code'] === 'string' && body['code'].trim().length > 0) {
      return body['code'].trim();
    }
    return null;
  }

  private extractErrorMessage(err: HttpErrorResponse, fallback: string): string {
    const body = err.error as Record<string, unknown> | undefined;
    const bodyMessage = body && typeof body['message'] === 'string' ? body['message'] : null;
    const bodyDetail = body && typeof body['detail'] === 'string' ? body['detail'] : null;
    const bodyError = body && typeof body['error'] === 'string' ? body['error'] : null;
    return pickNonEmpty(bodyMessage, bodyDetail, bodyError, fallback);
  }

  getMilestoneScopeStatus(milestone: {
    id?: string | null;
    milestone_id?: string | null;
    sequence_order: number;
  }): 'KEPT' | 'DEFERRED' | null {
    const pf = this.preliminaryFeasibility();
    if (!pf || pf.status !== 'FIT_CAPACITY_REQUIRES_APPROVAL') {
      return null;
    }
    const targetId = milestone.milestone_id ?? milestone.id ?? null;
    const matchesItem = (item: FeasibilityScopeItem): boolean =>
      Boolean(targetId && item.milestone_id && item.milestone_id === targetId) ||
      item.sequence_order === milestone.sequence_order;

    if (pf.deferred_scope.some(matchesItem)) {
      return 'DEFERRED';
    }
    if (pf.kept_scope.some(matchesItem)) {
      return 'KEPT';
    }
    return null;
  }

  private syncPreliminaryFeasibility(raw: unknown): PreliminaryFeasibility | null {
    const parsed = parsePreliminaryFeasibility(raw);
    this.preliminaryFeasibility.set(parsed);
    return parsed;
  }

  private handlePlanningConflictError(err: HttpErrorResponse, fallback: string): boolean {
    if (err.status !== 409) {
      return false;
    }
    const body = err.error as Partial<PlanningConflictResponse> | null | undefined;
    if (!body || typeof body !== 'object') {
      return false;
    }
    const code = body.code;
    if (code !== 'SCOPE_APPROVAL_REQUIRED' && code !== 'PRELIMINARY_UNSCHEDULABLE') {
      return false;
    }
    const parsedPf =
      'preliminary_feasibility' in body && body.preliminary_feasibility
        ? this.syncPreliminaryFeasibility(body.preliminary_feasibility)
        : this.preliminaryFeasibility();
    const msg = pickNonEmpty(
      typeof body.message === 'string' ? body.message : null,
      typeof body.detail === 'string' ? body.detail : null,
      fallback
    );
    this.scopeApprovalConflict.set({
      code,
      message: msg,
      scope_proposal_version:
        typeof body.scope_proposal_version === 'number'
          ? body.scope_proposal_version
          : (parsedPf?.scope_proposal_version ?? null),
      scope_proposal_hash:
        typeof body.scope_proposal_hash === 'string'
          ? body.scope_proposal_hash
          : (parsedPf?.scope_proposal_hash ?? null),
      hard_packable_capacity_minutes:
        typeof body.hard_packable_capacity_minutes === 'number'
          ? body.hard_packable_capacity_minutes
          : (parsedPf?.hard_packable_capacity_minutes ?? null),
      preliminary_feasibility: parsedPf,
    });
    this._lastErrorCode.set(code);
    this.errorMessage.set(msg);
    return true;
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
          this.syncPreliminaryFeasibility(detail.preliminary_feasibility ?? null);
          this.scopeApprovalConflict.set(null);
          this.syncProposalState(detail.current_draft_proposal ?? null);

          if (detail.goal?.clarification_context) {
            this.clarificationContext.set(detail.goal.clarification_context);
          }

          if (detail.official_schedule && !detail.current_draft_proposal) {
            this.activeStep.set(4);
          } else if (detail.current_draft_proposal || this.areMilestonesApproved()) {
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

  createRoadmap(
    payload: CreateRoadmapRequest,
    onSuccess?: (created: RoadmapResponse) => void,
    options?: { skipAutoClarify?: boolean }
  ): void {
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.clarificationQuestions.set([]);
    this.clarificationContext.set(null);
    this.clarificationSessionId.set(null);
    this.clarificationRound.set(1);
    this.clarificationStatus.set('ANALYZING');
    this.preliminaryFeasibility.set(null);
    this.scopeApprovalConflict.set(null);

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
            preliminary_feasibility: null,
          };
          this.selectedRoadmapDetail.set(emptyDetail);
          this.syncMilestonesState([]);
          this.syncPreliminaryFeasibility(null);
          this.scopeApprovalConflict.set(null);
          this.syncProposalState(null);
          this.activeStep.set(1);
          this.successMessage.set('Đã khởi tạo mục tiêu và lộ trình học tập mới!');

          if (created.goal_id && !options?.skipAutoClarify) {
            this.generateClarificationQuestions(created.goal_id);
          }
          onSuccess?.(created);
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

  uploadKnowledgeAttachments(
    goalId: string,
    items: DraftKnowledgeAttachment[]
  ): Observable<KnowledgeSourceResponse[]> {
    if (!goalId || items.length === 0) {
      return of([]);
    }
    const requests = items.slice(0, 3).map(item => {
      if (item.kind === 'FILE' && item.file) {
        const formData = new FormData();
        formData.append('file', item.file);
        formData.append('title', item.title);
        return this.http
          .post<KnowledgeSourceResponse>(
            API_ENDPOINTS.ROADMAPS.KNOWLEDGE_FILES(goalId),
            formData,
            { withCredentials: true }
          )
          .pipe(catchError(() => of(null)));
      }
      if (item.kind === 'URL' && item.url) {
        const payload: CreateKnowledgeUrlRequest = {
          title: item.title,
          url: item.url,
        };
        return this.http
          .post<KnowledgeSourceResponse>(
            API_ENDPOINTS.ROADMAPS.KNOWLEDGE_URLS(goalId),
            payload,
            { withCredentials: true }
          )
          .pipe(catchError(() => of(null)));
      }
      return of(null);
    });

    return forkJoin(requests).pipe(
      map(results => results.filter((r): r is KnowledgeSourceResponse => r !== null)),
      tap(uploaded => {
        if (uploaded.length > 0) {
          this.knowledgeSources.set(uploaded);
        }
      })
    );
  }

  generateClarificationQuestions(goalId: string): void {
    this.isGeneratingQuestions.set(true);
    this.errorMessage.set(null);
    this.clarificationStatus.set('ANALYZING');

    this.http
      .post<ClarificationQuestionsResponse>(
        API_ENDPOINTS.ROADMAPS.CLARIFY_QUESTIONS(goalId),
        {},
        {
          withCredentials: true,
          headers: { 'Idempotency-Key': createIdempotencyKey() },
        }
      )
      .pipe(
        tap(res => {
          this.clarificationQuestions.set(res.questions ?? []);
          this.applyClarificationTurn(res);
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể tạo bộ câu hỏi phỏng vấn chẩn đoán.')
          );
          this.clarificationStatus.set('ERROR');
          return of(null);
        }),
        finalize(() => {
          this.isGeneratingQuestions.set(false);
        })
      )
      .subscribe();
  }

  submitClarificationAnswers(
    goalId: string,
    answers: ClarificationAnswerItem[],
    onSuccess?: (res: SubmitClarificationAnswersResponse) => void
  ): void {
    this.isSubmittingAnswers.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const body: SubmitClarificationAnswersRequest = {
      session_id: this.clarificationSessionId(),
      round: this.clarificationRound(),
      answers,
      skipped: false,
      skipped_question_ids: this.clarificationQuestions()
        .map(question => question.question_id)
        .filter(questionId => !answers.some(answer => answer.question_id === questionId)),
      total_questions_count: this.clarificationQuestions().length,
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
          this.clarificationQuestions.set(res.questions ?? []);
          this.applyClarificationTurn(res);
          this.successMessage.set(
            res.status === 'WAITING_FOLLOW_UP'
              ? 'Đã ghi nhận vòng 1. Vui lòng trả lời câu hỏi làm rõ bổ sung (Vòng 2) bên dưới.'
              : 'Đã lưu chẩn đoán mục tiêu thành công!'
          );
          if (res.status !== 'WAITING_FOLLOW_UP') {
            this.activeStep.set(2);
          }
          onSuccess?.(res);
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

  skipClarification(goalId?: string, onSuccess?: () => void): void {
    const targetGoalId = goalId ?? this.selectedRoadmapDetail()?.goal_id;
    const skippedIds = this.clarificationQuestions().map(q => q.question_id);

    if (!targetGoalId) {
      this.errorMessage.set(
        'Chưa tìm thấy mục tiêu học tập trên máy chủ. Vui lòng hoàn tất Bước 1 trước.'
      );
      this.clarificationStatus.set('ERROR');
      return;
    }

    this.isSubmittingAnswers.set(true);
    this.errorMessage.set(null);
    this.http
      .post<SubmitClarificationAnswersResponse>(
        API_ENDPOINTS.ROADMAPS.CLARIFY_SKIP(targetGoalId),
        {
          session_id: this.clarificationSessionId(),
          skipped_question_ids: skippedIds,
        },
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.clarificationContext.set(res.clarification_context);
          this.clarificationQuestions.set([]);
          this.applyClarificationTurn(res);
          this.activeStep.set(2);
          onSuccess?.();
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể bỏ qua bước phỏng vấn chẩn đoán.')
          );
          this.clarificationStatus.set('ERROR');
          return of(null);
        }),
        finalize(() => {
          this.isSubmittingAnswers.set(false);
        })
      )
      .subscribe();
  }

  resumeClarification(goalId: string): void {
    this.isGeneratingQuestions.set(true);
    this.errorMessage.set(null);
    this.http
      .get<ClarificationQuestionsResponse>(
        API_ENDPOINTS.ROADMAPS.CLARIFICATION_STATE(goalId),
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.clarificationQuestions.set(res.questions ?? []);
          this.applyClarificationTurn(res);
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorMessage.set(
            this.extractErrorMessage(err, 'Không thể khôi phục phiên làm rõ mục tiêu.')
          );
          this.clarificationStatus.set('ERROR');
          return of(null);
        }),
        finalize(() => this.isGeneratingQuestions.set(false))
      )
      .subscribe();
  }

  private applyClarificationTurn(
    res: ClarificationQuestionsResponse | SubmitClarificationAnswersResponse
  ): void {
    this.clarificationSessionId.set(res.session_id ?? null);
    this.clarificationRound.set(res.round ?? 1);
    this.clarificationStatus.set(res.status ?? 'WAITING_ANSWER');
    this.clarificationInformationGaps.set(
      (res.information_gaps ?? []) as Record<string, unknown>[]
    );
    this.clarificationNextTurnQuotaCost.set(res.next_turn_quota_cost ?? 0);
  }

  generateMilestonesWithAi(
    roadmapId: string,
    additionalContext?: string,
    generationStrategy: 'FULL_SCOPE' | 'FIT_CAPACITY' = 'FULL_SCOPE'
  ): void {
    this.closeActiveStream();
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this._lastErrorCode.set(null);
    this._lastFailedStage.set(null);
    this.scopeApprovalConflict.set(null);
    this.lastFailedRoadmapId = roadmapId;
    this._lastMilestoneGenerationParams.set({
      roadmapId,
      additionalContext,
      generationStrategy,
    });

    const idemKey = createIdempotencyKey();
    this.sseProgress.set({
      stage: 'RESERVED',
      progress: 10,
      message: 'Đang giữ chỗ hạn ngạch AI và khởi tạo tiến trình phân rã cột mốc...',
      retryCount: 0,
      isStreaming: true,
    });

    const body: MilestoneGenerationRequest & { additional_context?: string } = {
      generation_strategy: generationStrategy,
      ...(additionalContext ? { additional_context: additionalContext } : {}),
    };
    this.aiSseService
      .initiateStreamJob(API_ENDPOINTS.ROADMAPS.MILESTONES_GENERATE_JOBS(roadmapId), body, idemKey)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          const msg = this.extractErrorMessage(
            err,
            'Không thể khởi tạo tiến trình sinh cột mốc bằng AI.'
          );
          this._lastErrorCode.set(this.extractErrorCode(err) ?? 'AI_STREAM_INIT_FAILED');
          this._lastFailedStage.set('MILESTONES');
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
            error: (err: unknown) => {
              const failMsg = pickNonEmpty(
                err instanceof Error ? err.message : null,
                'Mất kết nối luồng SSE khi đang sinh cột mốc học tập.'
              );
              this._lastErrorCode.set(
                err instanceof SseStreamError ? err.code : 'SSE_STREAM_DISCONNECTED'
              );
              this._lastFailedStage.set('MILESTONES');
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
          this.syncPreliminaryFeasibility(res.preliminary_feasibility ?? null);
          this.scopeApprovalConflict.set(null);
          this.selectedRoadmapDetail.update(detail =>
            detail
              ? {
                  ...detail,
                  milestones: res.milestones,
                  preliminary_feasibility: res.preliminary_feasibility ?? null,
                }
              : detail
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

  approveMilestones(
    roadmapId: string,
    onSuccess?: (res: MilestoneListResponse) => void,
    options?: {
      confirmedScopeProposalVersion?: number | null;
      acceptFitCapacity?: boolean;
    }
  ): void {
    if (this.loading() || this.saving() || this.isApprovingMilestones()) {
      return;
    }

    this.isApprovingMilestones.set(true);
    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    const requestBody: ApproveMilestonesRequest = {
      confirmed_scope_proposal_version: options?.confirmedScopeProposalVersion ?? null,
      accept_fit_capacity: Boolean(options?.acceptFitCapacity),
    };

    this.http
      .post<MilestoneListResponse>(
        API_ENDPOINTS.ROADMAPS.MILESTONES_APPROVE(roadmapId),
        requestBody,
        { withCredentials: true }
      )
      .pipe(
        tap(res => {
          this.syncMilestonesState(res.milestones ?? []);
          let parsedPf =
            res.preliminary_feasibility !== undefined
              ? this.syncPreliminaryFeasibility(res.preliminary_feasibility)
              : this.preliminaryFeasibility();

          if (options?.acceptFitCapacity) {
            const approvedVer =
              options.confirmedScopeProposalVersion ?? parsedPf?.scope_proposal_version ?? 1;
            if (parsedPf) {
              if (parsedPf.scope_approval_status !== 'APPROVED_BY_LEARNER') {
                parsedPf = {
                  ...parsedPf,
                  scope_approval_status: 'APPROVED_BY_LEARNER',
                  approved_scope_version: approvedVer,
                };
                this.preliminaryFeasibility.set(parsedPf);
              }
            } else {
              parsedPf = {
                status: 'FIT_CAPACITY_REQUIRES_APPROVAL',
                scope_proposal_version: approvedVer,
                requires_learner_approval: true,
                scope_approval_status: 'APPROVED_BY_LEARNER',
                approved_scope_version: approvedVer,
                kept_scope: [],
                deferred_scope: [],
                feasibility_reasons: [],
              };
              this.preliminaryFeasibility.set(parsedPf);
            }
          }

          this.scopeApprovalConflict.set(null);
          this.selectedRoadmapDetail.update(detail =>
            detail
              ? {
                  ...detail,
                  milestones: res.milestones,
                  preliminary_feasibility:
                    res.preliminary_feasibility !== undefined
                      ? res.preliminary_feasibility
                      : detail.preliminary_feasibility,
                }
              : detail
          );
          this.activeStep.set(3);
          this.successMessage.set(
            'Đã phê duyệt Cột mốc Cấp 1! Bạn có thể sinh Đề xuất Lịch học Chi tiết (Cấp 2).'
          );
          onSuccess?.(res);
        }),
        catchError((err: HttpErrorResponse) => {
          const handled = this.handlePlanningConflictError(
            err,
            'Cần xác nhận phạm vi FIT_CAPACITY hoặc điều chỉnh quỹ thời gian trước khi phê duyệt.'
          );
          if (!handled) {
            this.errorMessage.set(
              this.extractErrorMessage(err, 'Không thể phê duyệt cột mốc học tập.')
            );
          }
          return of(null);
        }),
        finalize(() => {
          this.isApprovingMilestones.set(false);
          this.saving.set(false);
        })
      )
      .subscribe();
  }

  generateScheduleProposalWithAi(roadmapId: string, onCompleted?: () => void): void {
    this.closeActiveStream();
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this._lastErrorCode.set(null);
    this._lastFailedStage.set(null);
    this.scopeApprovalConflict.set(null);
    this.freshCalendarConflicts.set([]);
    this.lastFailedRoadmapId = roadmapId;
    this.onProposalCompletedCallback = onCompleted ?? null;

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
          const handled = this.handlePlanningConflictError(
            err,
            'Cần phê duyệt phạm vi FIT_CAPACITY hoặc điều chỉnh quỹ thời gian trước khi sinh đề xuất lịch học.'
          );
          const msg = handled
            ? (this.errorMessage() ?? 'Không thể sinh đề xuất lịch học do giới hạn quỹ thời gian.')
            : this.extractErrorMessage(
                err,
                'Không thể khởi tạo tiến trình sinh đề xuất lịch học bằng AI.'
              );
          if (!handled) {
            this._lastErrorCode.set(this.extractErrorCode(err) ?? 'AI_STREAM_INIT_FAILED');
            this._lastFailedStage.set('PROPOSAL');
            this.errorMessage.set(msg);
          } else {
            this._lastFailedStage.set(null);
          }
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
            error: (err: unknown) => {
              const failMsg = pickNonEmpty(
                err instanceof Error ? err.message : null,
                'Mất kết nối luồng SSE khi đang sinh đề xuất lịch học.'
              );
              this._lastErrorCode.set(
                err instanceof SseStreamError ? err.code : 'SSE_STREAM_DISCONNECTED'
              );
              this._lastFailedStage.set('PROPOSAL');
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

  retryFailedAiGeneration(fallbackRoadmapId?: string): void {
    const failedStage = this.lastFailedStage();
    const targetRoadmapId =
      this.lastFailedRoadmapId ?? fallbackRoadmapId ?? this.selectedRoadmapDetail()?.id;
    if (!failedStage || !targetRoadmapId) {
      return;
    }
    if (failedStage === 'MILESTONES') {
      const params = this._lastMilestoneGenerationParams();
      if (params && (params.additionalContext || params.generationStrategy !== 'FULL_SCOPE')) {
        this.generateMilestonesWithAi(
          targetRoadmapId,
          params.additionalContext,
          params.generationStrategy
        );
      } else {
        this.generateMilestonesWithAi(targetRoadmapId);
      }
      return;
    }
    this.generateScheduleProposalWithAi(
      targetRoadmapId,
      this.onProposalCompletedCallback ?? undefined
    );
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
    const originalTasks = this.currentProposal()?.tasks ?? [];
    return tasks.map(t => {
      const original = originalTasks.find(raw => raw['task_id'] === t.task_id);
      const rawStart = original?.['scheduled_start'];
      const rawEnd = original?.['scheduled_end'];
      const preserveTimes = original?.['scheduled_date'] === t.scheduled_date &&
        original?.['estimated_minutes'] === Number(t.estimated_minutes) &&
        typeof rawStart === 'string' && typeof rawEnd === 'string' &&
        normalizeTimeInput(rawStart, '') === t.scheduled_start &&
        normalizeTimeInput(rawEnd, '') === t.scheduled_end;
      return {
        ...t,
        title: t.title.trim(),
        estimated_minutes: Number(t.estimated_minutes),
        scheduled_start: preserveTimes && typeof rawStart === 'string' ? rawStart : buildIsoDateTime(t.scheduled_date, t.scheduled_start),
        scheduled_end: preserveTimes && typeof rawEnd === 'string' ? rawEnd : buildIsoDateTime(t.scheduled_date, t.scheduled_end),
      };
    });
  }

  updateProposal(
    roadmapId: string,
    proposalId: string,
    payload?: UpdateScheduleProposalRequest
  ): void {
    if (!payload && !this.proposalDirty() && this.currentProposal()?.is_valid) {
      this.successMessage.set('Bản nháp đã đạt chuẩn kiểm định.');
      return;
    }
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
          this.clearApplyIdempotencyKeysForProposal(roadmapId, proposalId);
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
              estimated_effort_minutes: m.estimated_effort_minutes ?? null,
              learning_outcomes: m.learning_outcomes ?? [],
              completion_criteria: m.completion_criteria ?? null,
              required_concepts: m.required_concepts ?? [],
              unverified_concepts: m.unverified_concepts ?? [],
              prerequisite_milestone_ids: m.prerequisite_milestone_ids ?? [],
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
    confirmSoftOverflow: boolean = this.confirmSoftOverflow(),
    onSuccess?: (res: ApplyScheduleProposalResponse) => void,
    confirmWarnings: boolean = this.confirmWarnings(),
    confirmPartialSchedule: boolean = this.confirmPartialSchedule()
  ): void {
    if (this.saving()) {
      return;
    }

    this.saving.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this._lastErrorCode.set(null);
    this._lastFailedStage.set(null);
    this.freshCalendarConflicts.set([]);

    const shouldSendConfirmWarnings =
      confirmWarnings || this.needsJudgeConfirmation();
    const payload: ApplyScheduleProposalRequest = shouldSendConfirmWarnings
      ? {
          confirm_soft_overflow: confirmSoftOverflow,
          confirm_warnings: confirmWarnings || confirmSoftOverflow,
          confirm_partial_schedule: confirmPartialSchedule,
        }
      : {
          confirm_soft_overflow: confirmSoftOverflow,
          confirm_warnings: false,
          confirm_partial_schedule: confirmPartialSchedule,
        };

    const idemSlot = `${roadmapId}:${proposalId}:${Number(payload.confirm_soft_overflow)}:${Number(payload.confirm_warnings)}:${Number(payload.confirm_partial_schedule)}`;
    let idempotencyKey = this.applyIdempotencyKeys.get(idemSlot);
    if (!idempotencyKey) {
      idempotencyKey = createIdempotencyKey();
      this.applyIdempotencyKeys.set(idemSlot, idempotencyKey);
    }

    this.http
      .post<ApplyScheduleProposalResponse>(
        API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY(roadmapId, proposalId),
        payload,
        {
          withCredentials: true,
          headers: { 'Idempotency-Key': idempotencyKey },
        }
      )
      .pipe(
        tap(res => {
          this.clearApplyIdempotencyKeysForProposal(roadmapId, proposalId);
          this.lastApplyResult.set(res);
          this.confirmSoftOverflow.set(false);
          this.confirmWarnings.set(false);
          this.confirmPartialSchedule.set(false);
          this.freshCalendarConflicts.set([]);
          this.activeStep.set(4);
          this.successMessage.set(
            `Đã áp dụng lịch học chính thức thành công (${res.total_sessions} phiên, ${res.total_planned_minutes} phút)!`
          );
          this.loadRoadmapDetail(roadmapId);
          this.loadRoadmaps();
          onSuccess?.(res);
        }),
        catchError((err: HttpErrorResponse) => {
          const body = err.error as Record<string, unknown> | undefined;
          const errorCode = this.extractErrorCode(err);
          this._lastErrorCode.set(errorCode);
          this._lastFailedStage.set(null);

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

          if (err.status === 409 && errorCode === 'JUDGE_REVIEW_CONFIRMATION_REQUIRED') {
            const rawJudge =
              typeof body?.['judge_status'] === 'string' && body['judge_status'].trim().length > 0
                ? body['judge_status'].trim()
                : 'NEEDS_REVIEW';
            const advisory = Array.isArray(body?.['advisory_warnings'])
              ? body['advisory_warnings'].map(String)
              : undefined;
            this.confirmWarnings.set(false);
            this.currentProposal.update(prev =>
              prev
                ? {
                    ...prev,
                    judge_status: rawJudge,
                    ...(advisory ? { advisory_warnings: advisory } : {}),
                  }
                : prev
            );
            this.errorMessage.set(
              this.extractErrorMessage(
                err,
                'Đề xuất lịch học cần bạn kiểm tra lưu ý thẩm định và tích xác nhận trước khi áp dụng.'
              )
            );
            return of(null);
          }

          if (err.status === 409 && errorCode === 'PARTIAL_SCHEDULE_CONFIRMATION_REQUIRED') {
            this.confirmPartialSchedule.set(false);
            this.currentProposal.update(prev =>
              prev
                ? {
                    ...prev,
                    is_partial_schedule: true,
                    schedule_completeness_status: 'PARTIAL',
                  }
                : prev
            );
            this.errorMessage.set(
              this.extractErrorMessage(
                err,
                'Lịch chỉ xếp được một phần Roadmap trước deadline. Vui lòng tích xác nhận giữ phần còn lại trong Backlog trước khi áp dụng.'
              )
            );
            return of(null);
          }

          if (err.status === 409 && errorCode === 'FRESH_CALENDAR_CONFLICT_DETECTED') {
            const conflicts = Array.isArray(body?.['conflicts'])
              ? body['conflicts'].filter(
                  (c): c is Record<string, unknown> => typeof c === 'object' && c !== null
                )
              : [];
            this.freshCalendarConflicts.set(conflicts);
            this.errorMessage.set(
              this.extractErrorMessage(
                err,
                'Phát hiện xung đột mới với sự kiện bận trên Google Calendar hoặc lộ trình đang học. Vui lòng tạo lại hoặc tối ưu lại đề xuất trước khi áp dụng.'
              )
            );
            return of(null);
          }

          if (err.status === 409 && errorCode === 'PROPOSAL_SUPERSEDED') {
            this.clearApplyIdempotencyKeysForProposal(roadmapId, proposalId);
            this.currentProposal.update(prev =>
              prev && prev.id === proposalId ? { ...prev, status: 'SUPERSEDED' } : prev
            );
            this.errorMessage.set(
              this.extractErrorMessage(
                err,
                'Bản nháp đề xuất lịch học này đã bị thay thế bởi phiên bản mới hơn. Vui lòng tải lại bản nháp hiện hành.'
              )
            );
            return of(null);
          }

          if (err.status === 409 && errorCode === 'SOFT_OVERFLOW_CONFIRMATION_REQUIRED') {
            this.confirmSoftOverflow.set(false);
            this.currentProposal.update(prev =>
              prev ? { ...prev, has_soft_overflow: true } : prev
            );
          }

          const msg = this.extractErrorMessage(
            err,
            'Không thể áp dụng đề xuất lịch học vào Lịch học Chính thức.'
          );
          this.errorMessage.set(msg);
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
    const sseStepFailMsg = isFailed
      ? pickNonEmpty(evt.error, evt.message, 'Tiến trình AI gặp lỗi.')
      : '';

    this.sseProgress.update(prev => ({
      stage: isCompleted
        ? 'COMPLETED'
        : isFailed
          ? 'FAILED'
          : (evt.stage ?? prev.stage),
      progress: typeof evt.progress === 'number' ? evt.progress : prev.progress,
      message: isFailed ? sseStepFailMsg : (pickNonEmpty(text) || prev.message),
      retryCount: isRetry
        ? (evt.retry_attempt ?? prev.retryCount + 1)
        : prev.retryCount,
      isStreaming: !isCompleted && !isFailed,
    }));

    if (isCompleted) {
      this._lastErrorCode.set(null);
      this._lastFailedStage.set(null);
      if (mode === 'MILESTONES') {
        const payload = evt.payload as
          | {
              milestones?: MilestoneResponse[];
              preliminary_feasibility?: Record<string, unknown> | null;
            }
          | undefined;
        if (payload && Array.isArray(payload.milestones)) {
          this.syncMilestonesState(payload.milestones);
        }
        if (payload && 'preliminary_feasibility' in payload) {
          this.syncPreliminaryFeasibility(payload.preliminary_feasibility ?? null);
          this.scopeApprovalConflict.set(null);
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
        this.proposalCompletedCount.update(c => c + 1);
        const cb = this.onProposalCompletedCallback;
        this.onProposalCompletedCallback = null;
        cb?.();
      }
    } else if (isFailed) {
      this._lastErrorCode.set(pickNonEmpty(evt.error_code, evt.code, 'AI_EXECUTION_ERROR'));
      this._lastFailedStage.set(mode);
      this.errorMessage.set(
        pickNonEmpty(
          evt.error,
          evt.message,
          'Tiến trình sinh lộ trình bằng AI thất bại. Vui lòng thử lại hoặc lập kế hoạch thủ công.'
        )
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

  reoptimizeSchedule(id: string): Observable<unknown> {
    return this.http.post(
      API_ENDPOINTS.ROADMAPS.REOPTIMIZE_SCHEDULE(id),
      {},
      { withCredentials: true }
    );
  }

  triggerOverdueRecovery(id: string): Observable<unknown> {
    return this.http.post(
      API_ENDPOINTS.ROADMAPS.OVERDUE_REVISE(id),
      {},
      { withCredentials: true }
    );
  }
}

export { RoadmapService as RoadmapPlanningStore };
