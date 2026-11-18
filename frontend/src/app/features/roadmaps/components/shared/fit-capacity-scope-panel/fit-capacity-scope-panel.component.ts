import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import {
  FeasibilityScopeItem,
  PreliminaryFeasibility,
  PreliminaryFeasibilityReason,
  ScopeApprovalConflict,
  formatEffortMinutes,
} from '../../../models/roadmap.model';

@Component({
  selector: 'app-fit-capacity-scope-panel',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './fit-capacity-scope-panel.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FitCapacityScopePanelComponent {
  readonly preliminaryFeasibility = input<PreliminaryFeasibility | null>(null);
  readonly conflict = input<ScopeApprovalConflict | null>(null);
  readonly isReadOnly = input<boolean>(false);
  readonly isBusy = input<boolean>(false);
  readonly isStreaming = input<boolean>(false);
  readonly showAvailabilityLink = input<boolean>(true);

  readonly confirmChange = output<boolean>();
  readonly approveFitCapacity = output<number>();
  readonly regenerateFitCapacity = output<void>();

  private readonly confirmedVersion = signal<number | null>(null);

  readonly effectiveVersion = computed<number>(() => {
    const pf = this.preliminaryFeasibility();
    if (pf && typeof pf.scope_proposal_version === 'number' && pf.scope_proposal_version > 0) {
      return pf.scope_proposal_version;
    }
    const conflictVer = this.conflict()?.scope_proposal_version;
    if (typeof conflictVer === 'number' && conflictVer > 0) {
      return conflictVer;
    }
    return pf?.scope_proposal_version ?? 1;
  });

  readonly isScopeApproved = computed<boolean>(() => {
    const pf = this.preliminaryFeasibility();
    if (!pf || pf.status !== 'FIT_CAPACITY_REQUIRES_APPROVAL') {
      return false;
    }
    if (pf.scope_approval_status !== 'APPROVED_BY_LEARNER') {
      return false;
    }
    if (pf.approved_scope_version !== null && pf.approved_scope_version !== undefined) {
      return pf.approved_scope_version === pf.scope_proposal_version;
    }
    return true;
  });

  readonly showUnschedulableAlert = computed<boolean>(() => {
    return (
      this.preliminaryFeasibility()?.status === 'PRELIMINARY_UNSCHEDULABLE' ||
      this.conflict()?.code === 'PRELIMINARY_UNSCHEDULABLE'
    );
  });

  readonly showFitCapacityPanel = computed<boolean>(() => {
    if (this.showUnschedulableAlert()) {
      return false;
    }
    return (
      this.preliminaryFeasibility()?.status === 'FIT_CAPACITY_REQUIRES_APPROVAL' ||
      this.conflict()?.code === 'SCOPE_APPROVAL_REQUIRED'
    );
  });

  readonly requiresLearnerConfirmation = computed<boolean>(() => {
    return (
      this.showFitCapacityPanel() &&
      (!this.isScopeApproved() || this.conflict()?.code === 'SCOPE_APPROVAL_REQUIRED')
    );
  });

  readonly isConfirmedForCurrentVersion = computed<boolean>(() => {
    const confirmed = this.confirmedVersion();
    return confirmed !== null && confirmed === this.effectiveVersion();
  });

  readonly keptScope = computed<FeasibilityScopeItem[]>(() => {
    return this.preliminaryFeasibility()?.kept_scope ?? [];
  });

  readonly deferredScope = computed<FeasibilityScopeItem[]>(() => {
    return this.preliminaryFeasibility()?.deferred_scope ?? [];
  });

  readonly reasons = computed<PreliminaryFeasibilityReason[]>(() => {
    return this.preliminaryFeasibility()?.feasibility_reasons ?? [];
  });

  readonly earliestDateRange = computed(() => {
    return this.preliminaryFeasibility()?.adjustment_options?.estimated_earliest_target_date_range ?? null;
  });

  readonly recommendedAdditionalWeeklyMinutes = computed<number>(() => {
    return this.preliminaryFeasibility()?.adjustment_options?.recommended_additional_weekly_minutes ?? 0;
  });

  formatMinutes(minutes: number | null | undefined): string {
    return formatEffortMinutes(minutes);
  }

  onToggleConfirmation(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.confirmedVersion.set(checked ? this.effectiveVersion() : null);
    this.confirmChange.emit(checked);
  }

  onApproveFitCapacity(): void {
    if (!this.isConfirmedForCurrentVersion() || this.isReadOnly() || this.isBusy() || this.isStreaming()) {
      return;
    }
    this.approveFitCapacity.emit(this.effectiveVersion());
  }

  onRegenerateFitCapacity(): void {
    if (this.isReadOnly() || this.isBusy() || this.isStreaming()) {
      return;
    }
    this.regenerateFitCapacity.emit();
  }
}
