import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ScrollRevealDirective } from './scroll-reveal.directive';

@Component({
  standalone: true,
  imports: [ScrollRevealDirective],
  template: `
    <div
      id="test-el"
      appScrollReveal
      [revealDelay]="delay"
      [revealDirection]="direction"
    >
      Test Content
    </div>
  `,
})
class TestHostComponent {
  delay = 150;
  direction: 'up' | 'down' | 'left' | 'right' | 'none' = 'up';
}

describe('ScrollRevealDirective', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let hostComponent: TestHostComponent;
  let observerInstances: Array<{
    callback: IntersectionObserverCallback;
    options?: IntersectionObserverInit;
    observe: ReturnType<typeof vi.fn>;
    unobserve: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
  }>;

  beforeEach(() => {
    observerInstances = [];

    // Mock IntersectionObserver
    class MockIntersectionObserver implements IntersectionObserver {
      readonly root: Element | Document | null = null;
      readonly rootMargin: string;
      readonly thresholds: ReadonlyArray<number>;

      observe = vi.fn();
      unobserve = vi.fn();
      disconnect = vi.fn();
      takeRecords = vi.fn().mockReturnValue([]);

      constructor(
        public callback: IntersectionObserverCallback,
        public options?: IntersectionObserverInit
      ) {
        this.rootMargin = options?.rootMargin ?? '0px';
        const th = options?.threshold ?? 0;
        this.thresholds = Array.isArray(th) ? th : [th];
        observerInstances.push(this);
      }
    }

    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

    // Default matchMedia mock (prefers-reduced-motion: false)
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('should initialize and observe target element with threshold 0.12 and negative rootMargin', () => {
    fixture = TestBed.createComponent(TestHostComponent);
    hostComponent = fixture.componentInstance;
    fixture.detectChanges();

    const el = fixture.nativeElement.querySelector('#test-el') as HTMLElement;
    expect(el).toBeTruthy();

    expect(observerInstances.length).toBe(1);
    const mockObs = observerInstances[0];
    expect(mockObs.options?.threshold).toBe(0.12);
    expect(mockObs.options?.rootMargin).toBe('0px 0px -30px 0px');
    expect(mockObs.observe).toHaveBeenCalledWith(el);

    // Initial styles applied
    expect(el.style.opacity).toBe('0');
    expect(el.style.transform).toBe('translateY(28px)');
    expect(el.style.transitionDelay).toBe('150ms');
  });

  it('should add "is-revealed" class and update styles when element intersects viewport', () => {
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const el = fixture.nativeElement.querySelector('#test-el') as HTMLElement;
    const mockObs = observerInstances[0];

    // Trigger intersection
    mockObs.callback(
      [
        {
          isIntersecting: true,
          target: el,
        } as unknown as IntersectionObserverEntry,
      ],
      mockObs as unknown as IntersectionObserver
    );

    expect(el.classList.contains('is-revealed')).toBe(true);
    expect(el.style.opacity).toBe('1');
    expect(el.style.transform).toMatch(/^translateY\(0(px)?\)$/);
    expect(mockObs.disconnect).toHaveBeenCalled();
  });

  it('should immediately reveal if prefers-reduced-motion is active', () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('prefers-reduced-motion: reduce'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const el = fixture.nativeElement.querySelector('#test-el') as HTMLElement;
    expect(el.classList.contains('is-revealed')).toBe(true);
    expect(el.style.opacity).toBe('1');
    expect(el.style.transform).toBe('none');
    expect(observerInstances.length).toBe(0);
  });

  it('should support left direction initial transform', () => {
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.direction = 'left';
    fixture.detectChanges();

    const el = fixture.nativeElement.querySelector('#test-el') as HTMLElement;
    expect(el.style.transform).toBe('translateX(28px)');
  });

  it('should disconnect observer on destroy', () => {
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const mockObs = observerInstances[0];
    fixture.destroy();

    expect(mockObs.disconnect).toHaveBeenCalled();
  });
});
