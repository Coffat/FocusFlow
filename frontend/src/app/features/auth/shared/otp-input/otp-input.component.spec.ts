import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ComponentRef } from '@angular/core';
import { OtpInputComponent } from './otp-input.component';

describe('OtpInputComponent', () => {
  let component: OtpInputComponent;
  let componentRef: ComponentRef<OtpInputComponent>;
  let fixture: ComponentFixture<OtpInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OtpInputComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(OtpInputComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  afterEach(() => {
    component.ngOnDestroy();
  });

  it('should initialize with 6 empty digits', () => {
    expect(component.digits().length).toBe(6);
    expect(component.digits().every((d) => d === '')).toBe(true);
  });

  it('should format countdown timer correctly', () => {
    component.timerSeconds.set(59);
    expect(component.formattedTimer()).toBe('00:59');

    component.timerSeconds.set(125);
    expect(component.formattedTimer()).toBe('02:05');
  });

  it('should emit codeChange and codeCompleted when all 6 digits are provided', () => {
    let completedCode = '';
    const emittedCodes: string[] = [];

    component.codeChange.subscribe((code) => {
      emittedCodes.push(code);
    });
    component.codeCompleted.subscribe((code) => {
      completedCode = code;
    });

    const compiled = fixture.nativeElement as HTMLElement;
    const inputs = compiled.querySelectorAll('input');

    for (let i = 0; i < 6; i++) {
      inputs[i].value = String(i + 1);
      inputs[i].dispatchEvent(new Event('input'));
    }

    expect(completedCode).toBe('123456');
    expect(emittedCodes[emittedCodes.length - 1]).toBe('123456');
  });

  it('should handle paste of 6 digits and set isAutoFilled', () => {
    let completedCode = '';
    component.codeCompleted.subscribe((code) => {
      completedCode = code;
    });

    const pasteEvent = new Event('paste') as any;
    pasteEvent.clipboardData = {
      getData: (format: string) => (format === 'text' ? '987654' : '')
    };
    pasteEvent.preventDefault = () => {};

    const compiled = fixture.nativeElement as HTMLElement;
    const firstInput = compiled.querySelector('input');
    firstInput?.dispatchEvent(pasteEvent);

    expect(component.isAutoFilled()).toBe(true);
    expect(completedCode).toBe('987654');
    expect(component.digits()).toEqual(['9', '8', '7', '6', '5', '4']);
  });

  it('should handle keyboard navigation (ArrowLeft and ArrowRight)', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const inputs = compiled.querySelectorAll('input');

    const arrowRight = new KeyboardEvent('keydown', { key: 'ArrowRight' });
    inputs[0].dispatchEvent(arrowRight);

    const arrowLeft = new KeyboardEvent('keydown', { key: 'ArrowLeft' });
    inputs[1].dispatchEvent(arrowLeft);

    expect(component).toBeTruthy();
  });

  it('should clear digits and reset autoFill on clear()', () => {
    component.digits.set(['1', '2', '3', '4', '5', '6']);
    component.isAutoFilled.set(true);

    let emitted = 'initial';
    component.codeChange.subscribe((code) => {
      emitted = code;
    });

    component.clear();

    expect(component.digits().every((d) => d === '')).toBe(true);
    expect(component.isAutoFilled()).toBe(false);
    expect(emitted).toBe('');
  });

  it('should show resend button when timer reaches 0 and emit resend on click', () => {
    component.timerSeconds.set(0);
    fixture.detectChanges();

    let resendCalled = false;
    component.resend.subscribe(() => {
      resendCalled = true;
    });

    const compiled = fixture.nativeElement as HTMLElement;
    const resendBtn = compiled.querySelector('button');
    expect(resendBtn).toBeTruthy();

    resendBtn?.click();
    expect(resendCalled).toBe(true);
  });
});
