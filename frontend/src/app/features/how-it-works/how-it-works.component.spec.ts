import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { HowItWorksComponent } from './how-it-works.component';
import { AuthService } from '../../core/services/auth.service';
import { AmbientAudioService } from '../workspace/data/ambient-audio.service';

describe('HowItWorksComponent', () => {
  let component: HowItWorksComponent;
  let fixture: ComponentFixture<HowItWorksComponent>;
  let router: Router;
  let ambientAudioService: AmbientAudioService;

  const mockIsAuthenticated = signal<boolean>(false);
  const mockAuthService = {
    isAuthenticated: mockIsAuthenticated,
  };

  beforeEach(async () => {
    mockIsAuthenticated.set(false);

    await TestBed.configureTestingModule({
      imports: [HowItWorksComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    ambientAudioService = TestBed.inject(AmbientAudioService);
    fixture = TestBed.createComponent(HowItWorksComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should create and render all 5 core architectural sections', () => {
    expect(component).toBeTruthy();
    const el = fixture.nativeElement as HTMLElement;

    // Section 1: Hero & Telemetry Strip
    expect(el.textContent).toContain('Cách FocusFlow Kiến Tạo Lộ Trình');
    expect(el.textContent).toContain('6 Bước Khép Kín');
    expect(el.textContent).toContain('3-Tier Validation');
    expect(el.textContent).toContain('0 AI Credit');

    // Section 2: 4-Step Architecture of Flow
    expect(el.textContent).toContain('Kiến Trúc 4 Giai Đoạn Điều Phối');
    expect(el.textContent).toContain('Chẩn Đoán Ngữ Cảnh & Lập Lộ Trình Hybrid RAG');
    expect(el.textContent).toContain('Xếp Lịch Tất Định Mode A/B & Cổng Kiểm Duyệt 3 Tầng');
    expect(el.textContent).toContain('Thực Thi Tại Study Workspace Studio & TakeawayGuard');
    expect(el.textContent).toContain('Kiểm Chứng Prove Mode & 3 Chiến Lược Thích Ứng');

    // Section 3: Methodological Contrast Table
    expect(el.textContent).toContain('FocusFlow Adaptive System vs. Tự Học Rời Rạc');
    expect(el.textContent).toContain('1. Kiến trúc Lộ trình & Tiên quyết (DAG)');

    // Section 4: Atmospheric Studio & Web Audio
    expect(el.textContent).toContain('Không Gian Học Tập Tập Trung');
    expect(el.textContent).toContain('Bàn Điều Khiển Âm Thanh Thực Tế');

    // Section 5: Architectural Onboarding CTA
    expect(el.textContent).toContain('Kiến Tạo Nhịp Độ Tự Học Chuyên Sâu Của Bạn');
    expect(el.textContent).toContain('IELTS 7.5 (12 tuần)');
  });

  it('should switch between the 3 core entity tabs correctly', () => {
    expect(component.activeEntityTab()).toBe('roadmap');

    component.setEntityTab('schedule');
    fixture.detectChanges();
    expect(component.activeEntityTab()).toBe('schedule');
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('ENTITY: OFFICIAL_SCHEDULE (SCHEDULE_BLOCKS)');

    component.setEntityTab('learner-model');
    fixture.detectChanges();
    expect(component.activeEntityTab()).toBe('learner-model');
    expect(el.textContent).toContain('ENTITY: LEARNER_MODEL (4×3 MATRIX)');

    component.setEntityTab('roadmap');
    fixture.detectChanges();
    expect(component.activeEntityTab()).toBe('roadmap');
    expect(el.textContent).toContain('ENTITY: ROADMAP (ESTIMATED_EFFORT)');
  });

  it('should validate takeaway inputs according to TakeawayGuard rules', () => {
    // 1. Initial valid input
    expect(component.takeawayValidation().valid).toBe(true);

    // 2. Empty input
    component.setTakeawayInput('');
    expect(component.takeawayValidation().valid).toBe(false);
    expect(component.takeawayValidation().lengthOk).toBe(false);

    // 3. Under 30 characters
    component.setTakeawayInput('Bài học hay ngắn');
    expect(component.takeawayValidation().valid).toBe(false);
    expect(component.takeawayValidation().lengthOk).toBe(false);
    expect(component.takeawayValidation().message).toContain('Cần tối thiểu 30 ký tự');

    // 4. >= 30 chars but < 6 distinct words (repetitive words)
    component.setTakeawayInput('học học học học học học học học học học học');
    expect(component.takeawayValidation().lengthOk).toBe(true);
    expect(component.takeawayValidation().distinctWordsOk).toBe(false);
    expect(component.takeawayValidation().message).toContain('Cần tối thiểu 6 từ phân biệt');

    // 5. Excessive character repetition penalty
    component.setTakeawayInput('Học tập rất quan trọng aaaaaaa để nâng cao năng lực');
    expect(component.takeawayValidation().noRepetitionOk).toBe(false);
    expect(component.takeawayValidation().valid).toBe(false);

    // 6. Valid takeaway
    component.setTakeawayInput('Đã nắm vững cách thức phân rã đồ thị DAG và kiểm soát nhịp học Pomodoro 45 phút.');
    expect(component.takeawayValidation().valid).toBe(true);
    expect(component.takeawayValidation().lengthOk).toBe(true);
    expect(component.takeawayValidation().distinctWordsOk).toBe(true);
    expect(component.takeawayValidation().noRepetitionOk).toBe(true);
    expect(component.takeawayValidation().message).toContain('Chuẩn xác! Đạt quy tắc TakeawayGuard');
  });

  it('should interact with AmbientAudioService and clean up sounds on destroy', () => {
    const toggleSpy = vi.spyOn(ambientAudioService, 'toggleChannel');
    const stopAllSpy = vi.spyOn(ambientAudioService, 'stopAllSounds');

    component.toggleAudioChannel('rain');
    expect(toggleSpy).toHaveBeenCalledWith('rain');

    component.selectScene('rain');
    expect(component.selectedSceneId()).toBe('rain');

    component.toggleMasterAudio();

    // Destroy fixture to test cleanup in destroyRef
    fixture.destroy();
    expect(stopAllSpy).toHaveBeenCalled();
  });

  it('should navigate to sign-up when unauthenticated and roadmaps when authenticated', () => {
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    // Unauthenticated
    mockIsAuthenticated.set(false);
    component.setQuickGoal('Mastering Rust System Programming');
    component.startJourney();
    expect(navigateSpy).toHaveBeenCalledWith(['/sign-up'], {
      queryParams: { goal: 'Mastering Rust System Programming' },
    });

    // Authenticated
    mockIsAuthenticated.set(true);
    component.startJourney('IELTS 7.5 Preparation');
    expect(navigateSpy).toHaveBeenCalledWith(['/roadmaps'], {
      queryParams: { goal: 'IELTS 7.5 Preparation' },
    });
  });

  it('should support switching 3 adaptive strategies and schedule modes in stage previews', () => {
    component.setScheduleMode('B');
    expect(component.previewScheduleMode()).toBe('B');

    component.setAdaptiveStrategy('recovery');
    expect(component.previewAdaptiveStrategy()).toBe('recovery');

    component.setAdaptiveStrategy('stalled');
    expect(component.previewAdaptiveStrategy()).toBe('stalled');
  });
});
