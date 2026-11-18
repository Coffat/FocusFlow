import { components } from '../../../core/api/schema';

export type TodayFocusResponse = components['schemas']['TodayFocusResponse'];
export type StudySessionResponse = components['schemas']['StudySessionResponse'];
export type TaskResponse = components['schemas']['TaskResponse'];
export type StartSessionRequest = components['schemas']['StartSessionRequest'];
export type HeartbeatSessionRequest = components['schemas']['HeartbeatSessionRequest'];
export type FinalizeSessionRequest = components['schemas']['FinalizeSessionRequest'];
export type ResolveTakeawayRequest = components['schemas']['ResolveTakeawayRequest'];
export type StickyNoteResponse = components['schemas']['StickyNoteResponse'];
export type CreateStickyNoteRequest = components['schemas']['CreateStickyNoteRequest'];
export type UpdateStickyNoteRequest = components['schemas']['UpdateStickyNoteRequest'];
export type WorkspaceStudioConfigResponse = components['schemas']['WorkspaceStudioConfigResponse'];
export type UpdateWorkspaceStudioConfigRequest =
  components['schemas']['UpdateWorkspaceStudioConfigRequest'];
export type SessionMode = StartSessionRequest['session_mode'];
export type TimeSufficiency = NonNullable<FinalizeSessionRequest['checkin_time_sufficiency']>;

// Client-only UI/Studio types (do not represent backend API contracts)
export type TimerTabMode = 'pomodoro' | 'mvs' | 'stopwatch' | 'break';
export type BreakType = 'short' | 'long';
export type WorkspaceSceneId =
  | 'architectural'
  | 'lofi-night'
  | 'rain'
  | 'cafe'
  | 'library';
export type SessionLifecycleState =
  | 'READY'
  | 'FOCUSING'
  | 'PAUSED'
  | 'BREAK'
  | 'COMPLETED';
export type ClockStyleId = 'editorial' | 'ring' | 'flip' | 'minimal';
export type ClockSize = 'md' | 'lg';
export type StickyNoteColor =
  | 'cream'
  | 'pink'
  | 'sage'
  | 'blue'
  | 'amber'
  | 'lavender';
export type SoundChannelId = 'rain' | 'cafe' | 'brown' | 'white' | 'fireplace';
export type WorkspaceToolPopover = 'audio' | 'shield' | 'scene' | 'clock' | null;
export type TaskFilterMode = 'all' | 'todo' | 'overdue';

export interface SceneMeta {
  id: WorkspaceSceneId;
  label: string;
  description: string;
  isDark: boolean;
  imageUrl?: string;
  fallbackGradient: string;
  scrimRgba: string;
}

export interface StickyNoteItem {
  id: string;
  title: string;
  content: string;
  color: StickyNoteColor;
  pinned: boolean;
  sessionId: string | null;
  taskId: string | null;
  createdAt: number;
  updatedAt: number;
  posX?: number;
  posY?: number;
  zIndex?: number;
  serverSynced?: boolean;
}

export interface MilestoneContextSummary {
  roadmapId: string;
  milestoneId: string;
  milestoneTitle?: string | null;
  learningOutcomes: string[];
  completionCriteria: string | null;
}

export interface SoundChannelState {
  id: SoundChannelId;
  label: string;
  active: boolean;
  volume: number; // 0..1
}

export interface ParkingThoughtItem {
  id: string;
  text: string;
  createdAt: number;
  done: boolean;
}

export interface FocusShieldConfig {
  tabGuardEnabled: boolean;
  zenLockEnabled: boolean;
  blocklist: string[];
  parkingLot: ParkingThoughtItem[];
}

export interface TodayProgressSummary {
  completedCount: number;
  totalCount: number;
  percentage: number;
  totalPlannedMinutes: number;
  totalStudiedMinutes: number;
}
