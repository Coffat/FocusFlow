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

    expect(component.contextUnderstandingPercent()).toBe(40);

    const compiled = fixture.nativeElement as HTMLElement;
    const chip = compiled.querySelector('[data-testid="question-0-chip-0"]') as HTMLButtonElement;
    chip.click();
    fixture.detectChanges();

    expect(component.answeredCount()).toBe(1);
    expect(component.contextUnderstandingPercent()).toBeGreaterThan(40);

    const submitSpy = vi.fn();
    component.submitAnswers.subscribe(submitSpy);

    const submitBtn = compiled.querySelector('[data-testid="submit-interview-btn"]') as HTMLButtonElement;
    submitBtn.click();

    expect(submitSpy).toHaveBeenCalledTimes(1);
    expect(submitSpy.mock.calls[0][0].length).toBe(3);
  });

  it('phát sự kiện skipInterview khi bấm Bỏ qua phỏng vấn', () => {
    const skipSpy = vi.fn();
    component.skipInterview.subscribe(skipSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const skipBtn = compiled.querySelector('[data-testid="skip-interview-btn"]') as HTMLButtonElement;
    skipBtn.click();

    expect(skipSpy).toHaveBeenCalled();
  });
});
