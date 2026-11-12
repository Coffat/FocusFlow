export type DashboardDataState = 'normal' | 'new-user' | 'unscheduled' | 'empty-week';

export interface DashboardKpi {
  monthlyHours: number;
  monthlyTarget: number;
  weeklyCommitment: number;
  streakDays: number;
  streakRecord: number;
  recentStreak: boolean[];
  adherenceRate: number;
  adherenceChange: number;
  pomodoroCompleted: number;
  pomodoroDeepWorkHours: number;
  pomodoroTargetRate: number;
}

export interface DayStudyDistribution {
  day: string;
  fullDayName: string;
  hours: number;
  isToday: boolean;
  date?: string;
}

export interface DashboardActiveRoadmap {
  id: string;
  title: string;
  category: string;
  progressPercentage: number;
  totalTasks: number;
  completedTasks: number;
  nextTaskTitle: string;
  deadline: string;
  updatedAt?: string;
  commitmentHoursPerWeek?: number;
}

export interface DashboardTodayQueueItem {
  id: string;
  taskId: string;
  title: string;
  roadmapTitle: string;
  milestoneTitle: string;
  scheduledTime: string;
  durationMinutes: number;
  pomodoroCount: number;
  status: 'active' | 'pending' | 'completed' | 'in_progress';
  urgency: 'high' | 'medium' | 'normal';
}

export interface DashboardAiInsight {
  peakHourRange: string;
  efficiencyChange: number;
  suggestedBreak: string;
  summary: string;
  recommendations: string[];
}

export interface DashboardAdaptationStatus {
  hasDominoShift: boolean;
  affectedTasksCount: number;
  rescheduleReason: string;
  needsAttention: boolean;
  alertMessage: string;
}

export interface DashboardScheduleBlock {
  id: string;
  title: string;
  type: 'university' | 'completed' | 'live' | 'upcoming' | 'domino_proposal';
  dayOfWeek: number; // 1: T2, 2: T3, 3: T4, 4: T5, 5: T6, 6: T7, 7: CN
  dayLabel: string; // 'T2' | 'T3' | 'T4' | 'T5' | 'T6' | 'T7' | 'CN'
  startTime: string; // '08:00'
  endTime: string; // '10:00'
  code?: string;
  room?: string;
  isLive?: boolean;
  description?: string;
  pomodoroCount?: number;
  durationMinutes?: number;
}

export interface UpcomingTaskSummary {
  id: string;
  title: string;
  milestoneTitle: string;
  scheduledDate: string;
  pomodoroEstimate: number;
  isCompleted: boolean;
}

export interface DashboardSummary {
  kpi: DashboardKpi;
  activeRoadmaps: DashboardActiveRoadmap[];
  todayQueue: DashboardTodayQueueItem[];
  studyDistribution: DayStudyDistribution[];
  scheduleBlocks: DashboardScheduleBlock[];
  aiInsight: DashboardAiInsight;
  adaptationStatus: DashboardAdaptationStatus;
  currentWeek: {
    weekNumber: number;
    startDate: string;
    endDate: string;
  };
  // Backwards compatibility fields
  activeRoadmapTitle?: string;
  totalMilestones?: number;
  completedMilestones?: number;
  totalStudyHours?: number;
  weeklyTargetHours?: number;
  streakDays?: number;
  upcomingTasks?: UpcomingTaskSummary[];
}
