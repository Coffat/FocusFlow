import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ProveModeDialogComponent } from './prove-mode-dialog.component';
import {
  ProveModeService,
  GenerateProofResponseDTO,
  LatestMilestoneProofResponseDTO,
  MilestoneProofResponseDTO,
} from '../../../services/prove-mode.service';

describe('ProveModeDialogComponent (FE-FUNC-01)', () => {
  let fixture: ComponentFixture<ProveModeDialogComponent>;
  let component: ProveModeDialogComponent;
  let mockProveModeService: {
    getLatestProof: ReturnType<typeof vi.fn>;
    generateProof: ReturnType<typeof vi.fn>;
    submitProof: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    mockProveModeService = {
      getLatestProof: vi.fn().mockReturnValue(of(null)),
      generateProof: vi.fn(),
      submitProof: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ProveModeDialogComponent],
      providers: [{ provide: ProveModeService, useValue: mockProveModeService }],
    }).compileComponents();

    fixture = TestBed.createComponent(ProveModeDialogComponent);
    component = fixture.componentInstance;
  });

  function openDialog(milestoneId = 'ms-101', title = 'Chặng 1: Nền tảng Python'): void {
    fixture.componentRef.setInput('milestoneId', milestoneId);
    fixture.componentRef.setInput('milestoneTitle', title);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  }

  it('hiển thị trạng thái idle với nút Bắt đầu kiểm tra kiến thức khi chưa có proof trước đó', () => {
    mockProveModeService.getLatestProof.mockReturnValue(of(null));
    openDialog();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="prove-idle-state"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="prove-generate-btn"]')).toBeTruthy();
  });

  it('tạo 3 câu hỏi, điền câu trả lời + độ tự tin và nộp bài để hiển thị kết quả thật từ backend', () => {
    const generated: GenerateProofResponseDTO = {
      proof_id: 'proof-gen-1',
      status: 'READY',
      questions: [
        { id: 'q1', prompt: 'Giải thích GIL trong Python?' },
        { id: 'q2', prompt: 'Phân biệt list và tuple?' },
        { id: 'q3', prompt: 'Decorator hoạt động thế nào?' },
      ],
    };
    const submitted: MilestoneProofResponseDTO = {
      id: 'proof-gen-1',
      milestone_id: 'ms-101',
      status: 'PASSED',
      score: 90,
      confidence: 0.8,
      corrective_action: 'Rất tốt, có thể sang chặng tiếp theo.',
      is_verified: true,
      calibration_error: 0.1,
      answer_evidence: [
        { question_id: 'q1', evidence: 'Giải thích đúng mutex của CPython', is_addressed: true },
      ],
    };

    mockProveModeService.getLatestProof.mockReturnValue(of(null));
    mockProveModeService.generateProof.mockReturnValue(of(generated));
    mockProveModeService.submitProof.mockReturnValue(of(submitted));

    openDialog();

    const generateBtn = fixture.nativeElement.querySelector(
      '[data-testid="prove-generate-btn"]'
    ) as HTMLButtonElement;
    generateBtn.click();
    fixture.detectChanges();

    expect(component.questions().length).toBe(3);

    const textarea0 = fixture.nativeElement.querySelector(
      '[data-testid="prove-answer-input-0"]'
    ) as HTMLTextAreaElement;
    textarea0.value = 'GIL là Global Interpreter Lock trong CPython.';
    textarea0.dispatchEvent(new Event('input'));

    const slider = fixture.nativeElement.querySelector(
      '[data-testid="prove-confidence-slider"]'
    ) as HTMLInputElement;
    slider.value = '80';
    slider.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const submitBtn = fixture.nativeElement.querySelector(
      '[data-testid="prove-submit-btn"]'
    ) as HTMLButtonElement;
    submitBtn.click();
    fixture.detectChanges();

    expect(mockProveModeService.submitProof).toHaveBeenCalledWith('ms-101', 'proof-gen-1', {
      answers: [
        { question_id: 'q1', answer: 'GIL là Global Interpreter Lock trong CPython.' },
        { question_id: 'q2', answer: '' },
        { question_id: 'q3', answer: '' },
      ],
      confidence: 0.8,
    });

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="prove-result-panel"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="prove-result-score"]')?.textContent).toContain('90');
    expect(el.querySelector('[data-testid="prove-result-status"]')?.textContent).toContain(
      'PASSED'
    );
  });

  it('khôi phục trạng thái PASSED đã lưu từ backend khi mở lại hộp thoại (reload restore)', () => {
    const persisted: LatestMilestoneProofResponseDTO = {
      id: 'proof-persisted',
      milestone_id: 'ms-101',
      status: 'PASSED',
      score: 85,
      confidence: 0.75,
      corrective_action: 'Đã đạt chuẩn nắm vững.',
      is_verified: true,
      calibration_error: 0.1,
      questions: [],
      answer_evidence: [],
      created_at: '2026-11-21T08:00:00Z',
      updated_at: '2026-11-21T08:10:00Z',
    };
    mockProveModeService.getLatestProof.mockReturnValue(of(persisted));

    openDialog();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="prove-result-panel"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="prove-result-score"]')?.textContent).toContain('85');
  });

  it('hiển thị error banner và nút Thử lại khi generateProof thất bại — KHÔNG tạo câu hỏi giả', () => {
    mockProveModeService.getLatestProof.mockReturnValue(of(null));
    mockProveModeService.generateProof.mockReturnValue(
      throwError(() => new Error('Backend 503'))
    );

    openDialog();

    const generateBtn = fixture.nativeElement.querySelector(
      '[data-testid="prove-generate-btn"]'
    ) as HTMLButtonElement;
    generateBtn.click();
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="prove-error-banner"]')).toBeTruthy();
    expect(el.querySelector('[data-testid="prove-questions-form"]')).toBeNull();
    expect(component.questions().length).toBe(0);

    // Retry invokes generateProof again
    mockProveModeService.generateProof.mockReturnValue(
      of({
        proof_id: 'proof-retry-ok',
        status: 'READY',
        questions: [{ id: 'q1', prompt: 'Câu hỏi thật sau retry' }],
      })
    );
    const retryBtn = el.querySelector('[data-testid="prove-retry-btn"]') as HTMLButtonElement;
    retryBtn.click();
    fixture.detectChanges();

    expect(mockProveModeService.generateProof).toHaveBeenCalledTimes(2);
    expect(el.querySelector('[data-testid="prove-error-banner"]')).toBeNull();
    expect(component.questions().length).toBe(1);
  });

  it('giữ nguyên câu trả lời + proof_id khi chấm điểm gặp 503 AI_GRADING_UNAVAILABLE và cho phép Thử chấm lại thành công', () => {
    const generated: GenerateProofResponseDTO = {
      proof_id: 'proof-retry-503',
      status: 'READY',
      questions: [
        { id: 'q1', prompt: 'Giải thích MVCC trong PostgreSQL?' },
        { id: 'q2', prompt: 'Nêu một lỗi thường gặp với lock?' },
      ],
    };
    const submittedOk: MilestoneProofResponseDTO = {
      id: 'proof-retry-503',
      milestone_id: 'ms-101',
      status: 'PASSED',
      score: 84,
      confidence: 0.75,
      corrective_action: null,
      is_verified: true,
      calibration_error: -0.09,
      answer_evidence: [{ question_id: 'q1', evidence: 'Giải thích đúng MVCC', is_addressed: true }],
    };

    mockProveModeService.getLatestProof.mockReturnValue(of(null));
    mockProveModeService.generateProof.mockReturnValue(of(generated));
    mockProveModeService.submitProof
      .mockReturnValueOnce(
        throwError(() => ({
          status: 503,
          error: {
            code: 'AI_GRADING_UNAVAILABLE',
            detail:
              'Hệ thống chấm điểm AI tạm thời gián đoạn. Câu trả lời của bạn vẫn được giữ nguyên, vui lòng bấm thử chấm lại.',
          },
        }))
      )
      .mockReturnValueOnce(of(submittedOk));

    openDialog();

    const el = fixture.nativeElement as HTMLElement;
    (el.querySelector('[data-testid="prove-generate-btn"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const textarea0 = el.querySelector('[data-testid="prove-answer-input-0"]') as HTMLTextAreaElement;
    textarea0.value = 'MVCC lưu nhiều phiên bản tuple để đọc không chặn ghi.';
    textarea0.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    (el.querySelector('[data-testid="prove-submit-btn"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    // Phase stays on answering, answers & proofId preserved, error banner shown with Thử chấm lại
    expect(component.phase()).toBe('answering');
    expect(component.proofId()).toBe('proof-retry-503');
    expect(component.answersByQuestionId()['q1']).toBe(
      'MVCC lưu nhiều phiên bản tuple để đọc không chặn ghi.'
    );
    expect(el.querySelector('[data-testid="prove-questions-form"]')).toBeTruthy();
    const banner = el.querySelector('[data-testid="prove-error-banner"]');
    expect(banner?.textContent).toContain('Hệ thống chấm điểm AI tạm thời gián đoạn');
    const submitBtn = el.querySelector('[data-testid="prove-submit-btn"]') as HTMLButtonElement;
    expect(submitBtn.textContent).toContain('Thử chấm lại');

    // Retry on the SAME proof_id without regenerating questions
    submitBtn.click();
    fixture.detectChanges();

    expect(mockProveModeService.generateProof).toHaveBeenCalledTimes(1);
    expect(mockProveModeService.submitProof).toHaveBeenCalledTimes(2);
    expect(mockProveModeService.submitProof).toHaveBeenNthCalledWith(
      2,
      'ms-101',
      'proof-retry-503',
      {
        answers: [
          { question_id: 'q1', answer: 'MVCC lưu nhiều phiên bản tuple để đọc không chặn ghi.' },
          { question_id: 'q2', answer: '' },
        ],
        confidence: 0.7,
      }
    );
    expect(component.phase()).toBe('result');
    expect(el.querySelector('[data-testid="prove-result-score"]')?.textContent).toContain('84');
  });

  it('khôi phục chính xác kết quả verified với điểm 0 thật (score=0, is_verified=true)', () => {
    const persistedZero: LatestMilestoneProofResponseDTO = {
      id: 'proof-zero',
      milestone_id: 'ms-101',
      status: 'NEEDS_REVIEW',
      score: 0,
      confidence: 0.5,
      corrective_action: 'Cần ôn tập lại toàn bộ kiến thức nền tảng.',
      is_verified: true,
      calibration_error: 0.5,
      questions: [],
      answer_evidence: [],
      created_at: '2026-11-22T08:00:00Z',
      updated_at: '2026-11-22T08:05:00Z',
    };
    mockProveModeService.getLatestProof.mockReturnValue(of(persistedZero));

    openDialog();

    const el = fixture.nativeElement as HTMLElement;
    expect(component.phase()).toBe('result');
    expect(el.querySelector('[data-testid="prove-result-score"]')?.textContent).toContain('0');
    expect(el.querySelector('[data-testid="prove-result-panel"]')?.textContent).toContain(
      'Kết quả đã được xác thực'
    );
  });
});
