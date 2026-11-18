import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SkeletonLoaderComponent } from './skeleton-loader.component';

describe('SkeletonLoaderComponent', () => {
  let component: SkeletonLoaderComponent;
  let fixture: ComponentFixture<SkeletonLoaderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SkeletonLoaderComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SkeletonLoaderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create with default card variant and accessible aria attributes', () => {
    expect(component).toBeTruthy();
    expect(component.variant()).toBe('card');
    const el = fixture.nativeElement as HTMLElement;
    const statusEl = el.querySelector('[role="status"]');
    expect(statusEl).toBeTruthy();
    expect(statusEl?.getAttribute('aria-busy')).toBe('true');
  });

  it('should render bento variant grid', () => {
    fixture.componentRef.setInput('variant', 'bento');
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.md\\:col-span-7')).toBeTruthy();
    expect(el.querySelector('.md\\:col-span-5')).toBeTruthy();
  });

  it('should render timeline variant', () => {
    fixture.componentRef.setInput('variant', 'timeline');
    fixture.componentRef.setInput('count', 3);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const items = el.querySelectorAll('.min-h-\\[170px\\]');
    expect(items.length).toBe(3);
  });

  it('should render text variant', () => {
    fixture.componentRef.setInput('variant', 'text');
    fixture.componentRef.setInput('count', 4);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const items = el.querySelectorAll('.space-y-2\\.5 .skeleton-shimmer');
    expect(items.length).toBe(4);
  });
});
