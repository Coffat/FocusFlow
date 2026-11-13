import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { MessageService, ConfirmationService } from 'primeng/api';
import { ProfilePageComponent } from './profile-page.component';
import { ProfileService } from '../services/profile.service';
import type { ProfileResponseDTO, LearnerMemoryResponseDTO } from '../models/profile.model';

describe('ProfilePageComponent', () => {
  let component: ProfilePageComponent;
  let fixture: ComponentFixture<ProfilePageComponent>;

  const mockProfile: ProfileResponseDTO = {
    id: '11111111-1111-1111-1111-111111111111',
    email: 'learner@focusflow.ai',
    full_name: 'Minh Hoàng',
    timezone: 'Asia/Ho_Chi_Minh',
    role: 'learner',
    tier: 'PRO',
    created_at: '2026-01-01T00:00:00Z',
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
    srlMetrics: ReturnType<typeof signal<any>>;
    loadProfile: ReturnType<typeof vi.fn>;
    updateProfile: ReturnType<typeof vi.fn>;
    loadLearnerMemory: ReturnType<typeof vi.fn>;
    updateMemory: ReturnType<typeof vi.fn>;
    resetLearnerMemory: ReturnType<typeof vi.fn>;
  };

  let mockMessageService: { add: ReturnType<typeof vi.fn> };
  let mockConfirmationService: { confirm: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    mockProfileService = {
      profile: signal<ProfileResponseDTO | null>(mockProfile),
      profileLoading: signal(false),
      profileSaving: signal(false),
      learnerMemory: signal<readonly LearnerMemoryResponseDTO[]>([mockMemory]),
      memoryLoading: signal(false),
      memoryError: signal(null),
      srlMetrics: signal({
        optSessionMinutes: 45,
        completionRateBias: 1.05,
        learningStyle: 'Sequential Deep Work',
      }),
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
});
