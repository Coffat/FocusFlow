import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AuthHeaderComponent } from './auth-header.component';
import { ComponentRef } from '@angular/core';

describe('AuthHeaderComponent', () => {
  let component: AuthHeaderComponent;
  let componentRef: ComponentRef<AuthHeaderComponent>;
  let fixture: ComponentFixture<AuthHeaderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuthHeaderComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AuthHeaderComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    componentRef.setInput('title', 'Welcome back');
    fixture.detectChanges();
  });

  it('should create and render the title', () => {
    expect(component).toBeTruthy();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Welcome back');
  });

  it('should render subtitle when provided', () => {
    componentRef.setInput('subtitle', 'Enter credentials');
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('p')?.textContent).toContain('Enter credentials');
  });

  it('should render inline icon by default when icon is provided', () => {
    componentRef.setInput('icon', 'verified_user');
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const iconSpan = compiled.querySelector('.material-symbols-outlined');
    expect(iconSpan?.textContent).toContain('verified_user');
    expect(iconSpan?.classList.contains('text-primary')).toBe(true);
  });

  it('should render circle badge icon when iconStyle is "circle"', () => {
    componentRef.setInput('icon', 'lock_reset');
    componentRef.setInput('iconStyle', 'circle');
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const circleContainer = compiled.querySelector('.rounded-full.w-11.h-11');
    expect(circleContainer).toBeTruthy();
    expect(circleContainer?.textContent).toContain('lock_reset');
  });

  it('should toggle logo visibility based on showLogo input', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('img')).toBeTruthy();

    componentRef.setInput('showLogo', false);
    fixture.detectChanges();
    expect(compiled.querySelector('img')).toBeNull();
  });
});
