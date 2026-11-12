import {
  Component,
  OnInit,
  inject,
  ChangeDetectionStrategy,
  HostListener,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/services/translation.service';
import { DashboardService } from './services/dashboard.service';
import { DashboardDataState } from './models/dashboard.model';
import { DashboardStateSwitcherComponent } from './ui/dashboard-state-switcher.component';
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

@Component({
  selector: 'app-dashboard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DashboardStateSwitcherComponent,
    DashboardKpiGridComponent,
    DashboardWeeklyGridComponent,
    DashboardEmptyStateComponent,
    DashboardActivityChartComponent,
    DashboardActiveRoadmapsComponent,
    DashboardTodayQueueComponent,
    DashboardAiInsightsComponent,
    RoadmapWizardHostComponent,
    AdaptationModalDialogComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  readonly authService = inject(AuthService);
  readonly dashboardService = inject(DashboardService);
  readonly translationService = inject(TranslationService);
  readonly router = inject(Router);

  readonly currentUser = this.authService.currentUser;
  readonly summary = this.dashboardService.summary;
  readonly currentState = this.dashboardService.currentState;
  readonly isLoading = this.dashboardService.isLoading;
  readonly weekOffset = this.dashboardService.weekOffset;

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
  }

  onStateChange(state: DashboardDataState): void {
    this.dashboardService.setState(state);
  }

  onWeekOffsetChange(offset: number): void {
    this.dashboardService.setWeekOffset(offset);
  }

  openCreateWizard(step: 1 | 2 | 3 | 4 = 1): void {
    this.wizardInitialTitle.set('');
    this.wizardInitialLevel.set('BEGINNER');
    this.wizardInitialWeeklyHours.set(12);
    this.wizardStep.set(step);
    this.wizardOpen.set(true);
  }

  closeCreateWizard(): void {
    this.wizardOpen.set(false);
  }

  onSelectStarterTemplate(tpl: StarterTemplate): void {
    this.wizardInitialTitle.set(tpl.title);
    this.wizardInitialLevel.set(tpl.knowledgeLevel ?? 'BEGINNER');
    this.wizardInitialWeeklyHours.set(tpl.hoursPerWeek ?? 12);
    this.wizardStep.set(1);
    this.wizardOpen.set(true);
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

    if (event.key === 'c' || event.key === 'C') {
      event.preventDefault();
      this.openCreateWizard(1);
    } else if (event.code === 'Space' && !event.repeat) {
      event.preventDefault();
      this.router.navigate(['/workspace']);
    }
  }
}
