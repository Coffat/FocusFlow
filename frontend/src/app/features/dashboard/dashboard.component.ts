import { Component, OnInit, inject, ChangeDetectionStrategy, HostListener } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/services/translation.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
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

@Component({
  selector: 'app-dashboard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    ButtonModule,
    TranslatePipe,
    DashboardStateSwitcherComponent,
    DashboardKpiGridComponent,
    DashboardWeeklyGridComponent,
    DashboardEmptyStateComponent,
    DashboardActivityChartComponent,
    DashboardActiveRoadmapsComponent,
    DashboardTodayQueueComponent,
    DashboardAiInsightsComponent
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
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

    if (isInput) return;

    if (event.key === 'c' || event.key === 'C') {
      event.preventDefault();
      this.router.navigate(['/roadmaps']);
    } else if (event.code === 'Space' && !event.repeat) {
      event.preventDefault();
      this.router.navigate(['/workspace']);
    }
  }
}
