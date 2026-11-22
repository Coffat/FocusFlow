import {
  Component,
  OnInit,
  inject,
  ChangeDetectionStrategy,
  HostListener,
  signal,
  computed,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs';
import { MessageService } from 'primeng/api';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Plus,
} from 'lucide-angular';
import { AuthService } from '../../core/services/auth.service';
import { AvailabilityService } from '../../core/services/availability.service';
import { TranslationService } from '../../core/services/translation.service';
import { parseHttpErrorMessage } from '../../core/utils/error-parser.util';
import { DashboardService } from './services/dashboard.service';
import { DashboardDataState } from './models/dashboard.model';
import { DashboardKpiGridComponent } from './ui/dashboard-kpi-grid.component';
import { DashboardWeeklyGridComponent } from './ui/dashboard-weekly-grid.component';
import { DashboardEmptyStateComponent } from './ui/dashboard-empty-state.component';
import { DashboardActivityChartComponent } from './ui/dashboard-activity-chart.component';
import { DashboardActiveRoadmapsComponent } from './ui/dashboard-active-roadmaps.component';
import { DashboardTodayQueueComponent } from './ui/dashboard-today-queue.component';
import { DashboardAiInsightsComponent } from './ui/dashboard-ai-insights.component';
import { StarterTemplate } from '../../shared/components/blueprint-empty-state/blueprint-empty-state.component';
import { PlanningStep, PriorKnowledgeLevel } from '../roadmaps/models/roadmap.model';
import { RoadmapService } from '../roadmaps/services/roadmap.service';
import { RoadmapWizardHostComponent } from '../roadmaps/components/dialogs/roadmap-wizard-host/roadmap-wizard-host.component';
import {
  AdaptationConfirmEvent,
  AdaptationModalDialogComponent,
} from '../roadmaps/components/dialogs/adaptation-modal-dialog/adaptation-modal-dialog.component';
import { PrerequisiteAvailabilityDialogComponent } from '../roadmaps/components/dialogs/prerequisite-availability-dialog/prerequisite-availability-dialog.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    LucideAngularModule,
    DashboardKpiGridComponent,
    DashboardWeeklyGridComponent,
    DashboardEmptyStateComponent,
    DashboardActivityChartComponent,
    DashboardActiveRoadmapsComponent,
    DashboardTodayQueueComponent,
    DashboardAiInsightsComponent,
    RoadmapWizardHostComponent,
    AdaptationModalDialogComponent,
    PrerequisiteAvailabilityDialogComponent,
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({ Plus }),
    },
  ],
  templateUrl: './dashboard.component.html',
  styles: [':host { display: block; width: 100%; }'],
})
export class DashboardComponent implements OnInit {
  readonly authService = inject(AuthService);
  readonly dashboardService = inject(DashboardService);
  readonly availabilityService = inject(AvailabilityService);
  readonly roadmapService = inject(RoadmapService);
  readonly translationService = inject(TranslationService);
  readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly messageService = inject(MessageService, { optional: true });

  readonly currentUser = this.authService.currentUser;
  readonly summary = this.dashboardService.summary;
  readonly currentState = this.dashboardService.currentState;
  readonly isLoading = this.dashboardService.isLoading;
  readonly weekOffset = this.dashboardService.weekOffset;

  readonly isNewUser = computed(() => {
    return this.currentState() === 'new-user' || (this.summary()?.activeRoadmaps?.length ?? 0) === 0;
  });

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
  readonly adaptationSubmitting = signal<boolean>(false);
  readonly adaptationError = signal<string | null>(null);

  readonly adaptationContext = computed(() => {
    const currentSummary = this.summary();
    const primaryRoadmap = currentSummary.activeRoadmaps[0] ?? null;
    const rawDeadline = primaryRoadmap?.deadline ?? '';
    const currentDeadline =
      rawDeadline && rawDeadline !== 'Chưa xác định' ? rawDeadline : '';
    return {
      roadmapId: primaryRoadmap?.id ?? null,
      roadmapTitle: primaryRoadmap?.title ?? '',
      missedSessionsCount: currentSummary.adaptationStatus.affectedTasksCount ?? 0,
      currentDeadline,
    };
  });

  ngOnInit(): void {
    if (!this.currentUser()?.email) {
      this.authService.initAuth();
    }
    this.dashboardService.loadSummary().subscribe();

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

  onStateChange(state: DashboardDataState): void {
    this.dashboardService.setState(state);
  }

  onWeekOffsetChange(offset: number): void {
    this.dashboardService.setWeekOffset(offset);
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
    const state = this.currentState();
    if (state === 'new-user' || state === 'unscheduled') {
      this.dashboardService.setState('normal');
    }
    this.dashboardService.loadSummary().subscribe();
  }

  onSelectStarterTemplate(tpl: StarterTemplate): void {
    this.checkAvailabilityAndProceed(() => {
      this.wizardInitialTitle.set(tpl.title);
      this.wizardInitialLevel.set(tpl.knowledgeLevel ?? 'BEGINNER');
      this.wizardInitialWeeklyHours.set(tpl.hoursPerWeek ?? 12);
      this.wizardStep.set(1);
      this.wizardOpen.set(true);
    });
  }

  openAdaptationModal(): void {
    this.adaptationError.set(null);
    this.adaptationModalOpen.set(true);
  }

  closeAdaptationModal(): void {
    if (this.adaptationSubmitting()) {
      return;
    }
    this.adaptationModalOpen.set(false);
    this.adaptationError.set(null);
  }

  onConfirmAdaptation(event: AdaptationConfirmEvent): void {
    const roadmapId = event.roadmapId ?? this.adaptationContext().roadmapId;
    if (!roadmapId) {
      this.adaptationError.set(
        'Chưa tìm thấy lộ trình học tập đang hoạt động để tạo bản nháp tái tối ưu lịch trình.'
      );
      return;
    }

    this.adaptationSubmitting.set(true);
    this.adaptationError.set(null);

    this.roadmapService
      .reoptimizeSchedule(roadmapId)
      .pipe(
        finalize(() => {
          this.adaptationSubmitting.set(false);
        })
      )
      .subscribe({
        next: () => {
          this.adaptationModalOpen.set(false);
          this.adaptationError.set(null);
          this.messageService?.add({
            severity: 'info',
            summary: 'Đã tạo bản nháp đề xuất (DRAFT)',
            detail:
              'Bản nháp tái tối ưu lịch học đã sẵn sàng để bạn xem xét và xác nhận trước khi áp dụng.',
          });
          this.router.navigate(['/roadmaps', roadmapId]);
        },
        error: (err: unknown) => {
          this.adaptationError.set(
            parseHttpErrorMessage(
              err,
              'Không thể tạo bản nháp tái tối ưu lịch học. Vui lòng thử lại.'
            )
          );
        },
      });
  }

  signOut(): void {
    this.authService.signOut();
    this.router.navigate(['/sign-in']);
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent): void {
    const target = event.target as HTMLElement;
    const tagName = target?.tagName?.toLowerCase();
    const isInput =
      tagName === 'input' ||
      tagName === 'textarea' ||
      tagName === 'select' ||
      target?.isContentEditable;

    if (isInput || this.wizardOpen() || this.adaptationModalOpen()) return;

    if (event.code === 'Space' && !event.repeat) {
      event.preventDefault();
      this.router.navigate(['/workspace']);
    }
  }
}
