import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ComponentRef } from '@angular/core';
import { SocialAuthComponent } from './social-auth.component';

describe('SocialAuthComponent', () => {
  let component: SocialAuthComponent;
  let componentRef: ComponentRef<SocialAuthComponent>;
  let fixture: ComponentFixture<SocialAuthComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SocialAuthComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(SocialAuthComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('should create component', () => {
    expect(component).toBeTruthy();
  });

  it('should render default button text and divider text', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('button')?.textContent).toContain('Google');
    expect(compiled.textContent).toContain('or continue with email');
  });

  it('should render custom button text and divider text when provided', () => {
    componentRef.setInput('googleButtonText', 'Continue with Google');
    componentRef.setInput('dividerText', 'hoặc đăng nhập với email');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('button')?.textContent).toContain('Continue with Google');
    expect(compiled.textContent).toContain('hoặc đăng nhập với email');
  });

  it('should emit googleClick event when Google button is clicked', () => {
    let clicked = false;
    component.googleClick.subscribe(() => {
      clicked = true;
    });

    const compiled = fixture.nativeElement as HTMLElement;
    const button = compiled.querySelector('button');
    button?.click();

    expect(clicked).toBe(true);
  });

  it('should disable button when disabled input is true', () => {
    let clicked = false;
    component.googleClick.subscribe(() => {
      clicked = true;
    });

    componentRef.setInput('disabled', true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const button = compiled.querySelector('button');
    expect(button?.disabled).toBe(true);

    button?.click();
    expect(clicked).toBe(false);
  });
});
