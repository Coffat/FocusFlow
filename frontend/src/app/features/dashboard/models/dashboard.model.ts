export interface DashboardSummary {
  activeRoadmapTitle: string;
  totalMilestones: number;
  completedMilestones: number;
  totalStudyHours: number;
  weeklyTargetHours: number;
  streakDays: number;
  upcomingTasks: UpcomingTaskSummary[];
}

export interface UpcomingTaskSummary {
  id: string;
  title: string;
  milestoneTitle: string;
  scheduledDate: string;
  pomodoroEstimate: number;
  isCompleted: boolean;
}
