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
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Plus,
} from 'lucide-angular';
import { AuthService } from '../../core/services/auth.service';
import { AvailabilityService } from '../../core/services/availability.service';
import { TranslationService } from '../../core/services/translation.service';
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
import { PriorKnowledgeLevel } from '../roadmaps/models/roadmap.model';
import { RoadmapWizardHostComponent } from '../roadmaps/components/dialogs/roadmap-wizard-host/roadmap-wizard-host.component';
import { AdaptationModalDialogComponent } from '../roadmaps/components/dialogs/adaptation-modal-dialog/adaptation-modal-dialog.component';
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
  readonly translationService = inject(TranslationService);
  readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

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

  // 4-Step Wizard Dialog State
  readonly wizardOpen = signal<boolean>(false);
  readonly wizardStep = signal<1 | 2 | 3 | 4>(1);
  readonly wizardInitialTitle = signal<string>('');
  readonly wizardInitialLevel = signal<PriorKnowledgeLevel>('BEGINNER');
  readonly wizardInitialWeeklyHours = signal<number>(12);

  // SCR-08 Adaptation Modal Dialog State
  readonly adaptationModalOpen = signal<boolean>(false);

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
    const proceed = () => {
      if (!this.availabilityService.hasConfiguredAvailability()) {
        this.prerequisiteDialogOpen.set(true);
      } else {
        action();
      }
    };

    if (!this.availabilityService.profile()) {
      this.availabilityService.loadMyAvailability(() => {
        proceed();
      });
    } else {
      proceed();
    }
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

  openCreateWizard(step: 1 | 2 | 3 | 4 = 1): void {
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
    this.adaptationModalOpen.set(true);
  }

  closeAdaptationModal(): void {
    this.adaptationModalOpen.set(false);
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
