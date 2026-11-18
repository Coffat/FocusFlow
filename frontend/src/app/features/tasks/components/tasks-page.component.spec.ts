import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { TasksPageComponent } from './tasks-page.component';
import { TaskService } from '../services/task.service';
import { TaskResponse } from '../models/task.model';

const makeTask = (overrides: Partial<TaskResponse> = {}): TaskResponse => ({
  id: 'tsk-01',
  roadmap_id: 'rd-01',
  milestone_id: 'ms-01',
  title: 'Nhiệm vụ kiểm thử Vitest',
  description: 'Mô tả nhiệm vụ',
  estimated_minutes: 60,
  learning_resources: [{ title: 'Tài liệu Clean Arch', url: 'https://example.com' }],
  scheduled_date: '2026-11-18',
  status: 'IN_PROGRESS',
  reschedule_count: 0,
  is_overdue: false,
  is_blocked: false,
  is_stalled: false,
  predecessor_ids: [],
  roadmap_title: 'Kiến trúc phần mềm',
  created_at: '2026-11-18T00:00:00Z',
  updated_at: '2026-11-18T00:00:00Z',
  ...overrides,
});

describe('TasksPageComponent', () => {
  let component: TasksPageComponent;
  let fixture: ComponentFixture<TasksPageComponent>;
  let taskService: TaskService;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TasksPageComponent],
      providers: [TaskService, provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(TasksPageComponent);
    component = fixture.componentInstance;
    taskService = TestBed.inject(TaskService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function flushInitial(tasks: TaskResponse[] = [], backlog: TaskResponse[] = []) {
    fixture.detectChanges();
    httpMock.expectOne('/api/v1/tasks').flush(tasks);
    httpMock.expectOne('/api/v1/tasks/backlog').flush(backlog);
    httpMock.expectOne('/api/v1/roadmaps').flush([]);
    fixture.detectChanges();
  }

  it('khởi tạo thành công trang hàng đợi nhiệm vụ', () => {
    flushInitial();
    expect(component).toBeTruthy();
  });

  it('hiển thị empty state khi danh sách nhiệm vụ rỗng', () => {
    flushInitial();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Hàng đợi nhiệm vụ đang trống');
    expect(el.textContent).toContain('Xem Lộ trình học tập');
  });

  it('hiển thị danh sách nhiệm vụ, badge suy diễn OVERDUE/BLOCKED/STALLED và learning_resources', () => {
    const task = makeTask({
      is_overdue: true,
      is_blocked: true,
      is_stalled: true,
      reschedule_count: 3,
    });
    flushInitial([task]);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Nhiệm vụ kiểm thử Vitest');
    expect(el.textContent).toContain('Đang học');
    expect(el.textContent).toContain('60 phút');
    expect(el.textContent).toContain('Quá hạn');
    expect(el.textContent).toContain('Bị chặn');
    expect(el.textContent).toContain('Đình trệ (3 lần)');
    expect(el.textContent).toContain('Tài liệu Clean Arch');
  });

  it('chuyển tab Backlog hiển thị danh sách từ /api/v1/tasks/backlog', () => {
    const backlogTask = makeTask({
      id: 'tsk-bl',
      title: 'Nhiệm vụ Backlog ưu tiên cao',
      scheduled_date: null,
      status: 'TODO',
      priority_rank: 1,
    });
    flushInitial([], [backlogTask]);

    component.selectTab('BACKLOG');
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Nhiệm vụ Backlog ưu tiên cao');
    expect(el.textContent).toContain('Ưu tiên #1');
  });
});
