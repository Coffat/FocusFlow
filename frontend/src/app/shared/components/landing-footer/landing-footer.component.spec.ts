import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { LandingFooterComponent } from './landing-footer.component';

describe('LandingFooterComponent', () => {
  let component: LandingFooterComponent;
  let fixture: ComponentFixture<LandingFooterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingFooterComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(LandingFooterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should render default brand logo, copyright, status pill, and 5 public links', () => {
    expect(component).toBeTruthy();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('FocusFlow');
    expect(el.querySelector('img[src="assets/logo.svg"]')).toBeTruthy();
    expect(el.textContent).toContain(
      '© 2026 FocusFlow — Hệ thống Điều phối Lộ trình Tự học Thích ứng (SRL Learning Harness).'
    );
    expect(el.textContent).toContain('3-Tier Validation Gate • 2-Stage SSE');

    const anchorHrefs = Array.from(el.querySelectorAll('a')).map((a) => a.getAttribute('href'));
    expect(anchorHrefs).toEqual([
      '/',
      '/how-it-works',
      '/features',
      '/pricing',
      '/faq',
    ]);
  });

  it('should accept custom links and statusText', () => {
    fixture.componentRef.setInput('statusText', 'Hệ thống hoạt động bình thường');
    fixture.componentRef.setInput('links', [{ label: 'Liên hệ', href: '/contact' }]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Hệ thống hoạt động bình thường');
    expect(el.textContent).toContain('Liên hệ');
    const link = el.querySelector('a');
    expect(link?.getAttribute('href')).toBe('/contact');
  });
});
