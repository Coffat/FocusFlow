import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Component, signal } from '@angular/core';
import {
  AiInsightBannerComponent,
  AiInsightBannerType,
} from './ai-insight-banner.component';

@Component({
  standalone: true,
  imports: [AiInsightBannerComponent],
  template: `
    <app-ai-insight-banner
      [type]="type()"
      [title]="title()"
      [message]="message()"
      [complianceBadge]="complianceBadge()"
      [recommendations]="recommendations()"
      [actionLabel]="actionLabel()"
      (actionClick)="onAction()"
    />
  `,
})
class TestHostComponent {
  type = signal<AiInsightBannerType>('insight');
  title = signal<string>('Phân tích Nhận thức');
  message = signal<string>('Hiệu suất học buổi sáng tăng cao');
  complianceBadge = signal<string | undefined>('SRL Zimmerman');
  recommendations = signal<string[] | undefined>(['Chuyển task khó vào 8h - 10h']);
  actionLabel = signal<string | undefined>('Tối ưu hóa lịch');

  clicked = signal<boolean>(false);
  onAction(): void {
    this.clicked.set(true);
  }
}

describe('AiInsightBannerComponent', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let host: TestHostComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công AiInsightBannerComponent dạng insight', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Focus AI Cognitive Insight');
    expect(el.textContent).toContain('Phân tích Nhận thức');
    expect(el.textContent).toContain('SRL Zimmerman');
    expect(el.textContent).toContain('Chuyển task khó vào 8h - 10h');
  });

  it('hiển thị chính xác dạng domino_shift với tone hổ phách (amber)', () => {
    host.type.set('domino_shift');
    host.title.set('Điều phối Thích ứng: Domino Shift');
    host.message.set('3 task đã tự động dịch chuyển hạn chót');
    host.complianceBadge.set('3 task');
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Điều phối Thích ứng: Domino Shift');
    expect(el.textContent).toContain('3 task đã tự động dịch chuyển');
    expect(el.querySelector('.bg-amber-50\\/80')).toBeTruthy();
  });

  it('hiển thị dạng congratulation', () => {
    host.type.set('congratulation');
    host.title.set('Xuất sắc! Bạn đã hoàn thành mục tiêu');
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Xuất sắc! Bạn đã hoàn thành mục tiêu');
    expect(el.querySelector('.bg-emerald-50\\/80')).toBeTruthy();
  });

  it('phát sự kiện actionClick khi nhấn nút hành động', () => {
    const btn = fixture.nativeElement.querySelector('button');
    btn?.click();
    expect(host.clicked()).toBe(true);
  });
});
