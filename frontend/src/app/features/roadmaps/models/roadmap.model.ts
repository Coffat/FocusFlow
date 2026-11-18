import type { components } from '../../../core/api/schema';

// OpenAPI 3.1 Derived Schema Types (Zero hand-written API contracts)
export type GoalResponse = components['schemas']['GoalResponse'];
export type RoadmapResponse = components['schemas']['RoadmapResponse'];
export type RoadmapDetailResponse = components['schemas']['RoadmapDetailResponse'];
export type CreateRoadmapRequest = components['schemas']['CreateRoadmapRequest'];
export type UpdateRoadmapRequest = components['schemas']['UpdateRoadmapRequest'];
export type MilestoneResponse = components['schemas']['MilestoneResponse'];
export type MilestoneListResponse = components['schemas']['MilestoneListResponse'];
export type MilestoneUpsertItemSchema = components['schemas']['MilestoneUpsertItemSchema'];
export type UpdateMilestonesRequest = components['schemas']['UpdateMilestonesRequest'];
export type ApproveMilestonesRequest = components['schemas']['ApproveMilestonesRequest'];
export type MilestoneGenerationRequest = components['schemas']['MilestoneGenerationRequest'];
export type PlanningConflictResponse = components['schemas']['PlanningConflictResponse'];

export type PreliminaryFeasibilityStatus =
  | 'FULL_SCOPE_FEASIBLE'
  | 'FIT_CAPACITY_REQUIRES_APPROVAL'
  | 'PRELIMINARY_UNSCHEDULABLE';

export type ScopeApprovalStatus =
  | 'NOT_REQUIRED'
  | 'PENDING_LEARNER_APPROVAL'
  | 'APPROVED_BY_LEARNER';

export interface FeasibilityScopeItem {
  sequence_order: number;
  milestone_id?: string | null;
  title: string;
  completion_criteria?: string | null;
  estimated_effort_minutes: number;
  minimum_defensible_effort_minutes?: number | null;
  normalized_planned_effort_minutes?: number | null;
  expected_outcomes?: string[];
  learning_outcomes?: string[];
  dependencies?: number[];
  prerequisite_milestone_ids?: string[];
}

export interface PreliminaryFeasibilityReason {
  code: string;
  message: string;
  hard_packable_capacity_minutes?: number | null;
  soft_target_capacity_minutes?: number | null;
  first_milestone_minimum_minutes?: number | null;
  first_milestone_llm_minutes?: number | null;
  minimum_defensible_total_minutes?: number | null;
  llm_estimated_total_minutes?: number | null;
  estimated_total_minutes?: number | null;
}

export interface PreliminaryEarliestTargetDateRange {
  min_date: string;
  max_date: string;
}

export interface PreliminaryAdjustmentOptions {
  is_approximate?: boolean;
  estimated_earliest_target_date_range?: PreliminaryEarliestTargetDateRange | null;
  recommended_additional_weekly_minutes?: number;
}

export interface PreliminaryFeasibility {
  status: PreliminaryFeasibilityStatus;
  scope_proposal_version: number;
  scope_proposal_hash?: string | null;
  requires_learner_approval: boolean;
  scope_approval_status: ScopeApprovalStatus;
  approved_scope_version?: number | null;
  hard_packable_capacity_minutes?: number | null;
  soft_target_capacity_minutes?: number | null;
  llm_estimated_total_minutes?: number;
  estimated_total_minutes?: number;
  minimum_defensible_total_minutes?: number;
  normalized_planned_total_minutes?: number;
  kept_scope: FeasibilityScopeItem[];
  deferred_scope: FeasibilityScopeItem[];
  expected_outcomes?: string[];
  feasibility_reasons: PreliminaryFeasibilityReason[];
  adjustment_options?: PreliminaryAdjustmentOptions | null;
  target_date?: string | null;
  effective_start_date?: string | null;
  prior_knowledge_level?: string | null;
}

export interface ScopeApprovalConflict {
  code: 'SCOPE_APPROVAL_REQUIRED' | 'PRELIMINARY_UNSCHEDULABLE';
  message: string;
  scope_proposal_version: number | null;
  scope_proposal_hash: string | null;
  hard_packable_capacity_minutes: number | null;
  preliminary_feasibility: PreliminaryFeasibility | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function toOptionalNumber(value: unknown): number | null {
  return typeof value === 'number' && !Number.isNaN(value) ? value : null;
}

function toStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(v => String(v)) : [];
}

function toNumberArray(value: unknown): number[] {
  return Array.isArray(value)
    ? value.filter((v): v is number => typeof v === 'number' && !Number.isNaN(v))
    : [];
}

function parseScopeItem(raw: unknown): FeasibilityScopeItem | null {
  if (!isRecord(raw)) return null;
  const seq = typeof raw['sequence_order'] === 'number' ? raw['sequence_order'] : 0;
  const title = typeof raw['title'] === 'string' ? raw['title'] : '';
  if (!title && seq <= 0) return null;
  return {
    sequence_order: seq,
    milestone_id: typeof raw['milestone_id'] === 'string' ? raw['milestone_id'] : null,
    title,
    completion_criteria:
      typeof raw['completion_criteria'] === 'string' ? raw['completion_criteria'] : null,
    estimated_effort_minutes: toOptionalNumber(raw['estimated_effort_minutes']) ?? 0,
    minimum_defensible_effort_minutes: toOptionalNumber(raw['minimum_defensible_effort_minutes']),
    normalized_planned_effort_minutes: toOptionalNumber(raw['normalized_planned_effort_minutes']),
    expected_outcomes: Array.isArray(raw['expected_outcomes'])
      ? toStringArray(raw['expected_outcomes'])
      : undefined,
    learning_outcomes: Array.isArray(raw['learning_outcomes'])
      ? toStringArray(raw['learning_outcomes'])
      : undefined,
    dependencies: Array.isArray(raw['dependencies'])
      ? toNumberArray(raw['dependencies'])
      : undefined,
    prerequisite_milestone_ids: Array.isArray(raw['prerequisite_milestone_ids'])
      ? toStringArray(raw['prerequisite_milestone_ids'])
      : undefined,
  };
}

function parseFeasibilityReason(raw: unknown): PreliminaryFeasibilityReason | null {
  if (!isRecord(raw)) return null;
  const message = typeof raw['message'] === 'string' ? raw['message'] : '';
  const code = typeof raw['code'] === 'string' ? raw['code'] : 'FEASIBILITY_NOTE';
  if (!message) return null;
  return {
    code,
    message,
    hard_packable_capacity_minutes: toOptionalNumber(raw['hard_packable_capacity_minutes']),
    soft_target_capacity_minutes: toOptionalNumber(raw['soft_target_capacity_minutes']),
    first_milestone_minimum_minutes: toOptionalNumber(raw['first_milestone_minimum_minutes']),
    first_milestone_llm_minutes: toOptionalNumber(raw['first_milestone_llm_minutes']),
    minimum_defensible_total_minutes: toOptionalNumber(raw['minimum_defensible_total_minutes']),
    llm_estimated_total_minutes: toOptionalNumber(raw['llm_estimated_total_minutes']),
    estimated_total_minutes: toOptionalNumber(raw['estimated_total_minutes']),
  };
}

function parseAdjustmentOptions(raw: unknown): PreliminaryAdjustmentOptions | null {
  if (!isRecord(raw)) return null;
  const rawRange = raw['estimated_earliest_target_date_range'];
  let dateRange: PreliminaryEarliestTargetDateRange | null = null;
  if (
    isRecord(rawRange) &&
    typeof rawRange['min_date'] === 'string' &&
    typeof rawRange['max_date'] === 'string'
  ) {
    dateRange = { min_date: rawRange['min_date'], max_date: rawRange['max_date'] };
  }
  return {
    is_approximate: typeof raw['is_approximate'] === 'boolean' ? raw['is_approximate'] : true,
    estimated_earliest_target_date_range: dateRange,
    recommended_additional_weekly_minutes:
      toOptionalNumber(raw['recommended_additional_weekly_minutes']) ?? 0,
  };
}

export function parsePreliminaryFeasibility(raw: unknown): PreliminaryFeasibility | null {
  if (!isRecord(raw)) return null;
  const rawStatus = raw['status'];
  const status: PreliminaryFeasibilityStatus =
    rawStatus === 'FIT_CAPACITY_REQUIRES_APPROVAL' ||
    rawStatus === 'PRELIMINARY_UNSCHEDULABLE' ||
    rawStatus === 'FULL_SCOPE_FEASIBLE'
      ? rawStatus
      : 'FULL_SCOPE_FEASIBLE';

  const rawApproval = raw['scope_approval_status'];
  const scopeApprovalStatus: ScopeApprovalStatus =
    rawApproval === 'PENDING_LEARNER_APPROVAL' ||
    rawApproval === 'APPROVED_BY_LEARNER' ||
    rawApproval === 'NOT_REQUIRED'
      ? rawApproval
      : status === 'FIT_CAPACITY_REQUIRES_APPROVAL'
        ? 'PENDING_LEARNER_APPROVAL'
        : 'NOT_REQUIRED';

  const keptScope = Array.isArray(raw['kept_scope'])
    ? raw['kept_scope'].map(parseScopeItem).filter((item): item is FeasibilityScopeItem => item !== null)
    : [];
  const deferredScope = Array.isArray(raw['deferred_scope'])
    ? raw['deferred_scope']
        .map(parseScopeItem)
        .filter((item): item is FeasibilityScopeItem => item !== null)
    : [];
  const reasons = Array.isArray(raw['feasibility_reasons'])
    ? raw['feasibility_reasons']
        .map(parseFeasibilityReason)
        .filter((r): r is PreliminaryFeasibilityReason => r !== null)
    : [];

  return {
    status,
    scope_proposal_version: toOptionalNumber(raw['scope_proposal_version']) ?? 0,
    scope_proposal_hash:
      typeof raw['scope_proposal_hash'] === 'string' ? raw['scope_proposal_hash'] : null,
    requires_learner_approval: Boolean(raw['requires_learner_approval']),
    scope_approval_status: scopeApprovalStatus,
    approved_scope_version: toOptionalNumber(raw['approved_scope_version']),
    hard_packable_capacity_minutes: toOptionalNumber(raw['hard_packable_capacity_minutes']),
    soft_target_capacity_minutes: toOptionalNumber(raw['soft_target_capacity_minutes']),
    llm_estimated_total_minutes: toOptionalNumber(raw['llm_estimated_total_minutes']) ?? undefined,
    estimated_total_minutes: toOptionalNumber(raw['estimated_total_minutes']) ?? undefined,
    minimum_defensible_total_minutes:
      toOptionalNumber(raw['minimum_defensible_total_minutes']) ?? undefined,
    normalized_planned_total_minutes:
      toOptionalNumber(raw['normalized_planned_total_minutes']) ?? undefined,
    kept_scope: keptScope,
    deferred_scope: deferredScope,
    expected_outcomes: Array.isArray(raw['expected_outcomes'])
      ? toStringArray(raw['expected_outcomes'])
      : undefined,
    feasibility_reasons: reasons,
    adjustment_options: parseAdjustmentOptions(raw['adjustment_options']),
    target_date: typeof raw['target_date'] === 'string' ? raw['target_date'] : null,
    effective_start_date:
      typeof raw['effective_start_date'] === 'string' ? raw['effective_start_date'] : null,
    prior_knowledge_level:
      typeof raw['prior_knowledge_level'] === 'string' ? raw['prior_knowledge_level'] : null,
  };
}

export function formatEffortMinutes(minutes: number | null | undefined): string {
  if (typeof minutes !== 'number' || Number.isNaN(minutes) || minutes <= 0) {
    return '0 phút';
  }
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  if (hrs === 0) return `${mins} phút`;
  if (mins === 0) return `${hrs} giờ (${minutes} phút)`;
  return `${hrs}g ${mins}p (${minutes} phút)`;
}
export type SseJobTicketResponse = components['schemas']['SseJobTicketResponse'];
export type ProposedTaskItemSchema = components['schemas']['ProposedTaskItemSchema'];
export type ProposedDependencyItemSchema = components['schemas']['ProposedDependencyItemSchema'];
export type ConstraintViolationSchema = components['schemas']['ConstraintViolationSchema'];
export type SoftOverflowWarningSchema = components['schemas']['SoftOverflowWarningSchema'];
export type ScheduleProposalResponse = components['schemas']['ScheduleProposalResponse'];
export type UpdateScheduleProposalRequest = components['schemas']['UpdateScheduleProposalRequest'];
export type CreateManualRoadmapPlanRequest = components['schemas']['CreateManualRoadmapPlanRequest'];
export type ApplyScheduleProposalRequest = components['schemas']['ApplyScheduleProposalRequest'];
export type ApplyScheduleProposalResponse = components['schemas']['ApplyScheduleProposalResponse'];
export type OfficialScheduleResponse = components['schemas']['OfficialScheduleResponse'];
export type ScheduledTaskResponse = components['schemas']['ScheduledTaskResponse'];
export type LearningResourceSchema = components['schemas']['LearningResourceSchema'];

export interface LearningResourceItem {
  title: string;
  url: string;
  type: string;
  description?: string | null;
}

export type ProposalTask = ProposedTaskItemSchema;

export type PriorKnowledgeLevel = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';

export type ClarificationQuestion = components['schemas']['ClarificationQuestion'];
export type ClarificationOption = components['schemas']['ClarificationOption'];
export type ClarificationQuestionsResponse = components['schemas']['ClarificationQuestionsResponse'];
export type ClarificationAnswerItem = components['schemas']['ClarificationAnswerItem'];
export type SubmitClarificationAnswersRequest = components['schemas']['SubmitClarificationAnswersRequest'];
export type SubmitClarificationAnswersResponse = components['schemas']['SubmitClarificationAnswersResponse'];

export type KnowledgeSourceResponse = components['schemas']['KnowledgeSourceResponse'];
export type CreateKnowledgeUrlRequest = components['schemas']['CreateKnowledgeUrlRequest'];

export interface DraftKnowledgeAttachment {
  id: string;
  kind: 'FILE' | 'URL';
  title: string;
  file?: File;
  sizeBytes?: number;
  url?: string;
}

export type PlanningStep = 1 | 2 | 3 | 4;

export interface SseProgressState {
  stage: 'IDLE' | 'RESERVED' | 'STREAMING' | 'VALIDATING_TIER_1_2_3' | 'COMPLETED' | 'FAILED';
  progress: number;
  message: string;
  retryCount: number;
  isStreaming: boolean;
}

// Legacy View Models kept for backward compatibility
export interface Milestone {
  id: string;
  roadmapId: string;
  title: string;
  orderIndex: number;
  description: string;
  totalPomodoros: number;
  completedPomodoros: number;
  tasksCount: number;
}

export interface Roadmap {
  id: string;
  userId: string;
  title: string;
  targetGoal: string;
  status: 'DRAFT' | 'INITIALIZED' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED';
  hoursPerWeek: number;
  milestones: Milestone[];
  createdAt: string;
}

export interface GenerateRoadmapPayload {
  goal: string;
  hoursPerWeek: number;
  currentLevel: string;
}
