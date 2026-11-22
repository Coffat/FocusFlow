import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, finalize, of, share, tap } from 'rxjs';
import { components } from '../api/schema';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import { parseHttpErrorMessage } from '../utils/error-parser.util';
import { EntityInvalidationService } from '../services/entity-invalidation.service';

export type RoadmapResponse = components['schemas']['RoadmapResponse'];

export interface LoadRoadmapsOptions {
  force?: boolean;
  statusFilter?: string;
}

@Injectable({
  providedIn: 'root',
})
export class RoadmapStore {
  private readonly http = inject(HttpClient);
  private readonly entityInvalidation = inject(EntityInvalidationService);

  private readonly FRESHNESS_TTL_MS = 30_000;

  private readonly _roadmaps = signal<RoadmapResponse[]>([]);
  readonly roadmaps = this._roadmaps.asReadonly();

  private readonly _loading = signal<boolean>(false);
  readonly loading = this._loading.asReadonly();

  private readonly _error = signal<string | null>(null);
  readonly error = this._error.asReadonly();

  private hasLoaded = false;
  private lastFetchedAt = 0;
  private requestSeq = 0;
  private inFlight$: Observable<RoadmapResponse[]> | null = null;

  loadRoadmaps(options?: LoadRoadmapsOptions): Observable<RoadmapResponse[]> {
    const force = Boolean(options?.force);
    const statusFilter = options?.statusFilter?.trim() || undefined;
    const isFresh = this.hasLoaded && Date.now() - this.lastFetchedAt < this.FRESHNESS_TTL_MS;

    if (!force && !statusFilter) {
      if (isFresh) {
        return of(this._roadmaps());
      }
      if (this.inFlight$) {
        return this.inFlight$;
      }
    }

    const seq = ++this.requestSeq;
    this._loading.set(true);
    this._error.set(null);

    const url = statusFilter
      ? `${API_ENDPOINTS.ROADMAPS.BASE}?status=${encodeURIComponent(statusFilter)}`
      : API_ENDPOINTS.ROADMAPS.BASE;

    const request$ = this.http
      .get<RoadmapResponse[]>(url, { withCredentials: true })
      .pipe(
        tap((list) => {
          if (seq !== this.requestSeq) {
            return;
          }
          this._roadmaps.set(list);
          if (!statusFilter) {
            this.hasLoaded = true;
            this.lastFetchedAt = Date.now();
          }
        }),
        catchError((err: unknown) => {
          if (seq === this.requestSeq) {
            this._error.set(
              parseHttpErrorMessage(err, 'Không thể tải danh sách lộ trình học tập.')
            );
          }
          return of([] as RoadmapResponse[]);
        }),
        finalize(() => {
          if (this.inFlight$ === request$) {
            this.inFlight$ = null;
          }
          if (seq === this.requestSeq) {
            this._loading.set(false);
          }
        }),
        share()
      );

    if (!statusFilter) {
      this.inFlight$ = request$;
    }

    return request$;
  }

  upsertRoadmap(roadmap: RoadmapResponse): void {
    this._roadmaps.update((list) => {
      const exists = list.some((r) => r.id === roadmap.id);
      if (exists) {
        return list.map((r) => (r.id === roadmap.id ? roadmap : r));
      }
      return [roadmap, ...list];
    });
    this.hasLoaded = true;
    this.lastFetchedAt = Date.now();
  }

  setRoadmaps(list: RoadmapResponse[]): void {
    this._roadmaps.set(list);
    this.hasLoaded = true;
    this.lastFetchedAt = Date.now();
  }

  invalidate(): void {
    this.hasLoaded = false;
    this.lastFetchedAt = 0;
    this.inFlight$ = null;
    this.entityInvalidation.invalidate('roadmaps');
  }

  reset(): void {
    this._roadmaps.set([]);
    this._loading.set(false);
    this._error.set(null);
    this.hasLoaded = false;
    this.lastFetchedAt = 0;
    this.requestSeq = 0;
    this.inFlight$ = null;
  }
}
