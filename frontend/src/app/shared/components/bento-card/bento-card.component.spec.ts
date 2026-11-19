import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { BentoCardComponent } from './bento-card.component';

@Component({
  standalone: true,
  imports: [BentoCardComponent],
  template: `
    <app-bento-card
      [colSpan]="5"
      icon="timer"
      title="Pomodoro Zen"
      description="Deep work"
      category="Tập trung"
    >
      <div id="test-slot">Visual Slot Content</div>
    </app-bento-card>
  `,
})
class TestHostComponent {}

describe('BentoCardComponent', () => {
  let fixture: ComponentFixture<TestHostComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent, BentoCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
  });

  it('should render title, description, category, and projected slot content', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Pomodoro Zen');
    expect(el.textContent).toContain('Deep work');
    expect(el.textContent).toContain('Tập trung');
    expect(el.querySelector('#test-slot')?.textContent).toContain('Visual Slot Content');
  });

  it('should apply md:col-span-5 class based on colSpan input', () => {
    const cardEl = fixture.nativeElement.querySelector('app-bento-card') as HTMLElement;
    expect(cardEl.classList.contains('md:col-span-5')).toBe(true);
    expect(cardEl.classList.contains('hairline-card')).toBe(true);
  });
});
