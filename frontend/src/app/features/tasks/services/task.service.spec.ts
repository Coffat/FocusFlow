import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TaskService } from './task.service';
import { TaskResponse } from '../models/task.model';
import { EntityInvalidationService } from '../../../core/services/entity-invalidation.service';
import { WorkspaceSessionService } from '../../../core/services/workspace-session.service';

const makeTask = (overrides: Partial<TaskResponse> = {}): TaskResponse => ({
  id: 'task-1',
  roadmap_id: 'rm-1',
  milestone_id: 'ms-1',
  title: 'Học FastAPI Async',
  description: 'Xây dựng router và dependency injection',
  estimated_minutes: 45,
  learning_resources: [],
  scheduled_date: '2026-11-18',
  status: 'TODO',
  reschedule_count: 0,
  is_overdue: false,
  is_blocked: false,
  is_stalled: false,
  predecessor_ids: [],
  created_at: '2026-11-18T00:00:00Z',
  updated_at: '2026-11-18T00:00:00Z',
  ...overrides,
});

describe('TaskService', () => {
  let service: TaskService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [TaskService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(TaskService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('loadTasks() và loadBacklogTasks() gọi API với withCredentials: true', () => {
    const task = makeTask();
    const backlog = makeTask({ id: 'task-2', scheduled_date: null, priority_rank: 1 });

    service.loadTasks('rm-1').subscribe();
    const listReq = httpMock.expectOne('/api/v1/tasks?roadmap_id=rm-1');
    expect(listReq.request.method).toBe('GET');
    expect(listReq.request.withCredentials).toBe(true);
    listReq.flush([task]);

    service.loadBacklogTasks().subscribe();
    const backlogReq = httpMock.expectOne('/api/v1/tasks/backlog');
    expect(backlogReq.request.method).toBe('GET');
    expect(backlogReq.request.withCredentials).toBe(true);
    backlogReq.flush([backlog]);

    expect(service.tasks()).toHaveLength(1);
    expect(service.backlogTasks()).toHaveLength(1);
  });

  it('createTask(), completeTask(), reopenTask(), rescheduleTask(), deleteTask() cập nhật state chuẩn xác', () => {
    const created = makeTask({ id: 'task-new', scheduled_date: null });
    service
      .createTask({
        roadmap_id: 'rm-1',
        milestone_id: 'ms-1',
        title: 'Học FastAPI Async',
        estimated_minutes: 45,
        confirm_soft_overflow: false,
      })
      .subscribe();
    const createReq = httpMock.expectOne('/api/v1/tasks');
    expect(createReq.request.method).toBe('POST');
    expect(createReq.request.withCredentials).toBe(true);
    createReq.flush(created);
    expect(service.tasks()[0].id).toBe('task-new');
    expect(service.backlogTasks()[0].id).toBe('task-new');

    const completed = { ...created, status: 'COMPLETED' };
    service.completeTask('task-new', { takeaway: null, self_confidence: 4 }).subscribe();
    const compReq = httpMock.expectOne('/api/v1/tasks/task-new/complete');
    expect(compReq.request.method).toBe('POST');
    compReq.flush(completed);
    expect(service.tasks()[0].status).toBe('COMPLETED');
    expect(service.backlogTasks()).toHaveLength(0);

    const reopened = { ...created, status: 'TODO' };
    service.reopenTask('task-new').subscribe();
    const reopenReq = httpMock.expectOne('/api/v1/tasks/task-new/reopen');
    expect(reopenReq.request.method).toBe('POST');
    reopenReq.flush(reopened);
    expect(service.tasks()[0].status).toBe('TODO');

    const rescheduled = { ...reopened, scheduled_date: '2026-11-20', reschedule_count: 1 };
    service
      .rescheduleTask('task-new', {
        scheduled_date: '2026-11-20',
        allow_stalled_commitment: false,
        confirm_soft_overflow: false,
      })
      .subscribe();
    const reschedReq = httpMock.expectOne('/api/v1/tasks/task-new/reschedule');
    expect(reschedReq.request.method).toBe('POST');
    reschedReq.flush(rescheduled);
    expect(service.tasks()[0].scheduled_date).toBe('2026-11-20');

    const cancelled = { ...rescheduled, status: 'CANCELLED' };
    service.deleteTask('task-new').subscribe();
    const delReq = httpMock.expectOne('/api/v1/tasks/task-new');
    expect(delReq.request.method).toBe('DELETE');
    delReq.flush(cancelled);
    expect(service.tasks()[0].status).toBe('CANCELLED');
  });

  it('bỏ qua phản hồi loadTasks() cũ đến sau khi đổi bộ lọc nhanh (stale-response protection)', () => {
    const staleTask = makeTask({ id: 'task-stale', title: 'Filter cũ' });
    const freshTask = makeTask({ id: 'task-fresh', title: 'Filter mới' });

    service.loadTasks('rm-old').subscribe();
    service.loadTasks('rm-new').subscribe();

    const oldReq = httpMock.expectOne('/api/v1/tasks?roadmap_id=rm-old');
    const newReq = httpMock.expectOne('/api/v1/tasks?roadmap_id=rm-new');

    newReq.flush([freshTask]);
    expect(service.tasks()).toEqual([freshTask]);

    oldReq.flush([staleTask]);
    expect(service.tasks()).toEqual([freshTask]);
  });

  it('tự động đồng bộ TaskService.tasks và backlogTasks khi hoàn thành task từ WorkspaceSessionService', () => {
    const invalidation = TestBed.inject(EntityInvalidationService);
    const workspaceService = TestBed.inject(WorkspaceSessionService);
    invalidation.resetForTests();

    const initialTask = makeTask({ id: 'task-sync-1', status: 'TODO', scheduled_date: null });
    service.tasks.set([initialTask]);
    service.backlogTasks.set([initialTask]);

    workspaceService.toggleTaskCompletion(initialTask).subscribe();
    const req = httpMock.expectOne('/api/v1/tasks/task-sync-1/complete');
    req.flush({ ...initialTask, status: 'COMPLETED', completed_at: '2026-11-21T08:00:00Z' });

    TestBed.tick();

    expect(service.tasks()[0].status).toBe('COMPLETED');
    expect(service.backlogTasks()).toHaveLength(0);
    expect(invalidation.versionFor('tasks')()).toBe(1);
    expect(invalidation.versionFor('schedule')()).toBe(1);
    expect(invalidation.versionFor('dashboard')()).toBe(1);
    expect(invalidation.versionFor('analytics')()).toBe(1);
  });
});
