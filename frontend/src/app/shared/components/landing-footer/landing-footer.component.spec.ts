import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LandingFooterComponent } from './landing-footer.component';

describe('LandingFooterComponent', () => {
  let component: LandingFooterComponent;
  let fixture: ComponentFixture<LandingFooterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingFooterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(LandingFooterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should render default brand, copyright and status pill', () => {
    expect(component).toBeTruthy();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('FocusFlow');
    expect(el.textContent).toContain('© 2025 FocusFlow Systems Inc');
    expect(el.textContent).toContain('Động cơ Thích ứng: 99.99%');
    expect(el.textContent).toContain('Trạng thái Hệ thống');
  });

  it('should accept custom links and statusText', () => {
    fixture.componentRef.setInput('statusText', 'Hệ thống hoạt động bình thường');
    fixture.componentRef.setInput('links', [{ label: 'Liên hệ', href: '/contact' }]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Hệ thống hoạt động bình thường');
    expect(el.textContent).toContain('Liên hệ');
  });
});
