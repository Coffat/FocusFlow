import { ComponentFixture, TestBed } from '@angular/core/testing';
import { OtpInputComponent } from './otp-input.component';

describe('OtpInputComponent', () => {
  let component: OtpInputComponent;
  let fixture: ComponentFixture<OtpInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OtpInputComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(OtpInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    component.ngOnDestroy();
  });

  it('should initialize with 6 empty digits', () => {
    expect(component.digits().length).toBe(6);
    expect(component.digits().every(d => d === '')).toBe(true);
  });

  it('should format countdown timer correctly', () => {
    component.timerSeconds.set(59);
    expect(component.formattedTimer()).toBe('00:59');

    component.timerSeconds.set(125);
    expect(component.formattedTimer()).toBe('02:05');
  });

  it('should emit codeCompleted when all 6 digits are provided', () => {
    let completedCode = '';
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
  });
});
