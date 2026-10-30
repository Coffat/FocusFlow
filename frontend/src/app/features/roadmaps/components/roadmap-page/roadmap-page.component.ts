import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { RoadmapService } from '../../services/roadmap.service';
import { AvailabilityService } from '../../../../core/services/availability.service';
import { BadgeDirective, BadgeVariant } from '../../../../shared/ui/badge/badge.directive';

@Component({
  selector: 'app-roadmap-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    BadgeDirective,
  ],
  templateUrl: './roadmap-page.component.html',
  styleUrl: './roadmap-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoadmapPageComponent implements OnInit {
  readonly roadmapService = inject(RoadmapService);
  readonly availabilityService = inject(AvailabilityService);
  private readonly destroyRef = inject(DestroyRef);

  readonly Number = Number;

  // Local Form Signals for Creating a New Goal & Roadmap
  readonly showCreateForm = signal<boolean>(false);
  readonly showOnboardingModal = signal<boolean>(false);
  readonly newGoalTitle = signal<string>('');
  readonly newGoalDescription = signal<string>('');
  readonly newStartDate = signal<string>('2026-11-02');
  readonly newTargetDate = signal<string>('2026-12-30');

  readonly selectedDetail = computed(() => this.roadmapService.selectedRoadmapDetail());

  readonly totalOfficialMinutes = computed<number>(() => {
    const tasks = this.selectedDetail()?.scheduled_tasks ?? [];
    return tasks.reduce((acc, t) => acc + (t.estimated_minutes || 0), 0);
  });

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.roadmapService.closeActiveStream();
    });
  }

  ngOnInit(): void {
    this.roadmapService.loadRoadmaps();
    this.availabilityService.loadMyAvailability();
  }

  toggleCreateForm(): void {
    if (this.showCreateForm()) {
      this.showCreateForm.set(false);
      return;
    }

    const checkAndOpen = () => {
      if (!this.availabilityService.hasConfiguredAvailability()) {
        this.showOnboardingModal.set(true);
      } else {
        this.showCreateForm.set(true);
      }
    };

    if (!this.availabilityService.profile()) {
      this.availabilityService.loadMyAvailability(() => {
        checkAndOpen();
      });
    } else {
      checkAndOpen();
    }
  }

  closeOnboardingModal(): void {
    this.showOnboardingModal.set(false);
  }

  onConnectGoogleCalendar(): void {
    this.availabilityService.setCalendarIntegrationMode('CONNECTED');
    this.availabilityService.saveMyAvailability((res) => {
      if (res) {
        this.roadmapService.successMessage.set('Đã liên kết Google Calendar thành công!');
        this.showOnboardingModal.set(false);
        this.showCreateForm.set(true);
      }
    });
  }

  onSelectPreset(presetId: 'BUSY_PRO' | 'UNI_STUDENT' | 'BOOTCAMPER'): void {
    this.availabilityService.applyPreset(presetId);
    this.availabilityService.saveMyAvailability((res) => {
      if (res) {
        this.roadmapService.successMessage.set('Đã áp dụng mẫu quỹ giờ rảnh thành công!');
        this.showOnboardingModal.set(false);
        this.showCreateForm.set(true);
      }
    });
  }

  onSelectRoadmap(event: Event): void {
    const id = (event.target as HTMLSelectElement).value;
    if (id) {
      this.roadmapService.loadRoadmapDetail(id);
    }
  }

  onCreateRoadmap(): void {
    const title = this.newGoalTitle().trim();
    if (!title) {
      return;
    }
    if (!this.availabilityService.hasConfiguredAvailability()) {
      this.showOnboardingModal.set(true);
      return;
    }
    this.roadmapService.createRoadmap({
      title,
      description: this.newGoalDescription().trim() || null,
      goal_title: title,
      goal_description: this.newGoalDescription().trim() || null,
      start_date: this.newStartDate() || null,
      target_date: this.newTargetDate() || null,
    });
    this.newGoalTitle.set('');
    this.newGoalDescription.set('');
    this.showCreateForm.set(false);
  }

  onSaveAndValidateDraft(roadmapId: string): void {
    const prop = this.roadmapService.currentProposal();
    if (prop) {
      this.roadmapService.updateProposal(roadmapId, prop.id);
    } else {
      this.roadmapService.saveManualPlan(roadmapId);
    }
  }

  onToggleSoftOverflow(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.roadmapService.setConfirmSoftOverflow(checked);
  }

  onArchiveRoadmap(roadmapId: string): void {
    this.roadmapService.archiveRoadmap(roadmapId);
  }

  getStatusBadgeVariant(status: string): BadgeVariant {
    switch (status) {
      case 'ACTIVE':
      case 'COMPLETED':
        return 'success';
      case 'INITIALIZED':
        return 'default';
      case 'PAUSED':
        return 'outline';
      case 'ARCHIVED':
        return 'secondary';
      default:
        return 'secondary';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'INITIALIZED':
        return 'Khởi tạo (INITIALIZED)';
      case 'ACTIVE':
        return 'Đang thực thi (ACTIVE)';
      case 'PAUSED':
        return 'Tạm dừng (PAUSED)';
      case 'COMPLETED':
        return 'Hoàn thành (COMPLETED)';
      case 'ARCHIVED':
        return 'Đã lưu trữ (ARCHIVED)';
      default:
        return status;
    }
  }
}
