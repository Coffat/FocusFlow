import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, signal } from '@angular/core';
import { KpiCardComponent, KpiTone, KpiTrend } from './kpi-card.component';

@Component({
  standalone: true,
  imports: [KpiCardComponent],
  template: `
    <app-kpi-card
      [label]="label()"
      [value]="value()"
      [target]="target()"
      [delta]="delta()"
      [trend]="trend()"
      [tone]="tone()"
      [progress]="progress()"
      [subtitle]="subtitle()"
      [footerText]="footerText()"
      [icon]="icon()"
    />
  `,
})
class TestHostComponent {
  label = signal<string>('Tổng giờ tháng');
  value = signal<string | number>(42);
  target = signal<string | number>('60h');
  delta = signal<string | number>('+12%');
  trend = signal<KpiTrend>('up');
  tone = signal<KpiTone>('moss');
  progress = signal<number | undefined>(70);
  subtitle = signal<string | undefined>('70% mục tiêu');
  footerText = signal<string | undefined>('Cam kết 12h/tuần');
  icon = signal<string | undefined>('schedule');
}

describe('KpiCardComponent', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let host: TestHostComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công KpiCardComponent', () => {
    expect(fixture.nativeElement.querySelector('.kpi-card')).toBeTruthy();
  });

  it('hiển thị nhãn, giá trị và target chính xác', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Tổng giờ tháng');
    expect(el.textContent).toContain('42');
    expect(el.textContent).toContain('/ 60h');
  });

  it('hiển thị delta badge với biểu tượng xu hướng trend up', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('+12%');
    expect(el.textContent).toContain('trending_up');
  });

  it('hiển thị thanh tiến độ khi có input progress', () => {
    const bar = fixture.nativeElement.querySelector('.h-full.rounded-full');
    expect(bar).toBeTruthy();
    expect(bar.style.width).toBe('70%');
  });

  it('đổi màu sắc theo tone amber', () => {
    host.tone.set('amber');
    fixture.detectChanges();
    const iconContainer = fixture.nativeElement.querySelector('.w-7.h-7');
    expect(iconContainer.className).toContain('text-amber-600');
  });
});
