import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ButtonDirective, ButtonSize, ButtonVariant } from './button.directive';
import { By } from '@angular/platform-browser';

@Component({
  standalone: true,
  imports: [ButtonDirective],
  template: `
    <button
      appButton
      [variant]="variant()"
      [size]="size()"
      [class]="customClass()"
    >
      Action Button
    </button>
  `
})
class TestHostComponent {
  readonly variant = signal<ButtonVariant>('default');
  readonly size = signal<ButtonSize>('default');
  readonly customClass = signal<string>('');
}

describe('ButtonDirective (Angular 21 Signals input() & computed() classes)', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let hostComponent: TestHostComponent;
  let buttonEl: HTMLButtonElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    hostComponent = fixture.componentInstance;
    fixture.detectChanges();

    buttonEl = fixture.debugElement.query(By.directive(ButtonDirective)).nativeElement;
  });

  it('áp dụng các class mặc định (variant=default, size=default, base classes)', () => {
    expect(buttonEl.className).toContain('inline-flex');
    expect(buttonEl.className).toContain('items-center');
    expect(buttonEl.className).toContain('bg-[var(--primary)]');
    expect(buttonEl.className).toContain('h-9');
    expect(buttonEl.className).toContain('px-4');
  });

  it('phản ứng động khi thay đổi input signal variant sang destructive, secondary, outline', () => {
    // Switch to destructive
    hostComponent.variant.set('destructive');
    fixture.detectChanges();
    expect(buttonEl.className).toContain('bg-[var(--destructive)]');
    expect(buttonEl.className).not.toContain('bg-[var(--primary)]');

    // Switch to secondary
    hostComponent.variant.set('secondary');
    fixture.detectChanges();
    expect(buttonEl.className).toContain('bg-[var(--secondary)]');

    // Switch to outline
    hostComponent.variant.set('outline');
    fixture.detectChanges();
    expect(buttonEl.className).toContain('bg-transparent');
  });

  it('phản ứng động khi thay đổi input signal size sang sm, lg, icon', () => {
    // Switch to sm
    hostComponent.size.set('sm');
    fixture.detectChanges();
    expect(buttonEl.className).toContain('h-8');
    expect(buttonEl.className).toContain('text-xs');

    // Switch to lg
    hostComponent.size.set('lg');
    fixture.detectChanges();
    expect(buttonEl.className).toContain('h-10');
    expect(buttonEl.className).toContain('text-base');

    // Switch to icon
    hostComponent.size.set('icon');
    fixture.detectChanges();
    expect(buttonEl.className).toContain('h-9');
    expect(buttonEl.className).toContain('w-9');
  });

  it('kết hợp mượt mà class người dùng truyền vào (customClass/userClass alias) qua cn() tailwind-merge', () => {
    hostComponent.customClass.set('custom-shadow-class mt-6 w-full');
    fixture.detectChanges();

    expect(buttonEl.className).toContain('custom-shadow-class');
    expect(buttonEl.className).toContain('mt-6');
    expect(buttonEl.className).toContain('w-full');
  });
});
