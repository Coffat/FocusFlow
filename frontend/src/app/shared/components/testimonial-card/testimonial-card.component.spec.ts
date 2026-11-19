import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TestimonialCardComponent } from './testimonial-card.component';

describe('TestimonialCardComponent', () => {
  let component: TestimonialCardComponent;
  let fixture: ComponentFixture<TestimonialCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestimonialCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TestimonialCardComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('quote', 'Một công cụ định hình tư duy xuất sắc.');
    fixture.componentRef.setInput('authorName', 'Minh Huy');
    fixture.componentRef.setInput('authorRole', 'Cloud Solutions Architect');
    fixture.componentRef.setInput('avatarInitials', 'MH');
    fixture.detectChanges();
  });

  it('should render testimonial quote, author details, and initials', () => {
    expect(component).toBeTruthy();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Một công cụ định hình tư duy xuất sắc.');
    expect(el.textContent).toContain('Minh Huy');
    expect(el.textContent).toContain('Cloud Solutions Architect');
    expect(el.textContent).toContain('MH');
  });

  it('should apply custom badgeColor', () => {
    fixture.componentRef.setInput('badgeColor', 'bg-tertiary-fixed text-on-tertiary-fixed');
    fixture.detectChanges();
    const avatar = fixture.nativeElement.querySelector('.w-9.h-9') as HTMLElement;
    expect(avatar.classList.contains('bg-tertiary-fixed')).toBe(true);
  });
});
