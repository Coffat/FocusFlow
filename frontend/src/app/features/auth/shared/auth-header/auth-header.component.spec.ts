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

  it('should render icon when provided', () => {
    componentRef.setInput('icon', 'verified_user');
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.material-symbols-outlined')?.textContent).toContain('verified_user');
  });
});
