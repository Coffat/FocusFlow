import { components } from '../../../core/api/schema';

export type TodayFocusResponse = components['schemas']['TodayFocusResponse'];
export type StudySessionResponse = components['schemas']['StudySessionResponse'];
export type TaskResponse = components['schemas']['TaskResponse'];
export type StartSessionRequest = components['schemas']['StartSessionRequest'];
export type HeartbeatSessionRequest = components['schemas']['HeartbeatSessionRequest'];
export type FinalizeSessionRequest = components['schemas']['FinalizeSessionRequest'];
export type ResolveTakeawayRequest = components['schemas']['ResolveTakeawayRequest'];
export type SessionMode = StartSessionRequest['session_mode'];
export type TimeSufficiency = NonNullable<FinalizeSessionRequest['checkin_time_sufficiency']>;
