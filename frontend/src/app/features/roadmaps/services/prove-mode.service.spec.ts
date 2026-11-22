import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import {
  ProveModeService,
  GenerateProofResponseDTO,
  LatestMilestoneProofResponseDTO,
  MilestoneProofResponseDTO,
} from './prove-mode.service';
import { EntityInvalidationService } from '../../../core/services/entity-invalidation.service';
import { HTTP_TIMEOUT_MS } from '../../../core/interceptors/timeout.interceptor';

describe('ProveModeService (UC-20 / FR-REPORT-003)', () => {
  let service: ProveModeService;
  let httpMock: HttpTestingController;
  let invalidationSpy: { invalidate: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    invalidationSpy = { invalidate: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        ProveModeService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: EntityInvalidationService, useValue: invalidationSpy },
      ],
    });

    service = TestBed.inject(ProveModeService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('getLatestProof gửi GET với withCredentials và cache kết quả vào proofByMilestone', async () => {
    const mockLatest: LatestMilestoneProofResponseDTO = {
      id: 'proof-1',
      milestone_id: 'ms-1',
      status: 'PASSED',
      score: 88,
      confidence: 0.8,
      corrective_action: 'Tiếp tục duy trì tiến độ tốt.',
      is_verified: true,
      calibration_error: 0.08,
      questions: [{ id: 'q1', prompt: 'Giải thích event loop?' }],
      answer_evidence: [{ question_id: 'q1', evidence: 'Trả lời đầy đủ', is_addressed: true }],
      created_at: '2026-11-21T08:00:00Z',
      updated_at: '2026-11-21T08:05:00Z',
    };

    const promise = firstValueFrom(service.getLatestProof('ms-1'));
    const req = httpMock.expectOne('/api/v1/evaluation/milestones/ms-1/proofs/latest');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush(mockLatest);

    const res = await promise;
    expect(res).toEqual(mockLatest);
    expect(service.proofByMilestone()['ms-1']?.status).toBe('PASSED');
    expect(service.proofByMilestone()['ms-1']?.score).toBe(88);
  });

  it('generateProof gửi POST generate-jobs với withCredentials và trả về câu hỏi từ backend', async () => {
    const mockGen: GenerateProofResponseDTO = {
      proof_id: 'proof-2',
      status: 'READY',
      questions: [
        { id: 'q1', prompt: 'Câu 1' },
        { id: 'q2', prompt: 'Câu 2' },
        { id: 'q3', prompt: 'Câu 3' },
      ],
    };

    const promise = firstValueFrom(service.generateProof('ms-2'));
    const req = httpMock.expectOne('/api/v1/evaluation/milestones/ms-2/proofs/generate-jobs');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.context.get(HTTP_TIMEOUT_MS)).toBe(35_000);
    req.flush(mockGen);

    const res = await promise;
    expect(res.proof_id).toBe('proof-2');
    expect(res.questions.length).toBe(3);
  });

  it('submitProof gửi POST submit, cập nhật proofByMilestone và invalidate roadmaps/dashboard/analytics', async () => {
    const mockSubmitted: MilestoneProofResponseDTO = {
      id: 'proof-2',
      milestone_id: 'ms-2',
      status: 'NEEDS_REVIEW',
      score: 62,
      confidence: 0.75,
      corrective_action: 'Ôn lại cơ chế async/await.',
      is_verified: true,
      calibration_error: 0.13,
      answer_evidence: [
        { question_id: 'q1', evidence: 'Chưa nêu ví dụ cụ thể', is_addressed: false },
      ],
    };

    const promise = firstValueFrom(
      service.submitProof('ms-2', 'proof-2', {
        answers: [{ question_id: 'q1', answer: 'Async dùng event loop' }],
        confidence: 0.75,
      })
    );
    const req = httpMock.expectOne('/api/v1/evaluation/milestones/ms-2/proofs/proof-2/submit');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.context.get(HTTP_TIMEOUT_MS)).toBe(40_000);
    expect(req.request.body).toEqual({
      answers: [{ question_id: 'q1', answer: 'Async dùng event loop' }],
      confidence: 0.75,
    });
    req.flush(mockSubmitted);

    const res = await promise;
    expect(res).toEqual(mockSubmitted);
    expect(service.proofByMilestone()['ms-2']?.status).toBe('NEEDS_REVIEW');
    expect(service.proofByMilestone()['ms-2']?.score).toBe(62);
    expect(invalidationSpy.invalidate).toHaveBeenCalledWith('roadmaps', 'dashboard', 'analytics');
  });
});
