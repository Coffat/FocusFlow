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

export type PlanningStep = 1 | 2 | 3;

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
