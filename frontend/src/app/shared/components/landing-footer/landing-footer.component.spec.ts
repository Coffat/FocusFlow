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

  it('should initialize with default inputs and render standard footer elements', () => {
    expect(component).toBeTruthy();
    expect(component.brandName()).toBe('FocusFlow');
    expect(component.links().length).toBe(5);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Focus');
    expect(el.textContent).toContain('Flow');
    expect(el.textContent).toContain('SRL Learning Harness');
    expect(el.textContent).toContain('3-Tier Validation Gate • 2-Stage SSE');

    const anchorHrefs = Array.from(el.querySelectorAll('a')).map((a) => a.getAttribute('href'));
    expect(anchorHrefs).toEqual([
      '/',
      '/#methodology',
      '/#capabilities',
      '/pricing',
      '/faq',
    ]);
  });

  it('should accept custom links and statusText', () => {
    fixture.componentRef.setInput('statusText', 'Custom Engine Status');
    fixture.componentRef.setInput('links', [{ label: 'Privacy', href: '/privacy' }]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Custom Engine Status');
    expect(el.textContent).toContain('Privacy');
  });
});
