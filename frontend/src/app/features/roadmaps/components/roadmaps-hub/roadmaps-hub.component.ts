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
import { ConfirmationService, MessageService } from 'primeng/api';
import { RoadmapService } from '../../services/roadmap.service';
import { AuthService } from '../../../../core/services/auth.service';
import { RoadmapResponse } from '../../models/roadmap.model';
import { KpiCardComponent } from '../../../../shared/components/kpi-card/kpi-card.component';
import { RoadmapCardComponent } from '../../../../shared/components/roadmap-card/roadmap-card.component';
import {
  BlueprintEmptyStateComponent,
  StarterTemplate,
} from '../../../../shared/components/blueprint-empty-state/blueprint-empty-state.component';

export type RoadmapStatusFilter = 'ALL' | 'ACTIVE' | 'PAUSED' | 'COMPLETED';
export type ViewMode = 'grid' | 'list';

@Component({
  selector: 'app-roadmaps-hub',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    KpiCardComponent,
    RoadmapCardComponent,
    BlueprintEmptyStateComponent,
  ],
  templateUrl: './roadmaps-hub.component.html',
  styleUrl: './roadmaps-hub.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoadmapsHubComponent implements OnInit {
  readonly roadmapService = inject(RoadmapService);
  readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly confirmationService = inject(ConfirmationService, { optional: true });
  private readonly messageService = inject(MessageService, { optional: true });

  readonly activeFilter = signal<RoadmapStatusFilter>('ALL');
  readonly searchQuery = signal<string>('');
  readonly viewMode = signal<ViewMode>('grid');

  readonly currentUser = this.authService.currentUser;

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

  getTags(roadmap: RoadmapResponse): string[] {
    const title = (roadmap.title || '').toLowerCase();
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

  onPauseRoadmap(id: string): void {
    if (this.confirmationService) {
      this.confirmationService.confirm({
        header: 'Xác nhận Tạm dừng Lộ trình',
        message:
          'Bạn có chắc chắn muốn tạm dừng lộ trình này? Lịch học sẽ tạm đóng băng và tự động tịnh tiến qua cơ chế Domino Shift v2 khi kích hoạt lại.',
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: 'Tạm dừng',
        rejectLabel: 'Hủy bỏ',
        acceptButtonStyleClass: 'p-button-warning',
        accept: () => {
          this.executePause(id);
        },
      });
    } else {
      this.executePause(id);
    }
  }

  private executePause(id: string): void {
    this.roadmapService.pauseRoadmap(id).subscribe({
      next: () => {
        this.messageService?.add({
          severity: 'warn',
          summary: 'Đã tạm dừng',
          detail: 'Lộ trình đã chuyển sang trạng thái tạm dừng (Domino Shift v2).',
        });
        this.roadmapService.loadRoadmaps();
      },
      error: () => {
        // Fallback for local reactive update or offline mock
        this.roadmapService.roadmaps.update(list =>
          list.map(r => (r.id === id ? { ...r, status: 'PAUSED' } : r))
        );
        this.messageService?.add({
          severity: 'warn',
          summary: 'Đã tạm dừng',
          detail: 'Lộ trình đã được tạm dừng (Domino Shift v2).',
        });
      },
    });
  }

  onResumeRoadmap(id: string): void {
    if (this.confirmationService) {
      this.confirmationService.confirm({
        header: 'Xác nhận Kích hoạt Lại Lộ trình',
        message:
          'Bạn muốn kích hoạt lại lộ trình này? Các mốc thời gian học sẽ tự động được điều phối lại.',
        icon: 'pi pi-info-circle',
        acceptLabel: 'Kích hoạt lại',
        rejectLabel: 'Hủy bỏ',
        acceptButtonStyleClass: 'p-button-success',
        accept: () => {
          this.executeResume(id);
        },
      });
    } else {
      this.executeResume(id);
    }
  }

  private executeResume(id: string): void {
    this.roadmapService.resumeRoadmap(id).subscribe({
      next: () => {
        this.messageService?.add({
          severity: 'success',
          summary: 'Đã kích hoạt',
          detail: 'Lộ trình đã hoạt động trở lại.',
        });
        this.roadmapService.loadRoadmaps();
      },
      error: () => {
        // Fallback for local reactive update or offline mock
        this.roadmapService.roadmaps.update(list =>
          list.map(r => (r.id === id ? { ...r, status: 'ACTIVE' } : r))
        );
        this.messageService?.add({
          severity: 'success',
          summary: 'Đã kích hoạt',
          detail: 'Lộ trình đã hoạt động trở lại.',
        });
      },
    });
  }

  onArchiveRoadmap(id: string): void {
    if (this.confirmationService) {
      this.confirmationService.confirm({
        header: 'Xác nhận Lưu trữ Lộ trình',
        message:
          'Lưu trữ lộ trình này? Lộ trình sẽ chuyển sang trạng thái chỉ đọc (ARCHIVED) và không nhận thêm lịch học mới.',
        icon: 'pi pi-exclamation-circle',
        acceptLabel: 'Lưu trữ',
        rejectLabel: 'Hủy bỏ',
        acceptButtonStyleClass: 'p-button-danger',
        accept: () => {
          this.roadmapService.archiveRoadmap(id);
          this.messageService?.add({
            severity: 'info',
            summary: 'Đã lưu trữ',
            detail: 'Lộ trình đã được lưu trữ thành công.',
          });
        },
      });
    } else {
      this.roadmapService.archiveRoadmap(id);
    }
  }

  onSelectTemplate(tpl: StarterTemplate): void {
    this.router.navigate(['/roadmaps/new'], { queryParams: { goal: tpl.title } });
  }

  onCreateCustomRoadmap(): void {
    this.router.navigate(['/roadmaps/new']);
  }
}
