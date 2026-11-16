import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  AiGrillMeDialogComponent,
  STANDARD_PEDAGOGICAL_QUESTIONS,
} from './ai-grill-me-dialog.component';
import { RoadmapService } from '../../../services/roadmap.service';

describe('AiGrillMeDialogComponent', () => {
  let component: AiGrillMeDialogComponent;
  let fixture: ComponentFixture<AiGrillMeDialogComponent>;
  let roadmapService: RoadmapService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AiGrillMeDialogComponent],
      providers: [RoadmapService, provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AiGrillMeDialogComponent);
    component = fixture.componentInstance;
    roadmapService = TestBed.inject(RoadmapService);
    fixture.detectChanges();
  });

  it('hiển thị trạng thái trống với nút Yêu cầu AI Sinh Câu hỏi Làm rõ khi chưa có câu hỏi', () => {
    roadmapService.clarificationQuestions.set([]);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="grill-me-empty-state"]')).toBeTruthy();

    const genSpy = vi.fn();
    component.generateQuestions.subscribe(genSpy);

    const genBtn = compiled.querySelector('[data-testid="generate-questions-btn"]') as HTMLButtonElement;
    genBtn.click();
    expect(genSpy).toHaveBeenCalled();
  });

  it('cập nhật Context Understanding Meter và phát sự kiện submitAnswers khi chọn câu trả lời', () => {
    roadmapService.clarificationQuestions.set(STANDARD_PEDAGOGICAL_QUESTIONS);
    fixture.detectChanges();

    expect(component.answerProgressPercent()).toBe(0);

    const compiled = fixture.nativeElement as HTMLElement;
    const chip = compiled.querySelector('[data-testid="question-0-chip-0"]') as HTMLButtonElement;
    chip.click();
    fixture.detectChanges();

    expect(component.answeredCount()).toBe(1);
    expect(component.answerProgressPercent()).toBeGreaterThan(0);

    const submitSpy = vi.fn();
    component.submitAnswers.subscribe(submitSpy);

    const submitBtn = compiled.querySelector('[data-testid="submit-interview-btn"]') as HTMLButtonElement;
    submitBtn.click();

    expect(submitSpy).toHaveBeenCalledTimes(1);
    expect(submitSpy.mock.calls[0][0].length).toBe(1);
    expect(submitSpy.mock.calls[0][0][0].question_id).toBe('q1');
  });

  it('phát sự kiện skipInterview khi bấm Bỏ qua phỏng vấn', () => {
    const skipSpy = vi.fn();
    component.skipInterview.subscribe(skipSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const skipBtn = compiled.querySelector('[data-testid="skip-interview-btn"]') as HTMLButtonElement;
    skipBtn.click();

    expect(skipSpy).toHaveBeenCalled();
  });

  it('hiển thị màn hình loading tối giản chính giữa khi AI đang sinh câu hỏi', () => {
    roadmapService.clarificationQuestions.set([]);
    roadmapService.isGeneratingQuestions.set(true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const loadingState = compiled.querySelector('[data-testid="grill-me-skeleton-loading"]');
    expect(loadingState).toBeTruthy();
    expect(loadingState?.textContent).toContain('Đang phân tích mục tiêu & chuẩn bị câu hỏi chẩn đoán...');
    expect(loadingState?.textContent).toContain('Hệ thống đang chuẩn bị các câu hỏi phù hợp nhất cho bạn...');

    // Đã loại bỏ các skeleton pulse lộn xộn
    const pulseCards = loadingState?.querySelectorAll('.animate-pulse');
    expect(pulseCards?.length).toBe(0);
  });

  it('hiển thị banner lỗi và nút Thử lại ngay khi có errorMessage và chưa có câu hỏi', () => {
    roadmapService.clarificationQuestions.set([]);
    roadmapService.isGeneratingQuestions.set(false);
    roadmapService.errorMessage.set('Hệ thống AI hiện đang bận hoặc gặp sự cố kết nối. Vui lòng bấm \'Thử lại\' sau giây lát.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const errorBanner = compiled.querySelector('[data-testid="grill-me-error-state"]');
    expect(errorBanner).toBeTruthy();
    expect(errorBanner?.textContent).toContain('Hệ thống AI hiện đang bận hoặc gặp sự cố kết nối');

    const genSpy = vi.fn();
    component.generateQuestions.subscribe(genSpy);

    const retryBtn = compiled.querySelector('[data-testid="retry-generate-questions-btn"]') as HTMLButtonElement;
    expect(retryBtn).toBeTruthy();
    retryBtn.click();
    expect(genSpy).toHaveBeenCalled();
  });

  it('hỗ trợ toggle nhiều options khi câu hỏi là multiple_choice', () => {
    roadmapService.clarificationQuestions.set([
      {
        id: 'q1',
        question_id: 'q1',
        question: 'Chọn các công nghệ mong muốn',
        text: 'Chọn các công nghệ mong muốn',
        placeholder: 'Chọn...',
        question_type: 'multiple_choice',
        options: [
          { id: 'fastapi', label: 'FastAPI' },
          { id: 'docker', label: 'Docker' },
          { id: 'postgresql', label: 'PostgreSQL' },
          { id: 'other', label: 'Khác / Mục tiêu tự định nghĩa' },
        ],
        question_purpose: 'Xác định công nghệ',
        expected_answer_format: 'Chọn nhiều',
        diagnostic_dimension: 'TECH_STACK_DEPTH',
      },
    ]);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const chip0 = compiled.querySelector('[data-testid="question-0-chip-0"]') as HTMLButtonElement;
    const chip1 = compiled.querySelector('[data-testid="question-0-chip-1"]') as HTMLButtonElement;

    // Click FastAPI
    chip0.click();
    fixture.detectChanges();
    expect(component.answersMap()['q1']).toBe('FastAPI');

    // Click Docker -> joins as multiple choice
    chip1.click();
    fixture.detectChanges();
    expect(component.answersMap()['q1']).toBe('FastAPI, Docker');

    // Click FastAPI again -> untoggles FastAPI, leaves Docker
    chip0.click();
    fixture.detectChanges();
    expect(component.answersMap()['q1']).toBe('Docker');
  });

  it('hiển thị Header Card nhỏ gọn với tên mục tiêu, trình độ và badge tiến độ', () => {
    roadmapService.clarificationQuestions.set(STANDARD_PEDAGOGICAL_QUESTIONS);
    fixture.componentRef.setInput('goalTitle', 'Chuyên gia Full-Stack Cloud Native');
    fixture.componentRef.setInput('baselineLevel', 'ADVANCED');
    fixture.componentRef.setInput('weeklyHours', 15);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const headerCard = compiled.querySelector('[data-testid="grill-me-header-card"]');
    expect(headerCard).toBeTruthy();
    expect(headerCard?.textContent).toContain('Chuyên gia Full-Stack Cloud Native');
    expect(headerCard?.textContent).toContain('ADVANCED');
    expect(headerCard?.textContent).toContain('Đã trả lời 0/3 câu hỏi');

    // Bấm xem câu hỏi chuẩn từ footer
    const previewBtn = compiled.querySelector('[data-testid="preview-standard-questions-btn"]') as HTMLButtonElement;
    expect(previewBtn).toBeTruthy();
  });
});
