import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ProfileService } from './profile.service';
import { AuthService } from '../../../core/services/auth.service';
import type { ProfileResponseDTO, LearnerMemoryResponseDTO } from '../models/profile.model';

describe('ProfileService', () => {
  let service: ProfileService;
  let httpMock: HttpTestingController;

  const mockUser = {
    id: '11111111-1111-1111-1111-111111111111',
    email: 'user@focusflow.ai',
    fullName: 'Test User',
    role: 'learner' as const,
    tier: 'PRO',
    createdAt: '2026-01-01T00:00:00Z',
  };

  const mockAuthService = {
    currentUser: signal(mockUser),
    setUser: vi.fn(),
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ProfileService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService },
      ],
    });

    service = TestBed.inject(ProfileService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('khởi tạo thành công ProfileService với giá trị mặc định', () => {
    expect(service).toBeTruthy();
    expect(service.profile()).toBeNull();
    expect(service.profileLoading()).toBe(false);
    expect(service.learnerMemory()).toEqual([]);
    expect(service.srlMetrics().optSessionMinutes).toBe(45);
  });

  it('loadProfile tải thông tin người dùng từ backend thành công', async () => {
    const mockProfile: ProfileResponseDTO = {
      id: '11111111-1111-1111-1111-111111111111',
      email: 'user@focusflow.ai',
      full_name: 'Nguyễn Văn A',
      timezone: 'Asia/Ho_Chi_Minh',
      role: 'learner',
      tier: 'PRO',
      created_at: '2026-01-01T00:00:00Z',
    };

    const loadPromise = service.loadProfile();
    const req = httpMock.expectOne('/api/v1/account/profile');
    expect(req.request.method).toBe('GET');
    req.flush(mockProfile);

    await loadPromise;
    expect(service.profile()).toEqual(mockProfile);
    expect(service.profileLoading()).toBe(false);
  });

  it('loadProfile fallback sang authService khi request gặp lỗi', async () => {
    const loadPromise = service.loadProfile();
    const req = httpMock.expectOne('/api/v1/account/profile');
    req.flush('Server error', { status: 500, statusText: 'Internal Error' });

    await loadPromise;
    expect(service.profile()).toBeTruthy();
    expect(service.profile()?.email).toBe('user@focusflow.ai');
    expect(service.profile()?.full_name).toBe('Test User');
  });

  it('updateProfile cập nhật hồ sơ và đồng bộ sang authService', async () => {
    const updatedProfile: ProfileResponseDTO = {
      id: '11111111-1111-1111-1111-111111111111',
      email: 'user@focusflow.ai',
      full_name: 'Nguyễn Văn Mới',
      timezone: 'Asia/Tokyo',
      role: 'learner',
      tier: 'PRO',
      created_at: '2026-01-01T00:00:00Z',
    };

    const updatePromise = service.updateProfile({
      full_name: 'Nguyễn Văn Mới',
      timezone: 'Asia/Tokyo',
    });

    const req = httpMock.expectOne('/api/v1/account/profile');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({
      full_name: 'Nguyễn Văn Mới',
      timezone: 'Asia/Tokyo',
    });
    req.flush(updatedProfile);

    const result = await updatePromise;
    expect(result).toEqual(updatedProfile);
    expect(service.profile()).toEqual(updatedProfile);
    expect(mockAuthService.setUser).toHaveBeenCalledWith(
      expect.objectContaining({ fullName: 'Nguyễn Văn Mới' })
    );
  });

  it('loadLearnerMemory truy xuất danh sách memory items', async () => {
    const mockMemories: LearnerMemoryResponseDTO[] = [
      {
        id: '22222222-2222-2222-2222-222222222222',
        memory_key: 'focus_peak_time',
        value: { peak_hours: ['08:00', '10:00'] },
        category: 'BEHAVIORAL',
        epistemic_level: 'OBSERVED',
        confidence: 0.85,
        sample_size: 12,
        evidence: [],
        status: 'PENDING',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ];

    const loadPromise = service.loadLearnerMemory();
    const req = httpMock.expectOne('/api/v1/account/learner-memory');
    expect(req.request.method).toBe('GET');
    req.flush(mockMemories);

    await loadPromise;
    expect(service.learnerMemory().length).toBe(1);
    expect(service.learnerMemory()[0].memory_key).toBe('focus_peak_time');
    expect(service.memoryLoading()).toBe(false);
  });

  it('updateMemory cập nhật trạng thái của một memory item', async () => {
    const initialItem: LearnerMemoryResponseDTO = {
      id: '22222222-2222-2222-2222-222222222222',
      memory_key: 'focus_peak_time',
      value: { peak_hours: ['08:00', '10:00'] },
      category: 'BEHAVIORAL',
      epistemic_level: 'OBSERVED',
      confidence: 0.85,
      sample_size: 12,
      evidence: [],
      status: 'PENDING',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    };
    service.learnerMemory.set([initialItem]);

    const updatedItem: LearnerMemoryResponseDTO = {
      ...initialItem,
      status: 'CONFIRMED',
      epistemic_level: 'EXPLICIT',
    };

    const updatePromise = service.updateMemory(initialItem.id, {
      action: 'confirm',
      value: null,
    });

    const req = httpMock.expectOne(`/api/v1/account/learner-memory/${initialItem.id}`);
    expect(req.request.method).toBe('PATCH');
    req.flush(updatedItem);

    await updatePromise;
    expect(service.learnerMemory()[0].status).toBe('CONFIRMED');
    expect(service.learnerMemory()[0].epistemic_level).toBe('EXPLICIT');
  });

  it('resetLearnerMemory gửi confirm và làm rỗng mảng memory', async () => {
    service.learnerMemory.set([
      {
        id: '22222222-2222-2222-2222-222222222222',
        memory_key: 'focus_peak_time',
        value: {},
        category: 'BEHAVIORAL',
        epistemic_level: 'OBSERVED',
        confidence: 0.85,
        sample_size: 12,
        evidence: [],
        status: 'PENDING',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]);

    const resetPromise = service.resetLearnerMemory();
    const req = httpMock.expectOne('/api/v1/account/learner-memory/reset');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ confirm: true });
    req.flush(null, { status: 204, statusText: 'No Content' });

    await resetPromise;
    expect(service.learnerMemory()).toEqual([]);
  });
});
