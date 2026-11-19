import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  PLATFORM_ID,
  computed,
  inject,
  signal,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { AmbientAudioService } from '../workspace/data/ambient-audio.service';
import {
  SoundChannelId,
  WorkspaceSceneId,
} from '../workspace/models/workspace.model';
import { FloatingNavbarComponent } from '../../shared/components/floating-navbar/floating-navbar.component';
import { LandingFooterComponent } from '../../shared/components/landing-footer/landing-footer.component';

export type EntityTab = 'roadmap' | 'schedule' | 'learner-model';
export type StageId = 'stage-1' | 'stage-2' | 'stage-3' | 'stage-4';
export type AdaptiveStrategyId = 'domino' | 'recovery' | 'stalled';

export interface TakeawayValidationResult {
  valid: boolean;
  length: number;
  distinctWords: number;
  lengthOk: boolean;
  distinctWordsOk: boolean;
  noRepetitionOk: boolean;
  message: string;
}

export interface SceneOption {
  id: WorkspaceSceneId;
  label: string;
  sublabel: string;
  icon: string;
  gradient: string;
  accentColor: string;
}

@Component({
  selector: 'app-how-it-works',
  standalone: true,
  imports: [
    FormsModule,
    FloatingNavbarComponent,
    LandingFooterComponent,
  ],
  templateUrl: './how-it-works.component.html',
  styleUrl: './how-it-works.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HowItWorksComponent {
  protected readonly authService = inject(AuthService);
  protected readonly ambientAudio = inject(AmbientAudioService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);

  // Core Architectural State Signals
  readonly activeEntityTab = signal<EntityTab>('roadmap');
  readonly activeStageId = signal<StageId>('stage-1');
  readonly selectedSceneId = signal<WorkspaceSceneId>('architectural');
  readonly previewScheduleMode = signal<'A' | 'B'>('A');
  readonly previewAdaptiveStrategy = signal<AdaptiveStrategyId>('domino');

  // Interactive Validator & Quick Onboarding Inputs
  readonly takeawayInput = signal<string>(
    'Hiểu sâu sự khác biệt giữa Roadmap và Schedule giúp tránh phụ thuộc ảo giác AI khi đổi giờ rảnh.'
  );
  readonly quickGoalInput = signal<string>('');

  // 5 Study Workspace Studio Scenes
  readonly sceneOptions: readonly SceneOption[] = [
    {
      id: 'architectural',
      label: 'Giấy Kiến Trúc',
      sublabel: 'Tối giản, trung tính, không xao nhãng',
      icon: 'architecture',
      gradient: 'from-[#FAF8F5] to-[#F0ECE6]',
      accentColor: '#246b4a',
    },
    {
      id: 'lofi-night',
      label: 'Đêm Lofi',
      sublabel: 'Ánh đèn vàng ấm, êm đềm chiều sâu',
      icon: 'dark_mode',
      gradient: 'from-[#1A1926] to-[#12111A]',
      accentColor: '#9D86E9',
    },
    {
      id: 'rain',
      label: 'Mưa Bên Cửa Sổ',
      sublabel: 'Lắng đọng tiếng mưa, rửa sạch xao nhãng',
      icon: 'rainy',
      gradient: 'from-[#1E293B] to-[#0F172A]',
      accentColor: '#38BDF8',
    },
    {
      id: 'cafe',
      label: 'Quán Cafe Chiều',
      sublabel: 'Âm hưởng cốc sứ, nhịp điệu sinh động',
      icon: 'coffee',
      gradient: 'from-[#3E2723] to-[#271711]',
      accentColor: '#D7CCC8',
    },
    {
      id: 'library',
      label: 'Thư Viện Cổ Điển',
      sublabel: 'Trang giấy ngả vàng, lò sưởi tĩnh mịch',
      icon: 'local_library',
      gradient: 'from-[#2C1810] to-[#1A0E08]',
      accentColor: '#E28743',
    },
  ];

  // TakeawayGuard live validation rules
  readonly takeawayValidation = computed<TakeawayValidationResult>(() => {
    const raw = this.takeawayInput();
    const length = raw.trim().length;
    const words = raw
      .trim()
      .toLowerCase()
      .split(/[\s,.;:!?()"-]+/)
      .filter((w) => w.length > 0);
    const distinctWords = new Set(words).size;

    // Repetition check: 5 or more identical consecutive characters
    const hasExcessiveRepetition = /(.)\1{4,}/.test(raw);

    const lengthOk = length >= 30;
    const distinctWordsOk = distinctWords >= 6;
    const noRepetitionOk = !hasExcessiveRepetition;
    const valid = lengthOk && distinctWordsOk && noRepetitionOk;

    let message = '';
    if (length === 0) {
      message = 'Hãy nhập thử một bài học tâm đắc bạn đúc kết được sau phiên học.';
    } else if (!lengthOk) {
      message = `Cần tối thiểu 30 ký tự để đảm bảo độ sâu phản tư (hiện có ${length}/30).`;
    } else if (!distinctWordsOk) {
      message = `Cần tối thiểu 6 từ phân biệt để tránh câu sáo rỗng hoặc lặp từ (hiện có ${distinctWords}/6).`;
    } else if (!noRepetitionOk) {
      message = 'Phát hiện chuỗi ký tự lặp bất thường. Vui lòng ghi lại đúc kết thực sự.';
    } else {
      message = 'Chuẩn xác! Đạt quy tắc TakeawayGuard (0 AI credit, lưu an toàn vào Learner Memory).';
    }

    return {
      valid,
      length,
      distinctWords,
      lengthOk,
      distinctWordsOk,
      noRepetitionOk,
      message,
    };
  });

  constructor() {
    // Stop all testing audio channels when leaving this page to prevent background noise
    this.destroyRef.onDestroy(() => {
      this.ambientAudio.stopAllSounds();
    });
  }

  setEntityTab(tab: EntityTab): void {
    this.activeEntityTab.set(tab);
  }

  setStage(stage: StageId): void {
    this.activeStageId.set(stage);
  }

  setScheduleMode(mode: 'A' | 'B'): void {
    this.previewScheduleMode.set(mode);
  }

  setAdaptiveStrategy(strategy: AdaptiveStrategyId): void {
    this.previewAdaptiveStrategy.set(strategy);
  }

  selectScene(sceneId: WorkspaceSceneId): void {
    this.selectedSceneId.set(sceneId);
    if (this.ambientAudio.isAnySoundPlaying()) {
      this.ambientAudio.applyScenePreset(sceneId);
    }
  }

  toggleAudioChannel(channelId: SoundChannelId): void {
    this.ambientAudio.toggleChannel(channelId);
  }

  toggleMasterAudio(): void {
    if (this.ambientAudio.isAnySoundPlaying()) {
      this.ambientAudio.stopAllSounds();
    } else {
      this.ambientAudio.applyScenePreset(this.selectedSceneId());
      if (!this.ambientAudio.isAnySoundPlaying()) {
        this.ambientAudio.toggleChannel('rain');
      }
    }
  }

  setTakeawayInput(text: string): void {
    this.takeawayInput.set(text);
  }

  setQuickGoal(goal: string): void {
    this.quickGoalInput.set(goal);
  }

  startJourney(goal?: string): void {
    const targetGoal = (goal ?? this.quickGoalInput()).trim();
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/roadmaps'], {
        queryParams: targetGoal ? { goal: targetGoal } : undefined,
      });
    } else {
      this.router.navigate(['/sign-up'], {
        queryParams: targetGoal ? { goal: targetGoal } : undefined,
      });
    }
  }

  scrollTo(elementId: string, event?: Event): void {
    if (event) {
      event.preventDefault();
    }
    if (isPlatformBrowser(this.platformId)) {
      const element = document.getElementById(elementId);
      if (element && typeof element.scrollIntoView === 'function') {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }
}
