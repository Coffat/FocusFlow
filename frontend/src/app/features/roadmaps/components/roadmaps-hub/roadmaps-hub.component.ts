import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';
import { RoadmapService } from '../../services/roadmap.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AvailabilityService } from '../../../../core/services/availability.service';
import { PlanningStep, PriorKnowledgeLevel, RoadmapResponse } from '../../models/roadmap.model';
import { KpiCardComponent } from '../../../../shared/components/kpi-card/kpi-card.component';
import { RoadmapCardComponent } from '../../../../shared/components/roadmap-card/roadmap-card.component';
import {
  BlueprintEmptyStateComponent,
  DEFAULT_STARTER_TEMPLATES,
  StarterTemplate,
} from '../../../../shared/components/blueprint-empty-state/blueprint-empty-state.component';
import { RoadmapWizardHostComponent } from '../dialogs/roadmap-wizard-host/roadmap-wizard-host.component';
import {
  AdaptationConfirmEvent,
  AdaptationModalDialogComponent,
} from '../dialogs/adaptation-modal-dialog/adaptation-modal-dialog.component';
import { PrerequisiteAvailabilityDialogComponent } from '../dialogs/prerequisite-availability-dialog/prerequisite-availability-dialog.component';

export type RoadmapStatusFilter = 'ALL' | 'ACTIVE' | 'PAUSED' | 'COMPLETED';
export type ViewMode = 'grid' | 'list';

@Component({
  selector: 'app-roadmaps-hub',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    KpiCardComponent,
    RoadmapCardComponent,
    BlueprintEmptyStateComponent,
    RoadmapWizardHostComponent,
    AdaptationModalDialogComponent,
    PrerequisiteAvailabilityDialogComponent,
  ],
  templateUrl: './roadmaps-hub.component.html',
  styleUrl: './roadmaps-hub.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoadmapsHubComponent implements OnInit {
  readonly roadmapService = inject(RoadmapService);
  readonly authService = inject(AuthService);
  readonly availabilityService = inject(AvailabilityService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly confirmationService = inject(ConfirmationService, { optional: true });
  private readonly messageService = inject(MessageService, { optional: true });

  readonly activeFilter = signal<RoadmapStatusFilter>('ALL');
  readonly searchQuery = signal<string>('');
  readonly viewMode = signal<ViewMode>('grid');

  // Prerequisite Availability Dialog State
  readonly prerequisiteDialogOpen = signal<boolean>(false);

  // 5-Step Wizard Dialog State
  readonly wizardOpen = signal<boolean>(false);
  readonly wizardStep = signal<PlanningStep>(1);
  readonly wizardInitialTitle = signal<string>('');
  readonly wizardInitialLevel = signal<PriorKnowledgeLevel>('BEGINNER');
  readonly wizardInitialWeeklyHours = signal<number>(12);

  // SCR-08 Adaptation Modal Dialog State
  readonly adaptationModalOpen = signal<boolean>(false);
  readonly adaptationRoadmapId = signal<string | null>(null);
  readonly adaptationRoadmapTitle = signal<string>('');

  readonly starterTemplates: readonly StarterTemplate[] = DEFAULT_STARTER_TEMPLATES;

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
      if (filter === 'ACTIVE' && item.status !== 'ACTIVE') return false;
      if (filter === 'PAUSED' && item.status !== 'PAUSED') return false;
      if (filter === 'COMPLETED' && item.status !== 'COMPLETED') return false;

      if (query) {
        const titleMatch = item.title?.toLowerCase().includes(query) ?? false;
        const descMatch = item.description?.toLowerCase().includes(query) ?? false;
        if (!titleMatch && !descMatch) return false;
      }

      return true;
    });
  });

  ngOnInit(): void {
    this.roadmapService.loadRoadmaps();

    const autoOpen = this.route.snapshot.queryParamMap.get('autoOpen');
    if (autoOpen === 'true') {
      this.openCreateWizard(1);
      const queryParams = { ...this.route.snapshot.queryParams };
      delete queryParams['autoOpen'];
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams,
        replaceUrl: true,
      });
    }
  }

  checkAvailabilityAndProceed(action: () => void): void {
    this.availabilityService.checkPrerequisites((ready) => {
      if (!ready) {
        this.prerequisiteDialogOpen.set(true);
      } else {
        action();
      }
    });
  }

  closePrerequisiteDialog(): void {
    this.prerequisiteDialogOpen.set(false);
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

  openCreateWizard(step: PlanningStep = 1): void {
    this.checkAvailabilityAndProceed(() => {
      this.wizardInitialTitle.set('');
      this.wizardInitialLevel.set('BEGINNER');
      this.wizardInitialWeeklyHours.set(12);
      this.wizardStep.set(step);
      this.wizardOpen.set(true);
    });
  }

  closeCreateWizard(): void {
    this.wizardOpen.set(false);
  }

  onRoadmapApplied(_roadmapId: string): void {
    this.wizardOpen.set(false);
    if (this.activeFilter() !== 'ALL') {
      this.activeFilter.set('ALL');
    }
    this.messageService?.add({
      severity: 'success',
      summary: 'Áp dụng lộ trình thành công',
      detail: 'Lộ trình học tập mới đã được kích hoạt và đồng bộ vào danh sách.',
    });
    if (!this.roadmapService.loading()) {
      this.roadmapService.loadRoadmaps();
    }
  }

  onSelectTemplate(tpl: StarterTemplate): void {
    this.checkAvailabilityAndProceed(() => {
      this.wizardInitialTitle.set(tpl.title);
      this.wizardInitialLevel.set(tpl.knowledgeLevel ?? 'BEGINNER');
      this.wizardInitialWeeklyHours.set(tpl.hoursPerWeek ?? 12);
      this.wizardStep.set(1);
      this.wizardOpen.set(true);
    });
  }

  onCreateCustomRoadmap(): void {
    this.openCreateWizard(1);
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

  private extractHttpErrorMessage(err: unknown, fallback: string): string {
    if (err instanceof HttpErrorResponse) {
      const body = err.error;
      if (typeof body === 'string' && body.trim().length > 0) {
        return body.trim();
      }
      if (body && typeof body === 'object') {
        const record = body as Record<string, unknown>;
        if (typeof record['message'] === 'string' && record['message'].trim().length > 0) {
          return record['message'].trim();
        }
        if (typeof record['detail'] === 'string' && record['detail'].trim().length > 0) {
          return record['detail'].trim();
        }
      }
      if (typeof err.message === 'string' && err.message.trim().length > 0) {
        return err.message.trim();
      }
    }
    return fallback;
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
      error: (err: unknown) => {
        this.messageService?.add({
          severity: 'error',
          summary: 'Tạm dừng thất bại',
          detail: this.extractHttpErrorMessage(
            err,
            'Không thể tạm dừng lộ trình. Vui lòng thử lại.'
          ),
        });
      },
    });
  }

  onResumeRoadmap(id: string): void {
    this.openAdaptationModal(id);
  }

  openAdaptationModal(roadmapId?: string): void {
    const list = this.roadmapService.roadmaps();
    const target =
      (roadmapId ? list.find(r => r.id === roadmapId) : null) ??
      list.find(r => r.status === 'PAUSED') ??
      list[0] ??
      null;

    this.adaptationRoadmapId.set(target?.id ?? roadmapId ?? null);
    this.adaptationRoadmapTitle.set(target?.title ?? '');
    this.adaptationModalOpen.set(true);
  }

  closeAdaptationModal(): void {
    this.adaptationModalOpen.set(false);
  }

  onConfirmAdaptation(event: AdaptationConfirmEvent): void {
    this.adaptationModalOpen.set(false);
    const id = event.roadmapId ?? this.adaptationRoadmapId();
    if (id && (event.strategy === 'DOMINO_SHIFT' || event.strategy === 'COMPACT_REBALANCE')) {
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
      error: (err: unknown) => {
        this.messageService?.add({
          severity: 'error',
          summary: 'Kích hoạt lại thất bại',
          detail: this.extractHttpErrorMessage(
            err,
            'Không thể kích hoạt lại lộ trình. Vui lòng thử lại.'
          ),
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
          this.executeArchive(id);
        },
      });
    } else {
      this.executeArchive(id);
    }
  }

  private executeArchive(id: string): void {
    this.roadmapService.archiveRoadmap(id, {
      onSuccess: () => {
        this.messageService?.add({
          severity: 'info',
          summary: 'Đã lưu trữ',
          detail: 'Lộ trình đã được lưu trữ thành công.',
        });
      },
      onError: (detail: string) => {
        this.messageService?.add({
          severity: 'error',
          summary: 'Lưu trữ thất bại',
          detail,
        });
      },
    });
  }
}
