import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
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
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([])
      ]
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
    expect(compiled.querySelector('.dashboard-viewport')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-state-switcher')).toBeTruthy();
  });

  it('hiển thị KPI grid và Weekly grid khi ở trạng thái normal', () => {
    service.setState('normal');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-dashboard-kpi-grid')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-weekly-grid')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-empty-state')).toBeFalsy();
  });

  it('hiển thị empty state khi ở trạng thái new-user', () => {
    service.setState('new-user');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-dashboard-empty-state')).toBeTruthy();
    expect(compiled.querySelector('app-dashboard-kpi-grid')).toBeFalsy();
  });

  it('điều hướng tới /roadmaps khi bấm phím C ngoài ô input', () => {
    const event = new KeyboardEvent('keydown', { key: 'c' });
    window.dispatchEvent(event);
    expect(router.navigate).toHaveBeenCalledWith(['/roadmaps']);
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

    expect(router.navigate).not.toHaveBeenCalled();
    document.body.removeChild(inputEl);
  });
});
