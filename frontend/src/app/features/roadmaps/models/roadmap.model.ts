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
  status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED';
  hoursPerWeek: number;
  milestones: Milestone[];
  createdAt: string;
}

export interface GenerateRoadmapPayload {
  goal: string;
  hoursPerWeek: number;
  currentLevel: string;
}
