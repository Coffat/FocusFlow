import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of, map } from 'rxjs';
import {
  DashboardSummary,
  DashboardDataState,
  DashboardKpi,
  DayStudyDistribution,
  DashboardActiveRoadmap,
  DashboardTodayQueueItem,
  DashboardAiInsight,
  DashboardAdaptationStatus,
  DashboardScheduleBlock,
} from '../models/dashboard.model';

export const EMPTY_DASHBOARD_SUMMARY: DashboardSummary = {
  kpi: {
    monthlyHours: 0,
    monthlyTarget: 0,
    weeklyCommitment: 0,
    streakDays: 0,
    streakRecord: 0,
    recentStreak: [false, false, false, false, false, false, false],
    adherenceRate: 0,
    adherenceChange: 0,
    pomodoroCompleted: 0,
    pomodoroDeepWorkHours: 0,
    pomodoroTargetRate: 0,
  },
  activeRoadmaps: [],
  todayQueue: [],
  studyDistribution: [
    { day: 'T2', fullDayName: 'Thứ Hai', hours: 0, isToday: false },
    { day: 'T3', fullDayName: 'Thứ Ba', hours: 0, isToday: false },
    { day: 'T4', fullDayName: 'Thứ Tư', hours: 0, isToday: false },
    { day: 'T5', fullDayName: 'Thứ Năm', hours: 0, isToday: false },
    { day: 'T6', fullDayName: 'Thứ Sáu', hours: 0, isToday: false },
    { day: 'T7', fullDayName: 'Thứ Bảy', hours: 0, isToday: false },
    { day: 'CN', fullDayName: 'Chủ Nhật', hours: 0, isToday: false },
  ],
  scheduleBlocks: [],
  aiInsight: {
    peakHourRange: 'Chưa có dữ liệu',
    efficiencyChange: 0,
    suggestedBreak: 'Nghỉ 5 phút sau 25 phút',
    summary: 'Chưa có đủ dữ liệu học tập để phân tích nhịp sinh học.',
    recommendations: ['Hãy bắt đầu phiên học đầu tiên trong phòng học Pomodoro!'],
  },
  adaptationStatus: {
    hasDominoShift: false,
    affectedTasksCount: 0,
    rescheduleReason: '',
    needsAttention: false,
    alertMessage: 'Lịch trình học tập hiện tại cân bằng.',
  },
  currentWeek: {
    weekNumber: 1,
    startDate: '',
    endDate: '',
  },
  activeRoadmapTitle: '',
  totalMilestones: 0,
  completedMilestones: 0,
  totalStudyHours: 0,
  weeklyTargetHours: 0,
  streakDays: 0,
  upcomingTasks: [],
};

export const DEFAULT_DASHBOARD_SUMMARY = EMPTY_DASHBOARD_SUMMARY;

export function mapDashboardSummary(data: unknown): DashboardSummary {
  if (!data || typeof data !== 'object') {
    return { ...EMPTY_DASHBOARD_SUMMARY };
  }

  const payload = data as Record<string, unknown>;
  const rawKpi = (payload['kpi'] as Record<string, unknown>) ?? {};

  // Active roadmaps mapping
  const rawRoadmaps = payload['active_roadmaps'] ?? payload['activeRoadmaps'];
  const activeRoadmaps: DashboardActiveRoadmap[] = Array.isArray(rawRoadmaps)
    ? rawRoadmaps.map((r: Record<string, unknown>) => ({
        id: String(r?.['id'] ?? ''),
        title: String(r?.['title'] ?? 'Lộ trình học tập'),
        category: String(r?.['category'] ?? (r?.['code'] ? `Mã: ${r['code']}` : 'Chung')),
        progressPercentage: Number(r?.['progress_pct'] ?? r?.['progressPercentage'] ?? 0),
        totalTasks: Number(r?.['total_tasks'] ?? r?.['totalTasks'] ?? 0),
        completedTasks: Number(r?.['completed_tasks'] ?? r?.['completedTasks'] ?? 0),
        nextTaskTitle: String(r?.['next_task_title'] ?? r?.['nextTaskTitle'] ?? 'Chưa có nhiệm vụ kế tiếp'),
        deadline: String(r?.['deadline'] ?? 'Chưa xác định'),
        updatedAt: String(r?.['updated_at'] ?? r?.['updatedAt'] ?? 'Gần đây'),
        commitmentHoursPerWeek: Number(r?.['commitment_hours_per_week'] ?? r?.['commitmentHoursPerWeek'] ?? 0),
      }))
    : [];

  // Calculate weekly commitment from active roadmaps or fallback
  const roadmapWeeklySum = activeRoadmaps.reduce(
    (sum, r) => sum + (r.commitmentHoursPerWeek ?? 0),
    0
  );
  const fallbackCommitment = rawKpi['target_hours']
    ? Math.round(Number(rawKpi['target_hours']) / 4)
    : Number(rawKpi['weeklyCommitment'] ?? 0);
  const weeklyCommitment = roadmapWeeklySum > 0 ? roadmapWeeklySum : fallbackCommitment;

  const monthlyHours = Number(rawKpi['monthly_hours'] ?? rawKpi['monthlyHours'] ?? 0);
  const monthlyTarget = Number(rawKpi['target_hours'] ?? rawKpi['monthlyTarget'] ?? 0);
  const streakDays = Number(rawKpi['streak_days'] ?? rawKpi['streakDays'] ?? 0);
  const streakRecord = Number(rawKpi['personal_best_streak'] ?? rawKpi['streakRecord'] ?? streakDays);
  const adherenceRate = Number(rawKpi['adherence_rate_pct'] ?? rawKpi['adherenceRate'] ?? 0);
  const adherenceChange = Number(rawKpi['adherence_delta_pct'] ?? rawKpi['adherenceChange'] ?? 0);
  const pomodoroCompleted = Number(rawKpi['completed_pomodoro_count'] ?? rawKpi['pomodoroCompleted'] ?? 0);
  const pomodoroDeepWorkHours = Number(rawKpi['deep_work_hours'] ?? rawKpi['pomodoroDeepWorkHours'] ?? 0);

  const pomodoroTargetRate = rawKpi['monthly_progress_pct'] !== undefined
    ? Math.round(Number(rawKpi['monthly_progress_pct']))
    : rawKpi['pomodoroTargetRate'] !== undefined
      ? Number(rawKpi['pomodoroTargetRate'])
      : pomodoroCompleted > 0
        ? Math.min(100, Math.round(pomodoroCompleted * 1.25))
        : 0;

  const rawRecent = rawKpi['streak_history_last_7_days'] ?? rawKpi['recentStreak'];
  const recentStreak = Array.isArray(rawRecent)
    ? (rawRecent as boolean[])
    : [false, false, false, false, false, false, false];

  const kpi: DashboardKpi = {
    monthlyHours: isNaN(monthlyHours) ? 0 : monthlyHours,
    monthlyTarget: isNaN(monthlyTarget) ? 0 : monthlyTarget,
    weeklyCommitment: isNaN(weeklyCommitment) ? 0 : weeklyCommitment,
    streakDays: isNaN(streakDays) ? 0 : streakDays,
    streakRecord: isNaN(streakRecord) ? 0 : streakRecord,
    recentStreak,
    adherenceRate: isNaN(adherenceRate) ? 0 : adherenceRate,
    adherenceChange: isNaN(adherenceChange) ? 0 : adherenceChange,
    pomodoroCompleted: isNaN(pomodoroCompleted) ? 0 : pomodoroCompleted,
    pomodoroDeepWorkHours: isNaN(pomodoroDeepWorkHours) ? 0 : pomodoroDeepWorkHours,
    pomodoroTargetRate: isNaN(pomodoroTargetRate) ? 0 : pomodoroTargetRate,
  };

  // Study Distribution mapping
  const DAY_MAP: Record<string, { day: string; full: string }> = {
    Mon: { day: 'T2', full: 'Thứ Hai' },
    Tue: { day: 'T3', full: 'Thứ Ba' },
    Wed: { day: 'T4', full: 'Thứ Tư' },
    Thu: { day: 'T5', full: 'Thứ Năm' },
    Fri: { day: 'T6', full: 'Thứ Sáu' },
    Sat: { day: 'T7', full: 'Thứ Bảy' },
    Sun: { day: 'CN', full: 'Chủ Nhật' },
    T2: { day: 'T2', full: 'Thứ Hai' },
    T3: { day: 'T3', full: 'Thứ Ba' },
    T4: { day: 'T4', full: 'Thứ Tư' },
    T5: { day: 'T5', full: 'Thứ Năm' },
    T6: { day: 'T6', full: 'Thứ Sáu' },
    T7: { day: 'T7', full: 'Thứ Bảy' },
    CN: { day: 'CN', full: 'Chủ Nhật' },
  };

  const rawDist = payload['study_distribution'] ?? payload['studyDistribution'];
  const studyDistribution: DayStudyDistribution[] = Array.isArray(rawDist)
    ? rawDist.map((d: Record<string, unknown>) => {
        const label = String(d?.['day_label'] ?? d?.['day'] ?? '');
        const mapped = DAY_MAP[label] ?? {
          day: label || 'T2',
          full: String(d?.['full_day_name'] ?? d?.['fullDayName'] ?? label),
        };
        return {
          day: mapped.day,
          fullDayName: mapped.full,
          hours: Number(d?.['hours'] ?? 0),
          isToday: Boolean(d?.['is_today'] ?? d?.['isToday']),
          date: String(d?.['date'] ?? ''),
        };
      })
    : [...EMPTY_DASHBOARD_SUMMARY.studyDistribution];

  // Today queue mapping
  const rawQueue = payload['today_queue'] ?? payload['todayQueue'];
  const todayQueue: DashboardTodayQueueItem[] = Array.isArray(rawQueue)
    ? rawQueue.map((q: Record<string, unknown>) => {
        const rawStatus = String(q?.['status'] ?? '').toLowerCase();
        let status: 'active' | 'pending' | 'completed' | 'in_progress' = 'pending';
        if (rawStatus === 'in_progress') status = 'in_progress';
        else if (rawStatus === 'completed') status = 'completed';
        else if (rawStatus === 'ready' || rawStatus === 'active') status = 'active';

        return {
          id: String(q?.['id'] ?? ''),
          taskId: String(q?.['task_code'] ?? q?.['task_id'] ?? q?.['taskId'] ?? 'TASK'),
          title: String(q?.['title'] ?? 'Nhiệm vụ học tập'),
          roadmapTitle: String(q?.['roadmap_title'] ?? q?.['roadmapTitle'] ?? ''),
          milestoneTitle: String(q?.['milestone_title'] ?? q?.['milestoneTitle'] ?? 'Phiên học hôm nay'),
          scheduledTime: String(q?.['scheduled_time'] ?? q?.['scheduledTime'] ?? '08:00 - 09:30'),
          durationMinutes: Number(q?.['duration_minutes'] ?? q?.['durationMinutes'] ?? 90),
          pomodoroCount: Number(q?.['pomodoro_estimate'] ?? q?.['pomodoro_count'] ?? q?.['pomodoroCount'] ?? 2),
          status,
          urgency: (q?.['urgency'] ?? 'normal') as 'high' | 'medium' | 'normal',
        };
      })
    : [];

  // Schedule blocks mapping
  const rawBlocks = payload['schedule_blocks'] ?? payload['scheduleBlocks'];
  const scheduleBlocks: DashboardScheduleBlock[] = Array.isArray(rawBlocks)
    ? rawBlocks.map((b: Record<string, unknown>) => {
        const status = String(b?.['status'] ?? '');
        const rawType = b?.['type'] as DashboardScheduleBlock['type'];
        const type: DashboardScheduleBlock['type'] =
          rawType ?? (status === 'COMPLETED' ? 'completed' : status === 'IN_PROGRESS' ? 'live' : 'upcoming');

        return {
          id: String(b?.['id'] ?? ''),
          title: String(b?.['title'] ?? 'Khung giờ học'),
          type,
          dayOfWeek: Number(b?.['day_of_week'] ?? b?.['dayOfWeek'] ?? 1),
          dayLabel: String(b?.['day_label'] ?? b?.['dayLabel'] ?? 'T2'),
          startTime: String(b?.['start_time'] ?? b?.['startTime'] ?? '08:00'),
          endTime: String(b?.['end_time'] ?? b?.['endTime'] ?? '09:00'),
          code: String(b?.['roadmap_code'] ?? b?.['code'] ?? ''),
          room: String(b?.['room'] ?? ''),
          isLive: Boolean(b?.['is_live'] ?? b?.['isLive'] ?? (status === 'IN_PROGRESS')),
          description: String(b?.['description'] ?? ''),
          pomodoroCount: Number(b?.['pomodoro_count'] ?? b?.['pomodoroCount'] ?? 0),
          durationMinutes: Number(b?.['duration_minutes'] ?? b?.['durationMinutes'] ?? 0),
        };
      })
    : [];

  // AI insight mapping
  const rawAi = (payload['ai_insight'] as Record<string, unknown>) ?? (payload['aiInsight'] as Record<string, unknown>) ?? {};
  const aiInsight: DashboardAiInsight = {
    peakHourRange: String(rawAi['peak_hours'] ?? rawAi['peakHourRange'] ?? '09:00 - 11:30'),
    efficiencyChange: Number(rawAi['efficiency_growth_pct'] ?? rawAi['efficiencyChange'] ?? 0),
    suggestedBreak: String(rawAi['suggested_break'] ?? rawAi['suggestedBreak'] ?? '15 phút sau mỗi 2 phiên Pomodoro'),
    summary: String(rawAi['message'] ?? rawAi['summary'] ?? 'AI đồng bộ và theo dõi tiến độ học tập hàng ngày.'),
    recommendations: Array.isArray(rawAi['recommendations']) && rawAi['recommendations'].length > 0
      ? (rawAi['recommendations'] as string[])
      : ['Nên hoàn thành các phiên học trong khung giờ rảnh tối ưu để nâng cao hiệu quả hấp thu kiến thức.'],
  };

  // Adaptation status mapping
  const rawAdapt = (payload['adaptation_status'] as Record<string, unknown>) ?? (payload['adaptationStatus'] as Record<string, unknown>) ?? {};
  const adaptationStatus: DashboardAdaptationStatus = {
    hasDominoShift: Boolean(rawAdapt['domino_shift_ready'] ?? rawAdapt['hasDominoShift']),
    affectedTasksCount: Number(rawAdapt['affected_tasks_count'] ?? rawAdapt['affectedTasksCount'] ?? 0),
    rescheduleReason: String(rawAdapt['reschedule_reason'] ?? rawAdapt['rescheduleReason'] ?? ''),
    needsAttention: !(rawAdapt['is_balanced'] ?? !rawAdapt['needsAttention']),
    alertMessage: String(rawAdapt['message'] ?? rawAdapt['alertMessage'] ?? 'Lịch trình học tập hiện tại cân bằng.'),
  };

  const currentWeek = (payload['current_week'] as DashboardSummary['currentWeek']) ??
    (payload['currentWeek'] as DashboardSummary['currentWeek']) ?? {
      weekNumber: 1,
      startDate: '',
      endDate: '',
    };

  return {
    kpi,
    activeRoadmaps,
    todayQueue,
    studyDistribution,
    scheduleBlocks,
    aiInsight,
    adaptationStatus,
    currentWeek,
    activeRoadmapTitle: activeRoadmaps[0]?.title ?? '',
    totalMilestones: Number(
      payload['total_milestones'] ??
        payload['totalMilestones'] ??
        activeRoadmaps.reduce((acc, r) => acc + (r.totalTasks || 0), 0)
    ),
    completedMilestones: Number(
      payload['completed_milestones'] ??
        payload['completedMilestones'] ??
        activeRoadmaps.reduce((acc, r) => acc + (r.completedTasks || 0), 0)
    ),
    totalStudyHours: kpi.monthlyHours,
    weeklyTargetHours: weeklyCommitment,
    streakDays: kpi.streakDays,
    upcomingTasks: todayQueue.map((q) => ({
      id: q.id,
      title: q.title,
      milestoneTitle: q.milestoneTitle,
      scheduledDate: q.scheduledTime,
      pomodoroEstimate: q.pomodoroCount,
      isCompleted: q.status === 'completed',
    })),
  };
}

@Injectable({
  providedIn: 'root',
})
export class DashboardService {
  private readonly http = inject(HttpClient);

  readonly summary = signal<DashboardSummary>(EMPTY_DASHBOARD_SUMMARY);
  readonly currentState = signal<DashboardDataState>('normal');
  readonly isLoading = signal<boolean>(false);
  readonly weekOffset = signal<number>(0);

  loadSummary(): Observable<DashboardSummary> {
    this.isLoading.set(true);
    return this.http.get<unknown>('/api/v1/evaluation/dashboard-summary').pipe(
      map((data) => mapDashboardSummary(data)),
      tap({
        next: (mapped) => {
          this.summary.set(mapped);
          this.isLoading.set(false);
        },
        error: () => {
          this.summary.set(EMPTY_DASHBOARD_SUMMARY);
          this.isLoading.set(false);
        },
      }),
      catchError(() => {
        this.summary.set(EMPTY_DASHBOARD_SUMMARY);
        this.isLoading.set(false);
        return of(EMPTY_DASHBOARD_SUMMARY);
      })
    );
  }

  setState(state: DashboardDataState): void {
    this.currentState.set(state);
    if (state === 'new-user') {
      const current = this.summary();
      this.summary.set({
        ...current,
        activeRoadmaps: [],
        todayQueue: [],
        scheduleBlocks: [],
      });
    } else if (state === 'unscheduled') {
      const current = this.summary();
      this.summary.set({
        ...current,
        scheduleBlocks: [],
        todayQueue: [],
      });
    } else if (state === 'empty-week') {
      const current = this.summary();
      this.summary.set({
        ...current,
        scheduleBlocks: [],
      });
    }
  }

  setWeekOffset(offset: number): void {
    this.weekOffset.set(offset);
  }
}
