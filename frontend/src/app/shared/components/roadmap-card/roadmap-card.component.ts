import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { RoadmapResponse } from '../../../features/roadmaps/models/roadmap.model';
import { DashboardActiveRoadmap } from '../../../features/dashboard/models/dashboard.model';

export type RoadmapCardVariant = 'compact' | 'full';

export interface GenericRoadmapData {
  id: string;
  title: string;
  description?: string | null;
  category?: string;
  status?: string;
  progressPercentage?: number;
  nextTaskTitle?: string;
  completedTasks?: number;
  totalTasks?: number;
  deadline?: string;
  start_date?: string | null;
  target_date?: string | null;
  created_at?: string;
  updated_at?: string;
  tags?: string[];
}

export type RoadmapCardInput = RoadmapResponse | DashboardActiveRoadmap | GenericRoadmapData;

@Component({
  selector: 'app-roadmap-card',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './roadmap-card.component.html',
  styleUrl: './roadmap-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'block h-full',
  },
})
export class RoadmapCardComponent {
  readonly roadmap = input.required<RoadmapCardInput>();
  readonly variant = input<RoadmapCardVariant>('full');

  readonly selectRoadmap = output<string>();
  readonly pauseRoadmap = output<string>();
  readonly resumeRoadmap = output<string>();
  readonly archive = output<string>();
  readonly viewDetails = output<string>();

  readonly showMenu = signal<boolean>(false);

  readonly status = computed<'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'INITIALIZED'>(() => {
    const rm = this.roadmap();
    const rawStatus = 'status' in rm && typeof rm.status === 'string' ? rm.status : 'ACTIVE';
    const normalized = rawStatus.toUpperCase();
    if (normalized === 'PAUSED') return 'PAUSED';
    if (normalized === 'COMPLETED' || normalized === 'ARCHIVED') return 'COMPLETED';
    if (normalized === 'INITIALIZED') return 'INITIALIZED';
    return 'ACTIVE';
  });

  readonly progress = computed<number>(() => {
    const rm = this.roadmap();
    if ('progressPercentage' in rm && typeof rm.progressPercentage === 'number') {
      return rm.progressPercentage;
    }
    if (
      'completedTasks' in rm &&
      'totalTasks' in rm &&
      typeof rm.completedTasks === 'number' &&
      typeof rm.totalTasks === 'number' &&
      rm.totalTasks > 0
    ) {
      return Math.round((rm.completedTasks / rm.totalTasks) * 100);
    }
    const st = this.status();
    if (st === 'COMPLETED') return 100;
    return 0;
  });

  readonly taskRatio = computed<string>(() => {
    const rm = this.roadmap();
    if (
      'completedTasks' in rm &&
      'totalTasks' in rm &&
      typeof rm.completedTasks === 'number' &&
      typeof rm.totalTasks === 'number'
    ) {
      return `(${rm.completedTasks}/${rm.totalTasks} Tasks)`;
    }
    return '(0/0 Tasks)';
  });

  readonly tags = computed<string[]>(() => {
    const rm = this.roadmap();
    if ('tags' in rm && Array.isArray(rm.tags) && rm.tags.length > 0) {
      return rm.tags;
    }
    if ('category' in rm && typeof rm.category === 'string' && rm.category.trim()) {
      return [rm.category.trim()];
    }
    return ['Lộ trình tự học'];
  });

  readonly timeCommitment = computed<string>(() => {
    const rm = this.roadmap();
    if ('totalTasks' in rm && typeof rm.totalTasks === 'number' && rm.totalTasks > 0) {
      return `${rm.totalTasks} tác vụ`;
    }
    if (this.status() === 'COMPLETED') {
      return 'Đã hoàn tất';
    }
    return 'Lịch rảnh Mode A/B';
  });

  readonly currentMilestone = computed<string>(() => {
    const rm = this.roadmap();
    if ('nextTaskTitle' in rm && rm.nextTaskTitle) return rm.nextTaskTitle;
    const st = this.status();
    if (st === 'PAUSED') return 'Đang tạm dừng — chờ kích hoạt lại';
    if (st === 'COMPLETED') return 'Đã hoàn thành toàn bộ cột mốc';
    return 'Đang thực thi theo lịch chính thức';
  });

  readonly remainingDaysText = computed<string>(() => {
    const rm = this.roadmap();
    const targetDate = 'target_date' in rm ? rm.target_date : ('deadline' in rm ? rm.deadline : null);
    if (!targetDate) return 'Chưa đặt hạn';
    try {
      const target = new Date(targetDate);
      if (isNaN(target.getTime())) return targetDate;
      const now = new Date();
      const diffMs = target.getTime() - now.getTime();
      const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
      if (diffDays > 0) return `(Còn ${diffDays} ngày)`;
      if (diffDays === 0) return '(Đến hạn hôm nay)';
      return `(Quá hạn ${Math.abs(diffDays)} ngày)`;
    } catch {
      return '';
    }
  });

  readonly formattedDate = computed<string>(() => {
    const rm = this.roadmap();
    const dateStr = 'target_date' in rm ? rm.target_date : ('deadline' in rm ? rm.deadline : null);
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('vi-VN');
    } catch {
      return dateStr;
    }
  });

  readonly completedDate = computed<string>(() => {
    const rm = this.roadmap();
    const dateStr = 'target_date' in rm && rm.target_date ? rm.target_date : ('updated_at' in rm ? rm.updated_at : null);
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('vi-VN');
    } catch {
      return dateStr;
    }
  });

  readonly completedRating = computed<string>(() => 'Hoàn thành 100% mục tiêu');

  readonly category = computed<string>(() => {
    const rm = this.roadmap();
    if ('category' in rm && rm.category) return rm.category;
    return this.tags()[0] || 'Lộ trình';
  });

  readonly description = computed<string>(() => {
    const rm = this.roadmap();
    if ('description' in rm && rm.description) return rm.description;
    return 'Lộ trình học tập thích ứng phân rã theo đồ thị DAG và đồng bộ lịch rảnh cá nhân.';
  });

  toggleMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.showMenu.update(v => !v);
  }

  closeMenu(): void {
    this.showMenu.set(false);
  }

  onPause(event?: MouseEvent): void {
    event?.stopPropagation();
    this.closeMenu();
    this.pauseRoadmap.emit(this.roadmap().id);
  }

  onResume(event?: MouseEvent): void {
    event?.stopPropagation();
    this.closeMenu();
    this.resumeRoadmap.emit(this.roadmap().id);
  }

  onArchive(event?: MouseEvent): void {
    event?.stopPropagation();
    this.closeMenu();
    this.archive.emit(this.roadmap().id);
  }

  onSelect(): void {
    this.selectRoadmap.emit(this.roadmap().id);
  }

  onViewDetails(event?: MouseEvent): void {
    event?.stopPropagation();
    this.viewDetails.emit(this.roadmap().id);
  }
}
