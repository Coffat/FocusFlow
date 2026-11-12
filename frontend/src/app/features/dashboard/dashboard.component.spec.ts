import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DashboardComponent } from './dashboard.component';
import { DashboardService } from './services/dashboard.service';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let router: Router;
  let service: DashboardService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    service = TestBed.inject(DashboardService);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('khởi tạo thành công và hiển thị giao diện dashboard', () => {
    expect(component).toBeTruthy();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.dashboard-page-container')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="dashboard-create-roadmap-btn"]')).toBeTruthy();
  });

  it('hiển thị KPI grid và Weekly grid khi có lộ trình học', () => {
    service.summary.set({
      ...service.summary(),
      activeRoadmaps: [
        {
          id: 'rm-1',
          title: 'IELTS Academic',
          category: 'English',
          progressPercentage: 40,
          totalTasks: 20,
          completedTasks: 8,
          nextTaskTitle: 'Next',
          deadline: '2026-12-31',
        },
      ],
    });
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-dashboard-kpi-grid')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-weekly-grid')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-empty-state')).toBeFalsy();
  });

  it('hiển thị empty state khi ở trạng thái new-user và mở Wizard Dialog khi bấm Tạo Lộ trình Học tập Đầu tiên với AI', () => {
    service.setState('new-user');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-dashboard-empty-state')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-kpi-grid')).toBeFalsy();

    const emptyCtaBtn = compiled.querySelector(
      '[data-testid="empty-state-cta-btn"]'
    ) as HTMLButtonElement;
    expect(emptyCtaBtn).toBeTruthy();
    emptyCtaBtn.click();
    fixture.detectChanges();

    expect(component.wizardOpen()).toBe(true);
    expect(component.wizardStep()).toBe(1);
  });

  it('mở RoadmapWizardHostComponent ở Bước 1 khi bấm phím C ngoài ô input hoặc bấm nút Khởi tạo Lộ trình Mới với AI', () => {
    expect(component.wizardOpen()).toBe(false);
    const event = new KeyboardEvent('keydown', { key: 'c' });
    window.dispatchEvent(event);
    expect(component.wizardOpen()).toBe(true);
    expect(component.wizardStep()).toBe(1);
  });

  it('điều hướng tới /workspace khi bấm phím Space ngoài ô input', () => {
    const event = new KeyboardEvent('keydown', { code: 'Space' });
    window.dispatchEvent(event);
    expect(router.navigate).toHaveBeenCalledWith(['/workspace']);
  });

  it('bỏ qua phím tắt khi người dùng đang gõ trong ô input', () => {
    vi.clearAllMocks();
    const inputEl = document.createElement('input');
    document.body.appendChild(inputEl);
    inputEl.focus();

    const event = new KeyboardEvent('keydown', { key: 'c', bubbles: true });
    inputEl.dispatchEvent(event);

    expect(component.wizardOpen()).toBe(false);
    document.body.removeChild(inputEl);
  });
});
