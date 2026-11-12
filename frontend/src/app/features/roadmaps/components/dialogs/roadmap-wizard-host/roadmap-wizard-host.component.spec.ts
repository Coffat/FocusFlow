import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { RoadmapWizardHostComponent } from './roadmap-wizard-host.component';
import { RoadmapService } from '../../../services/roadmap.service';
import { API_ENDPOINTS } from '../../../../../core/constants/api-endpoints';

describe('RoadmapWizardHostComponent', () => {
  let component: RoadmapWizardHostComponent;
  let fixture: ComponentFixture<RoadmapWizardHostComponent>;
  let roadmapService: RoadmapService;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoadmapWizardHostComponent],
      providers: [RoadmapService, provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(RoadmapWizardHostComponent);
    component = fixture.componentInstance;
    roadmapService = TestBed.inject(RoadmapService);
    httpTesting = TestBed.inject(HttpTestingController);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('không tự ý chuyển sang Bước 2 nếu API createRoadmap trả lỗi (giữ nguyên Bước 1 và hiển thị banner lỗi)', () => {
    expect(component.currentStep()).toBe(1);

    component.onGoalSubmit({
      title: 'AWS Solutions Architect',
      description: 'Test',
      goal_title: 'AWS Solutions Architect',
      goal_description: 'Test',
      prior_knowledge_level: 'BEGINNER',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
    });

    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    req.flush(
      { message: 'Máy chủ AI hiện không khả dụng.' },
      { status: 503, statusText: 'Service Unavailable' }
    );
    fixture.detectChanges();

    expect(component.currentStep()).toBe(1);
    expect(roadmapService.errorMessage()).toBe('Máy chủ AI hiện không khả dụng.');

    const compiled = fixture.nativeElement as HTMLElement;
    const alertBanner = compiled.querySelector('[data-testid="wizard-error-banner"]');
    expect(alertBanner).toBeTruthy();
    expect(alertBanner?.textContent).toContain('Máy chủ AI hiện không khả dụng.');
  });

  it('tự động chuyển sang Bước 2 khi API createRoadmap thành công', () => {
    component.onGoalSubmit({
      title: 'IELTS 7.5 Academic',
      description: 'Test',
      goal_title: 'IELTS 7.5 Academic',
      goal_description: 'Test',
      prior_knowledge_level: 'INTERMEDIATE',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
    });

    const req = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.BASE);
    req.flush({
      id: 'rm-100',
      user_id: 'usr-1',
      goal_id: 'goal-100',
      title: 'IELTS 7.5 Academic',
      description: 'Test',
      status: 'INITIALIZED',
      start_date: '2026-11-12',
      target_date: '2027-02-01',
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    });

    const clarifyReq = httpTesting.expectOne(API_ENDPOINTS.ROADMAPS.CLARIFY_QUESTIONS('goal-100'));
    clarifyReq.flush({ questions: [] });
    fixture.detectChanges();

    expect(component.currentStep()).toBe(2);
  });

  it('cho phép người dùng click trực tiếp vào 4-Step Stepper trên Header để kiểm tra giao diện từng bước', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const step3Btn = compiled.querySelector('[data-testid="wizard-step-btn-3"]') as HTMLButtonElement;
    step3Btn.click();
    fixture.detectChanges();
    expect(component.currentStep()).toBe(3);

    const step4Btn = compiled.querySelector('[data-testid="wizard-step-btn-4"]') as HTMLButtonElement;
    step4Btn.click();
    fixture.detectChanges();
    expect(component.currentStep()).toBe(4);
  });
});
