import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { AuthFormFieldComponent } from './auth-form-field.component';

@Component({
  standalone: true,
  imports: [AuthFormFieldComponent],
  template: `
    <app-auth-form-field
      [label]="label()"
      [forId]="forId()"
      [hint]="hint()"
      [linkText]="linkText()"
      [linkRoute]="linkRoute()"
      [prefixIcon]="prefixIcon()"
      [suffixIcon]="suffixIcon()"
      [suffixAriaLabel]="suffixAriaLabel()"
      [showSuffix]="showSuffix()"
      [errorMessage]="errorMessage()"
      (suffixClick)="onSuffixClick()"
    >
      <input id="test-input" type="text" />
    </app-auth-form-field>
  `
})
class TestHostComponent {
  readonly label = signal('Email Address');
  readonly forId = signal('test-input');
  readonly hint = signal('');
  readonly linkText = signal('');
  readonly linkRoute = signal('');
  readonly prefixIcon = signal('');
  readonly suffixIcon = signal('');
  readonly suffixAriaLabel = signal('');
  readonly showSuffix = signal(false);
  readonly errorMessage = signal('');

  suffixClicked = false;
  onSuffixClick() {
    this.suffixClicked = true;
  }
}

describe('AuthFormFieldComponent', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let hostComponent: TestHostComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent, AuthFormFieldComponent],
      providers: [provideRouter([])]
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    hostComponent = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should render label associated with input id', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const label = compiled.querySelector('label');
    expect(label?.textContent?.trim()).toBe('Email Address');
    expect(label?.getAttribute('for')).toBe('test-input');
  });

  it('should project the input element', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const input = compiled.querySelector('#test-input');
    expect(input).toBeTruthy();
  });

  it('should render hint when provided and no link is set', () => {
    hostComponent.hint.set('Institutional preferred');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Institutional preferred');
  });

  it('should render link instead of hint when linkText and linkRoute are provided', () => {
    hostComponent.hint.set('Institutional preferred');
    hostComponent.linkText.set('Forgot Password?');
    hostComponent.linkRoute.set('/forgot-password');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const link = compiled.querySelector('a');
    expect(link).toBeTruthy();
    expect(link?.textContent?.trim()).toBe('Forgot Password?');
    expect(link?.getAttribute('href')).toBe('/forgot-password');
  });

  it('should render prefix icon when provided', () => {
    hostComponent.prefixIcon.set('alternate_email');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const icon = compiled.querySelector('.pointer-events-none .material-symbols-outlined');
    expect(icon?.textContent?.trim()).toBe('alternate_email');
  });

  it('should render suffix icon button and emit suffixClick on click', () => {
    hostComponent.suffixIcon.set('visibility');
    hostComponent.suffixAriaLabel.set('Toggle password visibility');
    hostComponent.showSuffix.set(true);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const button = compiled.querySelector('button');
    expect(button).toBeTruthy();
    expect(button?.getAttribute('aria-label')).toBe('Toggle password visibility');
    expect(button?.querySelector('.material-symbols-outlined')?.textContent?.trim()).toBe('visibility');

    button?.click();
    expect(hostComponent.suffixClicked).toBe(true);
  });

  it('should render error message with role="alert" when provided', () => {
    hostComponent.errorMessage.set('Email is invalid');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const error = compiled.querySelector('[role="alert"]');
    expect(error).toBeTruthy();
    expect(error?.textContent?.trim()).toBe('Email is invalid');
  });
});
