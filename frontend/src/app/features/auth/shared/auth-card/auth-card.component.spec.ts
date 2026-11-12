import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, signal } from '@angular/core';
import { AuthCardComponent } from './auth-card.component';

@Component({
  standalone: true,
  imports: [AuthCardComponent],
  template: `
    <app-auth-card [showLogo]="showLogo()" [cardClass]="cardClass()">
      <div id="projected-content">Sign in form content</div>
    </app-auth-card>
  `
})
class TestHostComponent {
  readonly showLogo = signal(true);
  readonly cardClass = signal('');
}

describe('AuthCardComponent', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let hostComponent: TestHostComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent, AuthCardComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    hostComponent = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and render projected content', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const projected = compiled.querySelector('#projected-content');
    expect(projected).toBeTruthy();
    expect(projected?.textContent).toContain('Sign in form content');
  });

  it('should render the FocusFlow logo by default', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const img = compiled.querySelector('img');
    expect(img).toBeTruthy();
    expect(img?.getAttribute('src')).toBe('assets/logo.svg');
    expect(img?.getAttribute('alt')).toBe('FocusFlow');
  });

  it('should hide the logo when showLogo is false', () => {
    hostComponent.showLogo.set(false);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const img = compiled.querySelector('img');
    expect(img).toBeNull();
  });

  it('should append custom cardClass to the inner container', () => {
    hostComponent.cardClass.set('custom-auth-card-class');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const innerCard = compiled.querySelector('.custom-auth-card-class');
    expect(innerCard).toBeTruthy();
  });
});
