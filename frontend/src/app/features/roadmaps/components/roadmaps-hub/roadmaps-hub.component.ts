import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { RoadmapService } from '../../services/roadmap.service';
import { AuthService } from '../../../../core/services/auth.service';
import { RoadmapResponse } from '../../models/roadmap.model';

export type RoadmapStatusFilter = 'ALL' | 'ACTIVE' | 'PAUSED' | 'COMPLETED';
export type ViewMode = 'grid' | 'list';

export interface StarterTemplate {
  id: string;
  title: string;
  subtitle: string;
  categoryTag: string;
  weeksCount: number;
  tasksCount: number;
  knowledgeLevel: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';
  hoursPerWeek: number;
  tags: string[];
}

@Component({
  selector: 'app-roadmaps-hub',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './roadmaps-hub.component.html',
  styleUrl: './roadmaps-hub.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoadmapsHubComponent implements OnInit {
  readonly roadmapService = inject(RoadmapService);
  readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly activeFilter = signal<RoadmapStatusFilter>('ALL');
  readonly searchQuery = signal<string>('');
  readonly viewMode = signal<ViewMode>('grid');

  readonly currentUser = this.authService.currentUser;

  readonly starterTemplates: StarterTemplate[] = [
    {
      id: 'fastapi-microservices',
      title: 'FastAPI & Microservices',
      subtitle:
        'Chinh phục Ports & Adapters, Asyncpg, Taskiq và triển khai Docker theo chuẩn kiến trúc sạch.',
      categoryTag: 'Backend',
      weeksCount: 12,
      tasksCount: 84,
      knowledgeLevel: 'INTERMEDIATE',
      hoursPerWeek: 12,
      tags: ['Backend', 'Python', 'Hexagonal Architecture'],
    },
    {
      id: 'aws-solutions-architect',
      title: 'AWS Solutions Architect',
      subtitle:
        'Làm chủ VPC, IAM, ECS Fargate, S3, RDS và thiết kế hệ thống đám mây High Availability.',
      categoryTag: 'Cloud Arch',
      weeksCount: 8,
      tasksCount: 56,
      knowledgeLevel: 'BEGINNER',
      hoursPerWeek: 8,
      tags: ['Cloud Arch', 'DevOps', 'AWS'],
    },
    {
      id: 'ielts-academic-75',
      title: 'IELTS Academic Band 7.5',
      subtitle:
        'Rèn phản xạ Writing Task 2 và Speaking Part 3 theo chuẩn học thuật chuyên sâu và phương pháp Monastic.',
      categoryTag: 'Academic',
      weeksCount: 10,
      tasksCount: 70,
      knowledgeLevel: 'INTERMEDIATE',
      hoursPerWeek: 10,
      tags: ['Academic', 'IELTS', 'Writing & Speaking'],
    },
  ];

  readonly userInitials = computed<string>(() => {
    const user = this.currentUser();
    if (!user || !user.fullName) {
      return 'SV';
    }
    const parts = user.fullName.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  });

  readonly totalCount = computed<number>(() => this.roadmapService.roadmaps().length);

  readonly activeCount = computed<number>(
    () => this.roadmapService.roadmaps().filter(r => r.status === 'ACTIVE').length
  );

  readonly pausedCount = computed<number>(
    () => this.roadmapService.roadmaps().filter(r => r.status === 'PAUSED').length
  );

  readonly completedCount = computed<number>(
    () => this.roadmapService.roadmaps().filter(r => r.status === 'COMPLETED').length
  );

  readonly filteredRoadmaps = computed<RoadmapResponse[]>(() => {
    const list = this.roadmapService.roadmaps();
    const filter = this.activeFilter();
    const query = this.searchQuery().trim().toLowerCase();

    return list.filter(item => {
      // Status filter
      if (filter === 'ACTIVE' && item.status !== 'ACTIVE') return false;
      if (filter === 'PAUSED' && item.status !== 'PAUSED') return false;
      if (filter === 'COMPLETED' && item.status !== 'COMPLETED') return false;

      // Search query
      if (query) {
        const titleMatch = item.title?.toLowerCase().includes(query) ?? false;
        const descMatch = item.description?.toLowerCase().includes(query) ?? false;
        if (!titleMatch && !descMatch) return false;
      }

      return true;
    });
  });

  @HostListener('window:keydown', ['$event'])
  onGlobalKeydown(event: KeyboardEvent): void {
    if (
      (event.key === 'c' || event.key === 'C') &&
      !['INPUT', 'TEXTAREA', 'SELECT'].includes((event.target as HTMLElement)?.tagName) &&
      !event.ctrlKey &&
      !event.metaKey &&
      !event.altKey
    ) {
      this.router.navigate(['/roadmaps/new']);
    }
  }

  ngOnInit(): void {
    this.roadmapService.loadRoadmaps();
  }

  setFilter(filter: RoadmapStatusFilter): void {
    this.activeFilter.set(filter);
  }

  setViewMode(mode: ViewMode): void {
    this.viewMode.set(mode);
  }

  onSearchChange(query: string): void {
    this.searchQuery.set(query);
  }

  getRemainingDays(targetDate?: string | null): string {
    if (!targetDate) {
      return 'Chưa đặt hạn';
    }
    const target = new Date(targetDate);
    const now = new Date();
    const diffMs = target.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays > 0) {
      return `(Còn ${diffDays} ngày)`;
    } else if (diffDays === 0) {
      return '(Đến hạn hôm nay)';
    } else {
      return `(Quá hạn ${Math.abs(diffDays)} ngày)`;
    }
  }

  getProgressPercent(roadmap: RoadmapResponse): number {
    if (roadmap.status === 'COMPLETED') return 100;
    if (roadmap.status === 'PAUSED') return 28;
    return 48;
  }

  getTaskRatio(roadmap: RoadmapResponse): string {
    if (roadmap.status === 'COMPLETED') return '(20/20 Tasks)';
    if (roadmap.status === 'PAUSED') return '(7/25 Tasks)';
    return '(12/25 Tasks)';
  }

  getTags(roadmap: RoadmapResponse): string[] {
    const title = roadmap.title.toLowerCase();
    if (title.includes('fastapi') || title.includes('python')) {
      return ['Backend', 'Python', 'Hexagonal Architecture'];
    }
    if (title.includes('aws') || title.includes('cloud')) {
      return ['Cloud', 'DevOps', 'AWS'];
    }
    if (title.includes('angular') || title.includes('frontend')) {
      return ['Frontend', 'Angular 21', 'TypeScript'];
    }
    if (title.includes('ielts') || title.includes('english')) {
      return ['Ngoại ngữ', 'IELTS', 'Academic'];
    }
    return ['Lộ trình', 'Tự học', 'AI Powered'];
  }

  getTimeCommitment(roadmap: RoadmapResponse): string {
    if (roadmap.status === 'PAUSED') return '8 giờ / tuần';
    if (roadmap.status === 'COMPLETED') return '48 giờ học';
    return '12 giờ / tuần';
  }

  getCurrentMilestone(roadmap: RoadmapResponse): string {
    if (roadmap.status === 'PAUSED') return 'Chờ kích hoạt lại khi hoàn thành Master FastAPI';
    if (roadmap.status === 'COMPLETED') return 'Đã hoàn thành toàn bộ cột mốc';
    return 'Mốc 2: Ports & Adapters';
  }

  getBiorhythm(roadmap: RoadmapResponse): string {
    return 'Evening Flow (20:00 - 22:00)';
  }

  formatDate(dateStr?: string | null): string {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('vi-VN');
    } catch {
      return dateStr;
    }
  }

  getCompletedRating(roadmap: RoadmapResponse): string {
    const title = roadmap.title.toLowerCase();
    if (title.includes('ielts')) return 'Target 7.5 Đạt chuẩn';
    return 'Xuất sắc (9.2/10)';
  }

  getCompletedDate(roadmap: RoadmapResponse): string {
    if (roadmap.target_date) return this.formatDate(roadmap.target_date);
    return this.formatDate(roadmap.updated_at);
  }

  onResumeRoadmap(id: string): void {
    this.router.navigate(['/workspace']);
  }

  onReactivateRoadmap(id: string): void {
    this.router.navigate(['/roadmaps', id]);
  }

  onViewSummaryReport(id: string): void {
    this.router.navigate(['/analytics']);
  }
}
