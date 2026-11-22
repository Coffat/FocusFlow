import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { RoadmapResponse, RoadmapStore } from './roadmap.store';
import { EntityInvalidationService } from '../services/entity-invalidation.service';

const makeRoadmap = (overrides: Partial<RoadmapResponse> = {}): RoadmapResponse => ({
  id: 'rm-1',
  user_id: 'usr-1',
  goal_id: 'goal-1',
  title: 'FastAPI & Hexagonal Architecture',
  description: 'Lộ trình backend',
  status: 'ACTIVE',
  start_date: '2026-11-01',
  target_date: '2026-12-31',
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
  ...overrides,
});

describe('RoadmapStore', () => {
  let store: RoadmapStore;
  let invalidation: EntityInvalidationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        RoadmapStore,
        EntityInvalidationService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    store = TestBed.inject(RoadmapStore);
    invalidation = TestBed.inject(EntityInvalidationService);
    httpMock = TestBed.inject(HttpTestingController);
    store.reset();
    invalidation.resetForTests();
  });

  afterEach(() => {
    vi.useRealTimers();
    httpMock.verify();
  });

  it('tải danh sách lộ trình với withCredentials: true và chống gọi trùng HTTP trong thời gian cache tươi (30s)', () => {
    const rm1 = makeRoadmap({ id: 'rm-1' });
    const receivedA: RoadmapResponse[][] = [];
    const receivedB: RoadmapResponse[][] = [];

    // Hai subscriber đồng thời dùng chung 1 request in-flight
    store.loadRoadmaps().subscribe((list) => receivedA.push(list));
    store.loadRoadmaps().subscribe((list) => receivedB.push(list));

    const req = httpMock.expectOne('/api/v1/roadmaps');
    expect(req.request.method).toBe('GET');
    expect(req.request.withCredentials).toBe(true);
    req.flush([rm1]);

    expect(store.roadmaps()).toEqual([rm1]);
    expect(receivedA).toEqual([[rm1]]);
    expect(receivedB).toEqual([[rm1]]);

    // Gọi tiếp trong vòng 30s không phát thêm HTTP request
    let cachedResult: RoadmapResponse[] = [];
    store.loadRoadmaps().subscribe((list) => {
      cachedResult = list;
    });
    httpMock.expectNone('/api/v1/roadmaps');
    expect(cachedResult).toEqual([rm1]);
  });

  it('force: true bỏ qua cache và tải mới từ server', () => {
    const rm1 = makeRoadmap({ id: 'rm-1', title: 'Bản cũ' });
    const rm1Updated = makeRoadmap({ id: 'rm-1', title: 'Bản mới' });

    store.setRoadmaps([rm1]);

    store.loadRoadmaps({ force: true }).subscribe();
    const req = httpMock.expectOne('/api/v1/roadmaps');
    expect(req.request.withCredentials).toBe(true);
    req.flush([rm1Updated]);

    expect(store.roadmaps()[0].title).toBe('Bản mới');
  });

  it('bỏ qua phản hồi HTTP cũ đến sau (out-of-order requestSeq protection)', () => {
    const staleList = [makeRoadmap({ id: 'rm-stale', title: 'Dữ liệu cũ' })];
    const freshList = [makeRoadmap({ id: 'rm-fresh', title: 'Dữ liệu mới nhất' })];

    store.loadRoadmaps({ force: true }).subscribe();
    store.loadRoadmaps({ force: true }).subscribe();

    const reqs = httpMock.match('/api/v1/roadmaps');
    expect(reqs).toHaveLength(2);

    // Request mới hoàn tất trước
    reqs[1].flush(freshList);
    expect(store.roadmaps()).toEqual(freshList);

    // Request cũ hoàn tất sau -> bị bỏ qua, không ghi đè state mới
    reqs[0].flush(staleList);
    expect(store.roadmaps()).toEqual(freshList);
  });

  it('upsertRoadmap cập nhật tại chỗ hoặc thêm lên đầu và invalidate() xóa freshness + tăng version roadmaps', () => {
    const rm1 = makeRoadmap({ id: 'rm-1', status: 'ACTIVE' });
    const rm2 = makeRoadmap({ id: 'rm-2', title: 'Angular 21', status: 'ACTIVE' });

    store.setRoadmaps([rm1]);
    store.upsertRoadmap(rm2);
    expect(store.roadmaps().map((r) => r.id)).toEqual(['rm-2', 'rm-1']);

    store.upsertRoadmap({ ...rm1, status: 'PAUSED' });
    expect(store.roadmaps().find((r) => r.id === 'rm-1')?.status).toBe('PAUSED');

    const prevVersion = invalidation.versionFor('roadmaps')();
    store.invalidate();
    expect(invalidation.versionFor('roadmaps')()).toBe(prevVersion + 1);

    // Sau invalidate(), loadRoadmaps() không dùng cache mà gọi HTTP lại
    store.loadRoadmaps().subscribe();
    const req = httpMock.expectOne('/api/v1/roadmaps');
    req.flush([rm2, { ...rm1, status: 'PAUSED' }]);
  });
});
