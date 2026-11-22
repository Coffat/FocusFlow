import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { computed, signal } from '@angular/core';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ProfilePageComponent } from './profile-page.component';
import { ProfileService } from '../services/profile.service';
import type {
  ProfileResponseDTO,
  LearnerMemoryResponseDTO,
  LearnerSrlProfileDTO,
} from '../models/profile.model';

describe('ProfilePageComponent', () => {
  let component: ProfilePageComponent;
  let fixture: ComponentFixture<ProfilePageComponent>;

  const coldStartSrl: LearnerSrlProfileDTO = {
    total_completed_sessions: 1,
    is_cold_start: true,
    min_sessions_required: 3,
    optimal_focus_duration_mins: null,
    estimation_bias_factor: null,
    weekly_completion_rate: 0,
    peak_productivity_slots: [],
    last_aggregated_at: null,
  };

  const adaptiveSrl: LearnerSrlProfileDTO = {
    total_completed_sessions: 6,
    is_cold_start: false,
    min_sessions_required: 3,
    optimal_focus_duration_mins: 32,
    estimation_bias_factor: 1.18,
    weekly_completion_rate: 0.85,
    peak_productivity_slots: ['MORNING', 'EVENING'],
    last_aggregated_at: '2026-01-05T10:00:00Z',
  };

  const mockProfile: ProfileResponseDTO = {
    id: '11111111-1111-1111-1111-111111111111',
    email: 'learner@focusflow.ai',
    full_name: 'Minh Hoàng',
    timezone: 'Asia/Ho_Chi_Minh',
    role: 'learner',
    tier: 'PRO',
    created_at: '2026-01-01T00:00:00Z',
    srl_profile: coldStartSrl,
  };

  const mockMemory: LearnerMemoryResponseDTO = {
    id: '22222222-2222-2222-2222-222222222222',
    memory_key: 'session_capacity',
    value: { capacity_minutes: 45 },
    category: 'PROFILE',
    epistemic_level: 'OBSERVED',
    confidence: 0.9,
    sample_size: 15,
    evidence: [],
    status: 'PENDING',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  let mockProfileService: {
    profile: ReturnType<typeof signal<ProfileResponseDTO | null>>;
    profileLoading: ReturnType<typeof signal<boolean>>;
    profileSaving: ReturnType<typeof signal<boolean>>;
    learnerMemory: ReturnType<typeof signal<readonly LearnerMemoryResponseDTO[]>>;
    memoryLoading: ReturnType<typeof signal<boolean>>;
    memoryError: ReturnType<typeof signal<string | null>>;
    srlProfile: ReturnType<typeof computed<LearnerSrlProfileDTO | null>>;
    isSrlColdStart: ReturnType<typeof computed<boolean>>;
    loadProfile: ReturnType<typeof vi.fn>;
    updateProfile: ReturnType<typeof vi.fn>;
    loadLearnerMemory: ReturnType<typeof vi.fn>;
    updateMemory: ReturnType<typeof vi.fn>;
    resetLearnerMemory: ReturnType<typeof vi.fn>;
  };

  let mockMessageService: { add: ReturnType<typeof vi.fn> };
  let mockConfirmationService: { confirm: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    const profileSignal = signal<ProfileResponseDTO | null>(mockProfile);
    const srlProfileComputed = computed<LearnerSrlProfileDTO | null>(
      () => profileSignal()?.srl_profile ?? null,
    );
    const isSrlColdStartComputed = computed<boolean>(
      () => srlProfileComputed()?.is_cold_start ?? true,
    );

    mockProfileService = {
      profile: profileSignal,
      profileLoading: signal(false),
      profileSaving: signal(false),
      learnerMemory: signal<readonly LearnerMemoryResponseDTO[]>([mockMemory]),
      memoryLoading: signal(false),
      memoryError: signal(null),
      srlProfile: srlProfileComputed,
      isSrlColdStart: isSrlColdStartComputed,
      loadProfile: vi.fn().mockResolvedValue(undefined),
      updateProfile: vi.fn().mockResolvedValue(mockProfile),
      loadLearnerMemory: vi.fn().mockResolvedValue(undefined),
      updateMemory: vi.fn().mockResolvedValue(undefined),
      resetLearnerMemory: vi.fn().mockResolvedValue(undefined),
    };

    mockMessageService = { add: vi.fn() };
    mockConfirmationService = { confirm: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [ProfilePageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ProfileService, useValue: mockProfileService },
        { provide: MessageService, useValue: mockMessageService },
        { provide: ConfirmationService, useValue: mockConfirmationService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ProfilePageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công ProfilePageComponent', () => {
    expect(component).toBeTruthy();
    expect(component.userInitials()).toBe('MH');
  });

  it('tải profile và điền sẵn vào form khi khởi động', () => {
    expect(mockProfileService.loadProfile).toHaveBeenCalled();
    expect(component.profileForm.get('full_name')?.value).toBe('Minh Hoàng');
    expect(component.profileForm.get('timezone')?.value).toBe('Asia/Ho_Chi_Minh');
  });

  it('lọc danh sách Learner Memory theo category', () => {
    expect(component.filteredMemories().length).toBe(1);

    component.selectedCategory.set('KNOWLEDGE');
    expect(component.filteredMemories().length).toBe(0);

    component.selectedCategory.set('PROFILE');
    expect(component.filteredMemories().length).toBe(1);
  });

  it('gọi onSaveProfile cập nhật hồ sơ khi form hợp lệ', async () => {
    component.profileForm.patchValue({
      full_name: 'Hoàng Minh',
      timezone: 'Asia/Tokyo',
    });
    component.profileForm.markAsDirty();

    await component.onSaveProfile();

    expect(mockProfileService.updateProfile).toHaveBeenCalledWith({
      full_name: 'Hoàng Minh',
      timezone: 'Asia/Tokyo',
    });
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'success' })
    );
  });

  it('gọi onConfirmMemory và hiển thị thông báo thành công', async () => {
    await component.onConfirmMemory(mockMemory.id);

    expect(mockProfileService.updateMemory).toHaveBeenCalledWith(mockMemory.id, {
      action: 'confirm',
      value: null,
    });
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'success' })
    );
  });

  it('gọi onRejectMemory và hiển thị thông báo info', async () => {
    await component.onRejectMemory(mockMemory.id);

    expect(mockProfileService.updateMemory).toHaveBeenCalledWith(mockMemory.id, {
      action: 'reject',
      value: null,
    });
    expect(mockMessageService.add).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'info' })
    );
  });

  it('mở hộp thoại xác nhận khi bấm onRequestReset', () => {
    component.onRequestReset();
    expect(mockConfirmationService.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        header: 'Xác nhận Đặt lại Cold Start',
      })
    );
  });

  it('hiển thị banner chưa đủ dữ liệu và không hiển thị số liệu giả lập khi is_cold_start = true', () => {
    const el: HTMLElement = fixture.nativeElement;
    const banner = el.querySelector('[data-testid="srl-insufficient-data-banner"]');
    const badge = el.querySelector('[data-testid="srl-state-badge"]');
    const optimalFocus = el.querySelector('[data-testid="srl-optimal-focus"]');
    const estimationBias = el.querySelector('[data-testid="srl-estimation-bias"]');
    const peakSlots = el.querySelector('[data-testid="srl-peak-slots"]');

    expect(banner).toBeTruthy();
    expect(banner?.textContent).toContain('Chưa đủ dữ liệu học tập (1/3 phiên hoàn thành)');
    expect(badge?.textContent).toContain('SRL: Chưa đủ dữ liệu');
    expect(optimalFocus?.textContent?.trim()).toBe('—');
    expect(estimationBias?.textContent?.trim()).toBe('—');
    expect(peakSlots?.textContent?.trim()).toBe('—');

    const fullText = el.textContent ?? '';
    expect(fullText).not.toContain('Sequential Deep Work');
    expect(fullText).not.toContain('1.05x');
    expect(fullText).not.toContain('45 phút / phiên');
  });

  it('hiển thị các chỉ số SRL thật từ backend khi is_cold_start = false', () => {
    mockProfileService.profile.set({
      ...mockProfile,
      srl_profile: adaptiveSrl,
    });
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const banner = el.querySelector('[data-testid="srl-insufficient-data-banner"]');
    const badge = el.querySelector('[data-testid="srl-state-badge"]');
    const optimalFocus = el.querySelector('[data-testid="srl-optimal-focus"]');
    const estimationBias = el.querySelector('[data-testid="srl-estimation-bias"]');
    const peakSlots = el.querySelector('[data-testid="srl-peak-slots"]');

    expect(banner).toBeNull();
    expect(badge?.textContent).toContain('SRL: Đang thích ứng');
    expect(optimalFocus?.textContent).toContain('32');
    expect(optimalFocus?.textContent).toContain('phút / phiên');
    expect(estimationBias?.textContent?.trim()).toBe('1.18x');
    expect(peakSlots?.textContent?.trim()).toBe('Buổi sáng, Buổi tối');
  });
});
