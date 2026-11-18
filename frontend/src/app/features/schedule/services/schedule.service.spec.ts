import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ScheduleService } from './schedule.service';
import { WeeklyScheduleResponse } from '../models/schedule.model';

describe('ScheduleService', () => {
  let service: ScheduleService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ScheduleService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ScheduleService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('loadWeeklySchedule() gọi GET /api/v1/tasks/schedule/week và nhóm các block theo ngày địa phương', () => {
    const mockRes: WeeklyScheduleResponse = {
      week_start: '2026-11-16',
      week_end: '2026-11-22',
      items: [
        {
          block_id: 'blk-1',
          roadmap_id: 'rm-1',
          roadmap_title: 'Python Backend',
          roadmap_status: 'ACTIVE',
          official_schedule_id: 'os-1',
          task_id: 'tsk-1',
          sequence_in_task: 1,
          block_type: 'STUDY',
          block_date: '2026-11-18',
          start_time: '2026-11-18T12:00:00Z',
          end_time: '2026-11-18T13:00:00Z',
          scheduled_duration_minutes: 60,
          block_status: 'SCHEDULED',
          sync_status: 'SYNCED',
          is_protected: false,
          task: {
            id: 'tsk-1',
            roadmap_id: 'rm-1',
            milestone_id: 'ms-1',
            title: 'Học SQLAlchemy Async',
            estimated_minutes: 60,
            status: 'TODO',
            reschedule_count: 0,
            is_overdue: false,
            is_blocked: false,
            is_stalled: false,
            created_at: '2026-11-18T00:00:00Z',
            updated_at: '2026-11-18T00:00:00Z',
          },
        },
      ],
    };

    service.loadWeeklySchedule('2026-11-16').subscribe();

    const req = httpMock.expectOne('/api/v1/tasks/schedule/week?week_start=2026-11-16');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush(mockRes);

    expect(service.items()).toHaveLength(1);
    expect(service.dayGroups()).toHaveLength(1);
    expect(service.dayGroups()[0].items[0].task?.title).toBe('Học SQLAlchemy Async');
  });

  it('moveTasksToBacklog() gọi POST /api/v1/tasks/{id}/reschedule với scheduled_date = null', () => {
    service.moveTasksToBacklog(['tsk-1'], 'Bận họp').subscribe();

    const req = httpMock.expectOne('/api/v1/tasks/tsk-1/reschedule');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body.scheduled_date).toBeNull();
    expect(req.request.body.reason).toBe('Bận họp');
    req.flush({
      id: 'tsk-1',
      roadmap_id: 'rm-1',
      milestone_id: 'ms-1',
      title: 'T1',
      estimated_minutes: 30,
      status: 'TODO',
      reschedule_count: 1,
      is_overdue: false,
      is_blocked: false,
      is_stalled: false,
      created_at: '2026-11-18T00:00:00Z',
      updated_at: '2026-11-18T00:00:00Z',
    });
  });
});
