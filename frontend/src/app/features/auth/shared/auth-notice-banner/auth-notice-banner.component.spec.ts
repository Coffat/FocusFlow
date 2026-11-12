import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, signal } from '@angular/core';
import { AuthNoticeBannerComponent } from './auth-notice-banner.component';

@Component({
  standalone: true,
  imports: [AuthNoticeBannerComponent],
  template: `
    <app-auth-notice-banner
      [type]="type()"
      [message]="message()"
      [title]="title()"
    >
      <span id="extra-banner-content">Additional details</span>
    </app-auth-notice-banner>
  `
})
class TestHostComponent {
  readonly type = signal<'error' | 'info' | 'success' | 'session-lock'>('info');
  readonly message = signal('');
  readonly title = signal('');
}

describe('AuthNoticeBannerComponent', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let hostComponent: TestHostComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent, AuthNoticeBannerComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    hostComponent = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should not render banner container when message and title are empty', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.leading-relaxed')).toBeNull();
  });

  it('should render error banner with role="alert", error icon, and message', () => {
    hostComponent.type.set('error');
    hostComponent.message.set('Invalid credentials provided.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const banner = compiled.querySelector('[role="alert"]');
    expect(banner).toBeTruthy();
    expect(banner?.textContent).toContain('Invalid credentials provided.');

    const icon = compiled.querySelector('.material-symbols-outlined');
    expect(icon?.textContent?.trim()).toBe('error');
    expect(icon?.classList.contains('text-[#ba1a1a]')).toBe(true);
  });

  it('should render info banner with info icon and role="status"', () => {
    hostComponent.type.set('info');
    hostComponent.message.set('Verification code dispatched to your inbox.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const banner = compiled.querySelector('[role="status"]');
    expect(banner).toBeTruthy();
    expect(banner?.textContent).toContain('Verification code dispatched to your inbox.');

    const icon = compiled.querySelector('.material-symbols-outlined');
    expect(icon?.textContent?.trim()).toBe('info');
  });

  it('should render success banner with check_circle icon and green theme', () => {
    hostComponent.type.set('success');
    hostComponent.message.set('Password reset instructions sent.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const banner = compiled.querySelector('[role="status"]');
    expect(banner).toBeTruthy();
    expect(banner?.textContent).toContain('Password reset instructions sent.');

    const icon = compiled.querySelector('.material-symbols-outlined');
    expect(icon?.textContent?.trim()).toBe('check_circle');
    expect(icon?.classList.contains('text-[#005234]')).toBe(true);
  });

  it('should render session-lock banner with shield icon and inline title', () => {
    hostComponent.type.set('session-lock');
    hostComponent.title.set('CRYPTOGRAPHIC SESSION LOCK');
    hostComponent.message.set('Active auth challenges expire after 10 minutes.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const banner = compiled.querySelector('[role="status"]');
    expect(banner).toBeTruthy();
    expect(banner?.textContent).toContain('CRYPTOGRAPHIC SESSION LOCK:');
    expect(banner?.textContent).toContain('Active auth challenges expire after 10 minutes.');

    const icon = compiled.querySelector('.material-symbols-outlined');
    expect(icon?.textContent?.trim()).toBe('shield');
    expect(icon?.classList.contains('text-primary')).toBe(true);
  });

  it('should render title and projected content for general notice', () => {
    hostComponent.type.set('info');
    hostComponent.title.set('Notice Header');
    hostComponent.message.set('Main message body.');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Notice Header');
    expect(compiled.textContent).toContain('Main message body.');
    expect(compiled.querySelector('#extra-banner-content')?.textContent).toBe('Additional details');
  });
});
