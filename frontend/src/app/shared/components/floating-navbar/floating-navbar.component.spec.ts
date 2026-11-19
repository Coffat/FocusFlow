import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { FloatingNavbarComponent } from './floating-navbar.component';

describe('FloatingNavbarComponent', () => {
  let component: FloatingNavbarComponent;
  let fixture: ComponentFixture<FloatingNavbarComponent>;

  beforeEach(async () => {
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true, configurable: true });
    await TestBed.configureTestingModule({
      imports: [FloatingNavbarComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(FloatingNavbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should initialize with default inputs, official logo, and mobile menu closed', () => {
    expect(component).toBeTruthy();
    expect(component.brandName()).toBe('FocusFlow');
    expect(component.isAuthenticated()).toBe(false);
    expect(component.mobileMenuOpen()).toBe(false);
    expect(component.navLinks().length).toBe(5);
    expect(component.navLinks()).toEqual([
      { label: 'Trang chủ', href: '/', exact: true },
      { label: 'Cách hoạt động', href: '/how-it-works' },
      { label: 'Tính năng', href: '/#capabilities' },
      { label: 'Kịch bản mẫu', href: '/#scenarios' },
      { label: 'Minh chứng', href: '/#testimonials' },
    ]);

    const el = fixture.nativeElement as HTMLElement;
    const logoImg = el.querySelector('img[src="assets/logo.svg"]');
    expect(logoImg).toBeTruthy();
    expect(el.textContent).toContain('Kịch bản mẫu');
  });

  it('should render unauthenticated links and CTA', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Đăng nhập');
    expect(el.textContent).toContain('Bắt đầu ngay');
    expect(el.textContent).not.toContain('Vào Dashboard');
  });

  it('should render dashboard CTA when authenticated', () => {
    fixture.componentRef.setInput('isAuthenticated', true);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Vào Dashboard');
  });

  it('should toggle mobile menu open and closed', () => {
    expect(component.mobileMenuOpen()).toBe(false);

    component.toggleMobileMenu();
    expect(component.mobileMenuOpen()).toBe(true);

    component.toggleMobileMenu();
    expect(component.mobileMenuOpen()).toBe(false);
  });

  it('should close mobile menu explicitly', () => {
    component.toggleMobileMenu();
    expect(component.mobileMenuOpen()).toBe(true);

    component.closeMobileMenu();
    expect(component.mobileMenuOpen()).toBe(false);
  });

  it('should identify active router links correctly', () => {
    expect(component.isLinkActive('/', true)).toBe(true);
    expect(component.isLinkActive('#capabilities')).toBe(false);
    expect(component.isLinkActive('/#capabilities')).toBe(false);
    expect(component.isLinkActive('/how-it-works')).toBe(false);
  });

  it('should initialize isScrolled synchronously from window.scrollY and update on scroll', () => {
    expect(component.isScrolled()).toBe(false);

    Object.defineProperty(window, 'scrollY', { value: 50, writable: true, configurable: true });
    const scrolledFixture = TestBed.createComponent(FloatingNavbarComponent);
    expect(scrolledFixture.componentInstance.isScrolled()).toBe(true);

    component.onWindowScroll();
    expect(component.isScrolled()).toBe(true);

    Object.defineProperty(window, 'scrollY', { value: 10, writable: true, configurable: true });
    component.onWindowScroll();
    expect(component.isScrolled()).toBe(false);
  });
});
