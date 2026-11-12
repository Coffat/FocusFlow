import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Component, signal } from '@angular/core';
import {
  RoadmapCardComponent,
  RoadmapCardInput,
  RoadmapCardVariant,
} from './roadmap-card.component';

@Component({
  standalone: true,
  imports: [RoadmapCardComponent],
  template: `
    <app-roadmap-card
      [roadmap]="roadmap()"
      [variant]="variant()"
      (pause)="onPause($event)"
      (resume)="onResume($event)"
      (archive)="onArchive($event)"
    />
  `,
})
class TestHostComponent {
  roadmap = signal<RoadmapCardInput>({
    id: 'rm-101',
    title: 'Mastering FastAPI Clean Architecture',
    description: 'Chinh phục Ports & Adapters và Asyncpg.',
    status: 'ACTIVE',
    target_date: '2026-12-31',
    tags: ['Backend', 'Python'],
  });
  variant = signal<RoadmapCardVariant>('full');

  pausedId = signal<string | null>(null);
  resumedId = signal<string | null>(null);
  archivedId = signal<string | null>(null);

  onPause(id: string): void {
    this.pausedId.set(id);
  }

  onResume(id: string): void {
    this.resumedId.set(id);
  }

  onArchive(id: string): void {
    this.archivedId.set(id);
  }
}

describe('RoadmapCardComponent', () => {
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

  it('khởi tạo thành công RoadmapCardComponent ở dạng full', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.roadmap-card-full')).toBeTruthy();
    expect(el.textContent).toContain('Mastering FastAPI Clean Architecture');
    expect(el.textContent).toContain('ĐANG KÍCH HOẠT');
    expect(el.textContent).toContain('Tiếp tục học');
  });

  it('hiển thị chính xác thẻ lộ trình ở dạng compact', () => {
    host.variant.set('compact');
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.roadmap-card-compact')).toBeTruthy();
    expect(el.querySelector('.roadmap-card-full')).toBeFalsy();
    expect(el.textContent).toContain('Chi tiết →');
  });

  it('hiển thị đúng huy hiệu khi lộ trình ở trạng thái PAUSED', () => {
    host.roadmap.set({
      id: 'rm-102',
      title: 'AWS SAA Cloud Certification',
      status: 'PAUSED',
      tags: ['Cloud', 'AWS'],
    });
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('TẠM DỪNG (DOMINO SHIFT)');
    expect(el.textContent).toContain('Kích hoạt lại lộ trình');
    expect(el.textContent).toContain('Lịch học tạm đóng băng');
  });

  it('mở menu 3 chấm và phát sự kiện pause khi chọn Tạm dừng', () => {
    const cardInstance = fixture.debugElement.children[0].componentInstance as RoadmapCardComponent;
    cardInstance.toggleMenu(new MouseEvent('click'));
    fixture.detectChanges();

    expect(cardInstance.showMenu()).toBe(true);
    cardInstance.onPause();
    expect(host.pausedId()).toBe('rm-101');
  });

  it('phát sự kiện archive khi chọn Lưu trữ', () => {
    const cardInstance = fixture.debugElement.children[0].componentInstance as RoadmapCardComponent;
    cardInstance.onArchive();
    expect(host.archivedId()).toBe('rm-101');
  });
});
