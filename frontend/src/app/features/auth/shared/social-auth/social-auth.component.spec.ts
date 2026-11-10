import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SocialAuthComponent } from './social-auth.component';

describe('SocialAuthComponent', () => {
  let component: SocialAuthComponent;
  let fixture: ComponentFixture<SocialAuthComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SocialAuthComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(SocialAuthComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create component', () => {
    expect(component).toBeTruthy();
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
});
