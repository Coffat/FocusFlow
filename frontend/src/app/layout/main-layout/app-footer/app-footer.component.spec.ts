import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AppFooterComponent } from './app-footer.component';

describe('AppFooterComponent', () => {
  let component: AppFooterComponent;
  let fixture: ComponentFixture<AppFooterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppFooterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AppFooterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công AppFooterComponent', () => {
    expect(component).toBeTruthy();
  });

  it('hiển thị đầy đủ trạng thái hệ thống: Gemini 1.5 Pro, WebCal Sync và WCAG 2.2 AA', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Gemini 1.5 Pro via SSE');
    expect(el.textContent).toContain('WebCal Sync');
    expect(el.textContent).toContain('WCAG 2.2 AA');
  });

  it('hiển thị gợi ý phím tắt', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('⌘K');
    expect(el.textContent).toContain('C');
    expect(el.textContent).toContain('Space');
  });
});
