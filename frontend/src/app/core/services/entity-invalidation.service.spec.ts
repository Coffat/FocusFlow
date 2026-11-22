import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { EntityInvalidationService, TaskResponse } from './entity-invalidation.service';

const makeTask = (overrides: Partial<TaskResponse> = {}): TaskResponse => ({
  id: 'task-1',
  roadmap_id: 'rm-1',
  milestone_id: 'ms-1',
  title: 'Học Angular Signals',
  estimated_minutes: 45,
  status: 'COMPLETED',
  reschedule_count: 0,
  is_overdue: false,
  is_blocked: false,
  is_stalled: false,
  created_at: '2026-11-21T00:00:00Z',
  updated_at: '2026-11-21T00:00:00Z',
  ...overrides,
});

describe('EntityInvalidationService', () => {
  let service: EntityInvalidationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [EntityInvalidationService],
    });
    service = TestBed.inject(EntityInvalidationService);
    service.resetForTests();
  });

  it('tăng version chính xác cho các domain được invalidate mà không ảnh hưởng domain khác', () => {
    expect(service.versionFor('tasks')()).toBe(0);
    expect(service.versionFor('dashboard')()).toBe(0);
    expect(service.versionFor('roadmaps')()).toBe(0);

    service.invalidate('tasks', 'dashboard', 'tasks');

    expect(service.versionFor('tasks')()).toBe(1);
    expect(service.versionFor('dashboard')()).toBe(1);
    expect(service.versionFor('roadmaps')()).toBe(0);
  });

  it('phát notifyTaskMutated và đặt lại sạch sẽ qua resetForTests()', () => {
    expect(service.lastTaskMutation()).toBeNull();

    const task = makeTask({ id: 'task-99', status: 'COMPLETED' });
    service.notifyTaskMutated(task);
    expect(service.lastTaskMutation()?.id).toBe('task-99');
    expect(service.lastTaskMutation()?.status).toBe('COMPLETED');

    service.resetForTests();
    expect(service.lastTaskMutation()).toBeNull();
    expect(service.versionFor('tasks')()).toBe(0);
  });
});
