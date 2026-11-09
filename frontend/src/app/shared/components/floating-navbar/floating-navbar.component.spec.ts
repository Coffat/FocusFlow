import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { FloatingNavbarComponent } from './floating-navbar.component';

describe('FloatingNavbarComponent', () => {
  let component: FloatingNavbarComponent;
  let fixture: ComponentFixture<FloatingNavbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FloatingNavbarComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(FloatingNavbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should initialize with default inputs and mobile menu closed', () => {
    expect(component).toBeTruthy();
    expect(component.brandName()).toBe('FocusFlow');
    expect(component.isAuthenticated()).toBe(false);
    expect(component.mobileMenuOpen()).toBe(false);
    expect(component.navLinks().length).toBe(4);
  });

  it('should render unauthenticated links and CTA', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Đăng nhập');
    expect(el.textContent).toContain('Bắt đầu ngay');
    expect(el.textContent).not.toContain('Vào Dashboard');
  });

  it('should render authenticated CTA when isAuthenticated is true', () => {
    fixture.componentRef.setInput('isAuthenticated', true);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Vào Dashboard');
  });

  it('should toggle and close mobile menu', () => {
    expect(component.mobileMenuOpen()).toBe(false);

    component.toggleMobileMenu();
    expect(component.mobileMenuOpen()).toBe(true);

    component.closeMobileMenu();
    expect(component.mobileMenuOpen()).toBe(false);
  });

  it('should handle smooth scrolling and close mobile menu', () => {
    const scrollSpy = vi.fn();
    Element.prototype.scrollIntoView = scrollSpy;

    component.toggleMobileMenu();
    expect(component.mobileMenuOpen()).toBe(true);

    const fakeEvent = new Event('click');
    const preventSpy = vi.spyOn(fakeEvent, 'preventDefault');

    component.scrollTo('capabilities', fakeEvent);

    expect(preventSpy).toHaveBeenCalled();
    expect(component.mobileMenuOpen()).toBe(false);
  });
});
