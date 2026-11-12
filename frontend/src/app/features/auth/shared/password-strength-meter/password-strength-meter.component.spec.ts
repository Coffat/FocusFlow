import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ComponentRef } from '@angular/core';
import { PasswordStrengthMeterComponent } from './password-strength-meter.component';

describe('PasswordStrengthMeterComponent', () => {
  let component: PasswordStrengthMeterComponent;
  let componentRef: ComponentRef<PasswordStrengthMeterComponent>;
  let fixture: ComponentFixture<PasswordStrengthMeterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PasswordStrengthMeterComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(PasswordStrengthMeterComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('should create and render default security label', () => {
    expect(component).toBeTruthy();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Mức độ bảo mật');
  });

  it('should render custom security label and strength text', () => {
    componentRef.setInput('securityLabel', 'Security Level');
    componentRef.setInput('strengthText', 'Rất mạnh');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Security Level');
    expect(compiled.textContent).toContain('Rất mạnh');
  });

  it('should render 4 strength indicator bars', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const bars = compiled.querySelectorAll('.rounded-full.h-full');
    expect(bars.length).toBe(4);
  });

  it('should reflect strength = 0 with no active bars', () => {
    componentRef.setInput('strength', 0);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const activeBars = compiled.querySelectorAll('.bg-primary');
    expect(activeBars.length).toBe(0);
  });

  it('should reflect strength = 2 with 2 active bars and 2 inactive bars', () => {
    componentRef.setInput('strength', 2);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const activeBars = compiled.querySelectorAll('.bg-primary');
    const inactiveBars = compiled.querySelectorAll('.bg-neutral-200');
    expect(activeBars.length).toBe(2);
    expect(inactiveBars.length).toBe(2);
  });

  it('should reflect strength = 4 with all 4 active bars', () => {
    componentRef.setInput('strength', 4);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const activeBars = compiled.querySelectorAll('.bg-primary');
    expect(activeBars.length).toBe(4);
  });
});
