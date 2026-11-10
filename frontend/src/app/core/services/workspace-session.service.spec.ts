import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { WorkspaceSessionService } from './workspace-session.service';

describe('WorkspaceSessionService (Angular 21 Signals & Timer Reactivity)', () => {
  let service: WorkspaceSessionService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        WorkspaceSessionService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(WorkspaceSessionService);
  });

  afterEach(() => {
    service.pauseSession();
  });

  it('khởi tạo với các giá trị mặc định chính xác cho Signal và Computed', () => {
    expect(service.sessionId()).toBeNull();
    expect(service.taskId()).toBeNull();
    expect(service.mode()).toBe('pomodoro');
    expect(service.durationMinutes()).toBe(25);
    expect(service.remainingSeconds()).toBe(1500);
    expect(service.isRunning()).toBe(false);
    expect(service.scratchpadNote()).toBe('');
    expect(service.formattedTime()).toBe('25:00');
    expect(service.progressPercentage()).toBe(0);
  });

  it('setScratchpadNote() cập nhật signal scratchpadNote phản ứng tức thì', () => {
    service.setScratchpadNote('Ghi chú ôn tập kiến trúc Hexagonal');
    expect(service.scratchpadNote()).toBe('Ghi chú ôn tập kiến trúc Hexagonal');

    service.setScratchpadNote('Cần lưu ý: Outbox pattern xử lý sự kiện bất đồng bộ');
    expect(service.scratchpadNote()).toBe('Cần lưu ý: Outbox pattern xử lý sự kiện bất đồng bộ');
  });

  it('startSession() cập nhật trạng thái session, đặt thời gian và kích hoạt isRunning = true', () => {
    service.startSession('session-101', 'task-202', 30);

    expect(service.sessionId()).toBe('session-101');
    expect(service.taskId()).toBe('task-202');
    expect(service.durationMinutes()).toBe(30);
    expect(service.remainingSeconds()).toBe(1800);
    expect(service.isRunning()).toBe(true);
    expect(service.formattedTime()).toBe('30:00');
    expect(service.progressPercentage()).toBe(0);
  });

  it('pauseSession() và resumeSession() chuyển đổi trạng thái isRunning chính xác', () => {
    service.startSession('session-101', 'task-202', 25);
    expect(service.isRunning()).toBe(true);

    service.pauseSession();
    expect(service.isRunning()).toBe(false);

    service.resumeSession();
    expect(service.isRunning()).toBe(true);
  });

  it('formattedTime computed signal định dạng chính xác mm:ss cho nhiều mốc thời gian', () => {
    service.remainingSeconds.set(1500);
    expect(service.formattedTime()).toBe('25:00');

    service.remainingSeconds.set(754);
    expect(service.formattedTime()).toBe('12:34');

    service.remainingSeconds.set(9);
    expect(service.formattedTime()).toBe('00:09');

    service.remainingSeconds.set(0);
    expect(service.formattedTime()).toBe('00:00');
  });

  it('progressPercentage computed signal tính toán chính xác tỷ lệ hoàn thành', () => {
    service.durationMinutes.set(20); // total 1200 seconds

    // 0% elapsed
    service.remainingSeconds.set(1200);
    expect(service.progressPercentage()).toBe(0);

    // 50% elapsed (600s left)
    service.remainingSeconds.set(600);
    expect(service.progressPercentage()).toBe(50);

    // 75% elapsed (300s left)
    service.remainingSeconds.set(300);
    expect(service.progressPercentage()).toBe(75);

    // 100% elapsed (0s left)
    service.remainingSeconds.set(0);
    expect(service.progressPercentage()).toBe(100);
  });
});
