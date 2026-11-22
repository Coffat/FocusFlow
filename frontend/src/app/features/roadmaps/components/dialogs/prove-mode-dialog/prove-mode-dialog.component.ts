import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { Subscription } from 'rxjs';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  X,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Send,
  BookOpen,
  ShieldCheck,
} from 'lucide-angular';
import {
  ProveModeService,
  LatestMilestoneProofResponseDTO,
  MilestoneProofResponseDTO,
} from '../../../services/prove-mode.service';

interface ParsedProofQuestion {
  readonly id: string;
  readonly prompt: string;
  readonly topic?: string;
}

interface ParsedAnswerEvidence {
  readonly question_id: string;
  readonly evidence: string;
  readonly is_addressed: boolean;
}

interface ProofResultView {
  readonly id: string;
  readonly milestone_id: string;
  readonly status: string;
  readonly score: number;
  readonly confidence: number;
  readonly corrective_action: string | null;
  readonly is_verified: boolean;
  readonly calibration_error: number | null;
  readonly answer_evidence: readonly ParsedAnswerEvidence[];
}

type ProvePhase = 'loading' | 'idle' | 'generating' | 'answering' | 'submitting' | 'result';
type RetryAction = 'loadLatest' | 'generate' | 'submit' | null;

@Component({
  selector: 'app-prove-mode-dialog',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, DecimalPipe, LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        X,
        Sparkles,
        CheckCircle2,
        AlertTriangle,
        RefreshCw,
        Send,
        BookOpen,
        ShieldCheck,
      }),
    },
  ],
  template: `
    @if (open()) {
      <div
        class="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px] transition-opacity"
        (click)="onClose()"
        aria-hidden="true"
      ></div>

      <div
        class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 pointer-events-none"
        (keydown.escape)="onClose()"
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="prove-mode-dialog-title"
          data-testid="prove-mode-dialog"
          class="pointer-events-auto w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-[#EAE8E7] bg-[#FBF9F8] text-[#1B1C1C] shadow-2xl flex flex-col"
        >
          <!-- Header -->
          <div class="flex items-start justify-between gap-4 px-6 py-5 bg-white border-b border-[#EAE8E7] rounded-t-2xl">
            <div class="space-y-1 min-w-0">
              <div class="inline-flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                <lucide-icon name="shield-check" [size]="14"></lucide-icon>
                <span>Chế độ Chứng minh Kiến thức (Prove Mode)</span>
              </div>
              <h2
                id="prove-mode-dialog-title"
                class="text-lg sm:text-xl font-serif font-bold text-[#1B1C1C] leading-snug break-words"
              >
                {{ milestoneTitle() || 'Kiểm tra hiểu sâu chặng học' }}
              </h2>
            </div>

            <button
              type="button"
              data-testid="prove-close-btn"
              aria-label="Đóng hộp thoại chứng minh kiến thức"
              (click)="onClose()"
              class="p-2 rounded-xl text-[#656464] hover:text-[#1B1C1C] hover:bg-neutral-100 transition-colors cursor-pointer shrink-0"
            >
              <lucide-icon name="x" [size]="18"></lucide-icon>
            </button>
          </div>

          <!-- Body -->
          <div class="p-6 space-y-5 flex-1">
            <!-- Error Banner -->
            @if (errorMessage(); as errMsg) {
              <div
                role="alert"
                data-testid="prove-error-banner"
                class="p-4 rounded-xl border border-rose-200 bg-rose-50/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div class="flex items-start gap-2.5">
                  <lucide-icon
                    name="alert-triangle"
                    [size]="18"
                    class="text-[#BA1A1A] shrink-0 mt-0.5"
                  ></lucide-icon>
                  <div class="space-y-0.5">
                    <p class="text-xs font-bold text-[#1B1C1C]">Đã xảy ra lỗi khi xử lý</p>
                    <p class="text-xs text-[#656464]">{{ errMsg }}</p>
                  </div>
                </div>
                @if (lastFailedAction()) {
                  <button
                    type="button"
                    data-testid="prove-retry-btn"
                    (click)="onRetry()"
                    class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors cursor-pointer shrink-0 self-start sm:self-auto"
                  >
                    <lucide-icon name="refresh-cw" [size]="13"></lucide-icon>
                    <span>{{ lastFailedAction() === 'submit' ? 'Thử chấm lại' : 'Thử lại' }}</span>
                  </button>
                }
              </div>
            }

            <!-- Loading / Generating / Submitting States -->
            @if (phase() === 'loading' || phase() === 'generating' || phase() === 'submitting') {
              <div
                role="status"
                aria-live="polite"
                data-testid="prove-loading-state"
                class="p-8 rounded-2xl border border-[#EAE8E7] bg-white flex flex-col items-center justify-center gap-3 text-center"
              >
                <div class="w-8 h-8 border-2 border-[#246B4A]/25 border-t-[#246B4A] rounded-full animate-spin"></div>
                <p class="text-sm font-semibold text-[#1B1C1C]">
                  @if (phase() === 'loading') {
                    Đang tải trạng thái kiểm tra kiến thức...
                  } @else if (phase() === 'generating') {
                    AI đang tạo 3 câu hỏi kiểm tra hiểu sâu...
                  } @else {
                    Máy chủ đang chấm điểm và đối chiếu mức độ tự tin...
                  }
                </p>
                <p class="text-xs text-[#656464]">
                  Vui lòng đợi trong giây lát, không đóng cửa sổ nếu bạn đang nộp bài.
                </p>
              </div>
            }

            <!-- Idle State: No proof yet -->
            @if (phase() === 'idle') {
              <div
                data-testid="prove-idle-state"
                class="p-6 sm:p-8 rounded-2xl border border-[#EAE8E7] bg-white text-center space-y-4"
              >
                <div class="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-200 text-[#246B4A] flex items-center justify-center mx-auto">
                  <lucide-icon name="book-open" [size]="22"></lucide-icon>
                </div>
                <div class="space-y-1.5 max-w-md mx-auto">
                  <h3 class="text-base font-serif font-bold text-[#1B1C1C]">
                    Sẵn sàng kiểm chứng kiến thức chặng này?
                  </h3>
                  <p class="text-xs sm:text-sm text-[#656464] leading-relaxed">
                    AI sẽ sinh 3 câu hỏi gợi nhớ chủ động (Active Recall) bám sát nội dung chặng học. Kết quả được chấm điểm tất định và lưu vào hồ sơ làm chủ kiến thức của bạn.
                  </p>
                </div>
                <div class="pt-1">
                  <button
                    type="button"
                    data-testid="prove-generate-btn"
                    (click)="onGenerateQuestions()"
                    class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs sm:text-sm font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors shadow-xs cursor-pointer"
                  >
                    <lucide-icon name="sparkles" [size]="15"></lucide-icon>
                    <span>Bắt đầu kiểm tra kiến thức</span>
                  </button>
                </div>
              </div>
            }

            <!-- Answering State -->
            @if (phase() === 'answering') {
              <div data-testid="prove-questions-form" class="space-y-5">
                <div class="space-y-4">
                  @for (q of questions(); track q.id; let idx = $index) {
                    <div
                      [attr.data-testid]="'prove-question-card-' + idx"
                      class="p-4 sm:p-5 rounded-2xl border border-[#EAE8E7] bg-white space-y-2.5"
                    >
                      <div class="flex items-start justify-between gap-2">
                        <label
                          [attr.for]="'prove-answer-' + q.id"
                          class="text-sm font-semibold text-[#1B1C1C] leading-snug"
                        >
                          <span class="text-xs font-mono text-[#246B4A] mr-1.5">Câu {{ idx + 1 }}.</span>
                          {{ q.prompt }}
                        </label>
                      </div>
                      <textarea
                        [id]="'prove-answer-' + q.id"
                        [attr.data-testid]="'prove-answer-input-' + idx"
                        rows="3"
                        [value]="answersByQuestionId()[q.id] || ''"
                        (input)="onAnswerChange(q.id, $event)"
                        placeholder="Trình bày câu trả lời bằng ngôn ngữ của bạn..."
                        class="w-full px-3.5 py-2.5 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] text-sm text-[#1B1C1C] focus:outline-none focus:bg-white focus:border-[#246B4A] focus:ring-1 focus:ring-[#246B4A] transition-colors resize-y"
                      ></textarea>
                    </div>
                  }
                </div>

                <!-- Confidence Calibration Slider -->
                <div class="p-4 sm:p-5 rounded-2xl border border-[#EAE8E7] bg-white space-y-3">
                  <div class="flex items-center justify-between gap-2">
                    <label
                      for="prove-confidence-slider"
                      class="text-xs font-mono uppercase tracking-wider font-semibold text-[#1B1C1C]"
                    >
                      Mức độ tự tin của bạn trước khi chấm điểm
                    </label>
                    <span
                      data-testid="prove-confidence-value"
                      class="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-50 text-[#246B4A] border border-emerald-200"
                    >
                      {{ confidencePercent() }}%
                    </span>
                  </div>
                  <input
                    id="prove-confidence-slider"
                    data-testid="prove-confidence-slider"
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    [value]="confidencePercent()"
                    (input)="onConfidenceChange($event)"
                    class="w-full accent-[#246B4A] cursor-pointer"
                  />
                  <div class="flex justify-between text-[11px] font-mono text-[#656464]">
                    <span>0% (Chưa chắc chắn)</span>
                    <span>50% (Tạm ổn)</span>
                    <span>100% (Rất tự tin)</span>
                  </div>
                </div>

                <!-- Actions -->
                <div class="flex items-center justify-end gap-3 pt-1">
                  <button
                    type="button"
                    (click)="onClose()"
                    class="px-4 py-2.5 rounded-full text-xs font-semibold border border-[#EAE8E7] bg-white text-[#656464] hover:text-[#1B1C1C] hover:bg-neutral-100 transition-colors cursor-pointer"
                  >
                    Hủy
                  </button>
                  <button
                    type="button"
                    data-testid="prove-submit-btn"
                    [disabled]="!hasAnyAnswer()"
                    (click)="onSubmitAnswers()"
                    class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs sm:text-sm font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors shadow-xs cursor-pointer disabled:opacity-45 disabled:cursor-not-allowed"
                  >
                    <lucide-icon name="send" [size]="14"></lucide-icon>
                    <span>{{ lastFailedAction() === 'submit' ? 'Thử chấm lại' : 'Nộp bài kiểm tra' }}</span>
                  </button>
                </div>
              </div>
            }

            <!-- Result State -->
            @if (phase() === 'result' && result(); as r) {
              <div data-testid="prove-result-panel" class="space-y-5">
                <!-- Score Summary Card -->
                <div
                  class="p-5 sm:p-6 rounded-2xl border bg-white space-y-4"
                  [class.border-emerald-200]="r.status === 'PASSED'"
                  [class.border-amber-200]="r.status !== 'PASSED'"
                >
                  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div class="space-y-1">
                      <span
                        data-testid="prove-result-status"
                        class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold uppercase border"
                        [class.bg-emerald-50]="r.status === 'PASSED'"
                        [class.text-[#246B4A]]="r.status === 'PASSED'"
                        [class.border-emerald-200]="r.status === 'PASSED'"
                        [class.bg-amber-50]="r.status !== 'PASSED'"
                        [class.text-amber-800]="r.status !== 'PASSED'"
                        [class.border-amber-200]="r.status !== 'PASSED'"
                      >
                        <lucide-icon
                          [name]="r.status === 'PASSED' ? 'check-circle-2' : 'alert-triangle'"
                          [size]="13"
                        ></lucide-icon>
                        <span>
                          {{ r.status === 'PASSED' ? 'Đạt yêu cầu (PASSED)' : 'Cần ôn tập thêm (' + r.status + ')' }}
                        </span>
                      </span>
                      <p class="text-xs text-[#656464] pt-1">
                        {{ r.is_verified ? 'Kết quả đã được xác thực và lưu vào hồ sơ làm chủ kiến thức.' : 'Kết quả đang chờ xác thực bổ sung.' }}
                      </p>
                    </div>

                    <div class="text-left sm:text-right">
                      <span class="text-[11px] font-mono uppercase tracking-wider text-[#656464] block">
                        Điểm đánh giá
                      </span>
                      <div
                        data-testid="prove-result-score"
                        class="text-3xl font-serif font-bold text-[#1B1C1C]"
                      >
                        {{ r.score }}<span class="text-base font-normal text-[#656464]">/100</span>
                      </div>
                    </div>
                  </div>

                  <!-- Calibration Telemetry -->
                  <div class="grid grid-cols-2 gap-3 pt-3 border-t border-[#EAE8E7]">
                    <div class="p-3 rounded-xl bg-[#FBF9F8] border border-[#EAE8E7]">
                      <span class="text-[10px] font-mono uppercase tracking-wider text-[#656464] block">
                        Độ tự tin đã khai báo
                      </span>
                      <span class="text-sm font-mono font-bold text-[#1B1C1C]">
                        {{ r.confidence * 100 | number: '1.0-0' }}%
                      </span>
                    </div>
                    <div class="p-3 rounded-xl bg-[#FBF9F8] border border-[#EAE8E7]">
                      <span class="text-[10px] font-mono uppercase tracking-wider text-[#656464] block">
                        Sai số hiệu chuẩn (Calibration Error)
                      </span>
                      <span class="text-sm font-mono font-bold text-[#1B1C1C]">
                        @if (r.calibration_error !== null && r.calibration_error !== undefined) {
                          {{ r.calibration_error | number: '1.2-2' }}
                        } @else {
                          —
                        }
                      </span>
                    </div>
                  </div>

                  <!-- Corrective Action -->
                  @if (r.corrective_action) {
                    <div
                      data-testid="prove-corrective-action"
                      class="p-4 rounded-xl border border-emerald-200/80 bg-emerald-50/40 space-y-1"
                    >
                      <span class="text-[11px] font-mono uppercase tracking-wider font-semibold text-[#246B4A] block">
                        Gợi ý hành động tiếp theo
                      </span>
                      <p class="text-xs sm:text-sm text-[#1B1C1C] leading-relaxed">
                        {{ r.corrective_action }}
                      </p>
                    </div>
                  }
                </div>

                <!-- Per-Question Answer Evidence -->
                @if (r.answer_evidence.length > 0) {
                  <div class="space-y-2.5">
                    <h3 class="text-xs font-mono uppercase tracking-wider font-semibold text-[#656464]">
                      Chi tiết đánh giá từng câu trả lời
                    </h3>
                    <div class="space-y-2">
                      @for (ev of r.answer_evidence; track ev.question_id; let idx = $index) {
                        <div class="p-3.5 rounded-xl border border-[#EAE8E7] bg-white flex items-start justify-between gap-3">
                          <div class="space-y-1 min-w-0">
                            <div class="text-xs font-mono font-semibold text-[#1B1C1C]">
                              Câu {{ idx + 1 }} ({{ ev.question_id }})
                            </div>
                            <p class="text-xs text-[#656464] leading-relaxed">
                              {{ ev.evidence }}
                            </p>
                          </div>
                          <span
                            class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase shrink-0 border"
                            [class.bg-emerald-50]="ev.is_addressed"
                            [class.text-[#246B4A]]="ev.is_addressed"
                            [class.border-emerald-200]="ev.is_addressed"
                            [class.bg-rose-50]="!ev.is_addressed"
                            [class.text-[#BA1A1A]]="!ev.is_addressed"
                            [class.border-rose-200]="!ev.is_addressed"
                          >
                            {{ ev.is_addressed ? 'Đạt ý' : 'Còn thiếu' }}
                          </span>
                        </div>
                      }
                    </div>
                  </div>
                }

                <!-- Footer Actions -->
                <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2.5 pt-1">
                  <button
                    type="button"
                    data-testid="prove-retake-btn"
                    (click)="onGenerateQuestions()"
                    class="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-full text-xs font-semibold border border-[#EAE8E7] bg-white text-[#1B1C1C] hover:border-[#246B4A] hover:text-[#246B4A] transition-colors cursor-pointer"
                  >
                    <lucide-icon name="refresh-cw" [size]="13"></lucide-icon>
                    <span>Làm lại bài kiểm tra mới</span>
                  </button>
                  <button
                    type="button"
                    (click)="onClose()"
                    class="inline-flex items-center justify-center gap-1.5 px-5 py-2.5 rounded-full text-xs font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors cursor-pointer"
                  >
                    <span>Hoàn tất</span>
                  </button>
                </div>
              </div>
            }
          </div>
        </div>
      </div>
    }
  `,
})
export class ProveModeDialogComponent {
  private readonly proveModeService = inject(ProveModeService);
  private readonly destroyRef = inject(DestroyRef);

  readonly open = input<boolean>(false);
  readonly milestoneId = input<string | null>(null);
  readonly milestoneTitle = input<string>('');

  readonly closeModal = output<void>();
  readonly proofSubmitted = output<MilestoneProofResponseDTO>();

  readonly phase = signal<ProvePhase>('idle');
  readonly proofId = signal<string | null>(null);
  readonly questions = signal<readonly ParsedProofQuestion[]>([]);
  readonly answersByQuestionId = signal<Record<string, string>>({});
  readonly confidencePercent = signal<number>(70);
  readonly result = signal<ProofResultView | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly lastFailedAction = signal<RetryAction>(null);

  readonly hasAnyAnswer = computed<boolean>(() => {
    const map = this.answersByQuestionId();
    return Object.values(map).some((v) => v.trim().length > 0);
  });

  private activeSub?: Subscription;

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.cancelActiveRequest();
    });

    effect(() => {
      const isOpen = this.open();
      const mId = this.milestoneId();
      if (isOpen && mId) {
        this.loadLatestProof(mId);
      } else if (!isOpen) {
        this.cancelActiveRequest();
      }
    });
  }

  onClose(): void {
    this.cancelActiveRequest();
    this.closeModal.emit();
  }

  onAnswerChange(questionId: string, event: Event): void {
    const value = (event.target as HTMLTextAreaElement).value;
    this.answersByQuestionId.update((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  }

  onConfidenceChange(event: Event): void {
    const raw = Number((event.target as HTMLInputElement).value);
    const clamped = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 70;
    this.confidencePercent.set(clamped);
  }

  onRetry(): void {
    const action = this.lastFailedAction();
    const mId = this.milestoneId();
    if (!mId) {
      return;
    }
    if (action === 'loadLatest') {
      this.loadLatestProof(mId);
    } else if (action === 'generate') {
      this.onGenerateQuestions();
    } else if (action === 'submit') {
      this.onSubmitAnswers();
    }
  }

  onGenerateQuestions(): void {
    const mId = this.milestoneId();
    if (!mId) {
      return;
    }

    this.cancelActiveRequest();
    this.errorMessage.set(null);
    this.lastFailedAction.set(null);
    this.phase.set('generating');

    this.activeSub = this.proveModeService.generateProof(mId).subscribe({
      next: (res) => {
        const parsed = this.parseQuestions(res.questions);
        if (parsed.length === 0) {
          this.phase.set('idle');
          this.errorMessage.set('Máy chủ không trả về câu hỏi hợp lệ. Vui lòng thử lại.');
          this.lastFailedAction.set('generate');
          return;
        }
        this.proofId.set(res.proof_id);
        this.questions.set(parsed);
        this.answersByQuestionId.set({});
        this.confidencePercent.set(70);
        this.result.set(null);
        this.phase.set('answering');
      },
      error: () => {
        this.phase.set(this.result() ? 'result' : 'idle');
        this.errorMessage.set(
          'Không thể tạo bộ câu hỏi kiểm tra kiến thức lúc này. Vui lòng thử lại sau.'
        );
        this.lastFailedAction.set('generate');
      },
    });
  }

  onSubmitAnswers(): void {
    const mId = this.milestoneId();
    const pId = this.proofId();
    if (!mId || !pId || !this.hasAnyAnswer()) {
      return;
    }

    this.cancelActiveRequest();
    this.errorMessage.set(null);
    this.lastFailedAction.set(null);
    this.phase.set('submitting');

    const answersMap = this.answersByQuestionId();
    const answers = this.questions().map((q) => ({
      question_id: q.id,
      answer: (answersMap[q.id] ?? '').trim(),
    }));
    const confidence = Math.round(this.confidencePercent()) / 100;

    this.activeSub = this.proveModeService
      .submitProof(mId, pId, { answers, confidence })
      .subscribe({
        next: (res) => {
          this.result.set({
            id: res.id,
            milestone_id: res.milestone_id,
            status: res.status,
            score: res.score,
            confidence: res.confidence,
            corrective_action: res.corrective_action,
            is_verified: res.is_verified,
            calibration_error: res.calibration_error ?? null,
            answer_evidence: this.parseAnswerEvidence(res.answer_evidence),
          });
          this.phase.set('result');
          this.proofSubmitted.emit(res);
        },
        error: (err: unknown) => {
          const { status, code, detail } = this.extractErrorPayload(err);
          if (status === 409 || code === 'PROOF_ALREADY_GRADED') {
            this.loadLatestProof(mId);
            return;
          }
          this.phase.set('answering');
          if (status === 503 || code === 'AI_GRADING_UNAVAILABLE') {
            this.errorMessage.set(
              detail ??
                'Hệ thống chấm điểm AI tạm thời gián đoạn. Câu trả lời của bạn vẫn được giữ nguyên, vui lòng bấm thử chấm lại.'
            );
          } else if (status === 429 || code === 'QUOTA_EXHAUSTED') {
            this.errorMessage.set(
              detail ??
                'Bạn đã hết hạn mức lượt gọi AI trong tháng. Câu trả lời của bạn vẫn được giữ nguyên.'
            );
          } else {
            this.errorMessage.set(
              detail ??
                'Không thể nộp bài kiểm tra kiến thức. Câu trả lời của bạn vẫn được giữ nguyên, vui lòng bấm thử chấm lại.'
            );
          }
          this.lastFailedAction.set('submit');
        },
      });
  }

  private loadLatestProof(milestoneId: string): void {
    this.cancelActiveRequest();
    this.errorMessage.set(null);
    this.lastFailedAction.set(null);
    this.phase.set('loading');

    this.activeSub = this.proveModeService.getLatestProof(milestoneId).subscribe({
      next: (latest) => {
        this.applyLatestProofState(latest);
      },
      error: () => {
        this.phase.set('idle');
        this.errorMessage.set(
          'Không thể tải lịch sử kiểm tra kiến thức của chặng học này. Vui lòng thử lại.'
        );
        this.lastFailedAction.set('loadLatest');
      },
    });
  }

  private applyLatestProofState(latest: LatestMilestoneProofResponseDTO | null): void {
    if (!latest) {
      this.proofId.set(null);
      this.questions.set([]);
      this.answersByQuestionId.set({});
      this.result.set(null);
      this.phase.set('idle');
      return;
    }

    if (latest.status === 'READY' && latest.score == null) {
      const parsed = this.parseQuestions(latest.questions);
      this.proofId.set(latest.id);
      this.questions.set(parsed);
      this.answersByQuestionId.set({});
      this.confidencePercent.set(
        latest.confidence != null ? Math.round(latest.confidence * 100) : 70
      );
      this.result.set(null);
      this.phase.set(parsed.length > 0 ? 'answering' : 'idle');
      return;
    }

    this.proofId.set(latest.id);
    this.questions.set(this.parseQuestions(latest.questions));
    this.result.set({
      id: latest.id,
      milestone_id: latest.milestone_id,
      status: latest.status,
      score: latest.score ?? 0,
      confidence: latest.confidence ?? 0,
      corrective_action: latest.corrective_action ?? null,
      is_verified: latest.is_verified,
      calibration_error: latest.calibration_error ?? null,
      answer_evidence: this.parseAnswerEvidence(latest.answer_evidence),
    });
    this.phase.set('result');
  }

  private parseQuestions(
    raw: readonly Record<string, unknown>[] | undefined
  ): readonly ParsedProofQuestion[] {
    if (!Array.isArray(raw)) {
      return [];
    }
    return raw
      .map((item, idx) => {
        const id = typeof item['id'] === 'string' && item['id'].trim() ? item['id'] : `q${idx + 1}`;
        const promptRaw = item['prompt'] ?? item['question'] ?? item['text'];
        const prompt = typeof promptRaw === 'string' ? promptRaw.trim() : '';
        const topic = typeof item['topic'] === 'string' ? item['topic'] : undefined;
        return { id, prompt, topic };
      })
      .filter((q) => q.prompt.length > 0);
  }

  private parseAnswerEvidence(
    raw: readonly Record<string, unknown>[] | undefined
  ): readonly ParsedAnswerEvidence[] {
    if (!Array.isArray(raw)) {
      return [];
    }
    return raw.map((item, idx) => ({
      question_id:
        typeof item['question_id'] === 'string' && item['question_id'].trim()
          ? item['question_id']
          : `q${idx + 1}`,
      evidence:
        typeof item['evidence'] === 'string'
          ? item['evidence']
          : typeof item['feedback'] === 'string'
            ? item['feedback']
            : 'Đã ghi nhận câu trả lời.',
      is_addressed: Boolean(item['is_addressed']),
    }));
  }

  private extractErrorPayload(err: unknown): { status?: number; code?: string; detail?: string } {
    if (typeof err !== 'object' || err === null) {
      return {};
    }
    const status =
      'status' in err && typeof (err as { status?: unknown }).status === 'number'
        ? (err as { status: number }).status
        : undefined;
    const body = 'error' in err ? (err as { error?: unknown }).error : undefined;
    if (typeof body !== 'object' || body === null) {
      return { status };
    }
    const code =
      'code' in body && typeof (body as { code?: unknown }).code === 'string'
        ? (body as { code: string }).code
        : undefined;
    const detail =
      'detail' in body && typeof (body as { detail?: unknown }).detail === 'string'
        ? (body as { detail: string }).detail
        : undefined;
    return { status, code, detail };
  }

  private cancelActiveRequest(): void {
    this.activeSub?.unsubscribe();
    this.activeSub = undefined;
  }
}
