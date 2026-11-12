import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TasksPageComponent } from './tasks-page.component';
import { TaskService } from '../services/task.service';

describe('TasksPageComponent', () => {
  let component: TasksPageComponent;
  let fixture: ComponentFixture<TasksPageComponent>;
  let taskService: TaskService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TasksPageComponent],
      providers: [TaskService, provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(TasksPageComponent);
    component = fixture.componentInstance;
    taskService = TestBed.inject(TaskService);
    fixture.detectChanges();
  });

  it('khởi tạo thành công trang hàng đợi nhiệm vụ', () => {
    expect(component).toBeTruthy();
  });

  it('hiển thị empty state khi danh sách nhiệm vụ rỗng (không dùng mock)', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Hàng đợi nhiệm vụ đang trống');
    expect(el.textContent).toContain('Xem Lộ trình học tập');
  });

  it('hiển thị danh sách nhiệm vụ khi có dữ liệu', () => {
    taskService.tasks.set([
      {
        id: 'tsk-01',
        roadmapId: 'rd-01',
        milestoneId: 'ms-01',
        title: 'Nhiệm vụ kiểm thử Vitest',
        description: 'Mô tả nhiệm vụ',
        pomodoroEstimate: 3,
        pomodorosCompleted: 1,
        priority: 'HIGH',
        status: 'IN_PROGRESS',
      },
    ]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Nhiệm vụ kiểm thử Vitest');
    expect(el.textContent).toContain('Đang học');
    expect(el.textContent).toContain('1 / 3 phiên');
  });
});
