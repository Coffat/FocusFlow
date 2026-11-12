import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Component, signal } from '@angular/core';
import { ScheduleBlockDetailDialogComponent } from './schedule-block-detail-dialog.component';
import { DashboardScheduleBlock } from '../models/dashboard.model';

@Component({
  standalone: true,
  imports: [ScheduleBlockDetailDialogComponent],
  template: `
    <app-schedule-block-detail-dialog
      [open]="open()"
      [block]="block()"
      (closeDialog)="onClose()"
      (startSession)="onStart($event)"
    />
  `,
})
class TestHostComponent {
  open = signal<boolean>(false);
  block = signal<DashboardScheduleBlock | null>(null);

  closed = signal<boolean>(false);
  startedBlock = signal<DashboardScheduleBlock | null>(null);

  onClose(): void {
    this.closed.set(true);
  }

  onStart(b: DashboardScheduleBlock): void {
    this.startedBlock.set(b);
  }
}

describe('ScheduleBlockDetailDialogComponent', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let host: TestHostComponent;

  const mockBlock: DashboardScheduleBlock = {
    id: 'block-1',
    title: 'Full IELTS Mock Test & Error Log Review',
    type: 'live',
    dayOfWeek: 6,
    dayLabel: 'Thứ Bảy',
    startTime: '08:30',
    endTime: '11:30',
    code: 'RD-IELTS-75',
    durationMinutes: 180,
    pomodoroCount: 6,
    description: 'Luyện đề 4 kỹ năng & phân tích nhật ký lỗi sai chi tiết',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestHostComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('không hiển thị khi open là false', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[role="dialog"]')).toBeNull();
  });

  it('hiển thị đầy đủ thông tin ca học khi open là true', () => {
    host.block.set(mockBlock);
    host.open.set(true);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[role="dialog"]')).toBeTruthy();
    expect(el.textContent).toContain('Full IELTS Mock Test & Error Log Review');
    expect(el.textContent).toContain('08:30 – 11:30');
    expect(el.textContent).toContain('180 phút');
    expect(el.textContent).toContain('Đang diễn ra');
    expect(el.textContent).toContain('RD-IELTS-75');
    expect(el.textContent).toContain('6 phiên');
    expect(el.textContent).toContain('Luyện đề 4 kỹ năng & phân tích nhật ký lỗi sai chi tiết');
  });

  it('phát sự kiện closeDialog khi bấm nút Đóng hoặc nút X', () => {
    host.block.set(mockBlock);
    host.open.set(true);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const closeBtn = el.querySelector('button[aria-label="Đóng"]') as HTMLButtonElement;
    expect(closeBtn).toBeTruthy();
    closeBtn.click();
    fixture.detectChanges();

    expect(host.closed()).toBe(true);
  });

  it('phát sự kiện startSession khi bấm nút Vào phòng học ngay', () => {
    host.block.set(mockBlock);
    host.open.set(true);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const startBtn = Array.from(el.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('Vào phòng học ngay')
    );
    expect(startBtn).toBeTruthy();
    startBtn!.click();
    fixture.detectChanges();

    expect(host.startedBlock()?.id).toBe('block-1');
  });
});
