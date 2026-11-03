export interface BacklogTask {
  id: string;
  roadmapId: string;
  milestoneId: string;
  title: string;
  description: string;
  pomodoroEstimate: number;
  pomodorosCompleted: number;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'PENDING' | 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'OVERDUE';
}
