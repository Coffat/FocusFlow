import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, catchError, finalize, of, tap, throwError } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { parseHttpErrorMessage } from '../../../core/utils/error-parser.util';
import {
  AnalyticsSummaryResponse,
  AnalyticsWeeklyResponse,
  GenerateWeeklyReviewRequestDTO,
  RoadmapResponse,
  WeeklyReviewResponseDTO,
} from '../models/analytics.model';

export interface AnalyticsApiError {
  code: string | null;
  status: number;
  message: string;
  isOffline: boolean;
}

export function getLocalMondayDate(offsetWeeks = 0): string {
  const now = new Date();
  const day = now.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + diffToMonday + offsetWeeks * 7
  );
  const y = monday.getFullYear();
  const m = String(monday.getMonth() + 1).padStart(2, '0');
  const d = String(monday.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function parseAnalyticsApiError(
  err: unknown,
  fallback = 'Không thể tải dữ liệu phân tích.'
): AnalyticsApiError {
  if (err instanceof HttpErrorResponse) {
    const body =
      err.error && typeof err.error === 'object' ? (err.error as Record<string, unknown>) : null;
    const code = body && typeof body['code'] === 'string' ? body['code'] : null;
    return {
      code,
      status: err.status,
      message: parseHttpErrorMessage(err, fallback),
      isOffline: err.status === 0,
    };
  }
  return { code: null, status: 0, message: fallback, isOffline: false };
}

@Injectable({
  providedIn: 'root',
})
export class AnalyticsService {
  private readonly http = inject(HttpClient);

  readonly summary = signal<AnalyticsSummaryResponse | null>(null);
  readonly weekly = signal<AnalyticsWeeklyResponse | null>(null);
  readonly latestReview = signal<WeeklyReviewResponseDTO | null>(null);
  readonly roadmaps = signal<RoadmapResponse[]>([]);
  readonly weekOffset = signal<number>(0);

  readonly isLoading = signal<boolean>(false);
  readonly isWeeklyLoading = signal<boolean>(false);
  readonly isGeneratingReview = signal<boolean>(false);
  readonly errorState = signal<AnalyticsApiError | null>(null);
  readonly reviewError = signal<AnalyticsApiError | null>(null);

  clearError(): void {
    this.errorState.set(null);
  }

  clearReviewError(): void {
    this.reviewError.set(null);
  }

  loadSummary(): Observable<AnalyticsSummaryResponse | null> {
    this.isLoading.set(true);
    this.errorState.set(null);

    return this.http
      .get<AnalyticsSummaryResponse>(API_ENDPOINTS.ANALYTICS.SUMMARY, {
        withCredentials: true,
      })
      .pipe(
        tap((res) => {
          this.summary.set(res);
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseAnalyticsApiError(err, 'Không thể tải tổng quan phân tích.'));
          return of(null);
        }),
        finalize(() => {
          this.isLoading.set(false);
        })
      );
  }

  loadWeekly(weekStart?: string | null): Observable<AnalyticsWeeklyResponse | null> {
    this.isWeeklyLoading.set(true);
    let params = new HttpParams();
    if (weekStart) {
      params = params.set('week_start', weekStart);
    }

    return this.http
      .get<AnalyticsWeeklyResponse>(API_ENDPOINTS.ANALYTICS.WEEKLY, {
        params,
        withCredentials: true,
      })
      .pipe(
        tap((res) => {
          this.weekly.set(res);
        }),
        catchError((err: unknown) => {
          this.errorState.set(parseAnalyticsApiError(err, 'Không thể tải phân tích theo tuần.'));
          return of(null);
        }),
        finalize(() => {
          this.isWeeklyLoading.set(false);
        })
      );
  }

  loadLatestWeeklyReview(): Observable<WeeklyReviewResponseDTO | null> {
    this.reviewError.set(null);

    return this.http
      .get<WeeklyReviewResponseDTO>(API_ENDPOINTS.EVALUATION.WEEKLY_REVIEWS_LATEST, {
        withCredentials: true,
      })
      .pipe(
        tap((res) => {
          this.latestReview.set(res);
        }),
        catchError((err: unknown) => {
          if (err instanceof HttpErrorResponse && err.status === 404) {
            this.latestReview.set(null);
            return of(null);
          }
          this.reviewError.set(
            parseAnalyticsApiError(err, 'Không thể tải bản đánh giá tuần gần nhất.')
          );
          return of(null);
        })
      );
  }

  loadRoadmaps(): Observable<RoadmapResponse[]> {
    return this.http
      .get<RoadmapResponse[]>(API_ENDPOINTS.ROADMAPS.BASE, { withCredentials: true })
      .pipe(
        tap((list) => {
          this.roadmaps.set(list);
        }),
        catchError(() => of([]))
      );
  }

  generateWeeklyReview(
    payload: GenerateWeeklyReviewRequestDTO
  ): Observable<WeeklyReviewResponseDTO> {
    this.isGeneratingReview.set(true);
    this.reviewError.set(null);

    return this.http
      .post<WeeklyReviewResponseDTO>(
        API_ENDPOINTS.EVALUATION.WEEKLY_REVIEWS_GENERATE,
        payload,
        { withCredentials: true }
      )
      .pipe(
        tap((review) => {
          this.latestReview.set(review);
        }),
        catchError((err: unknown) => {
          if (err instanceof HttpErrorResponse && err.status === 409) {
            this.reviewError.set({
              code: 'DUPLICATE_WEEKLY_REVIEW',
              status: 409,
              message:
                'Đánh giá tuần cho lộ trình và khoảng thời gian này đã được tạo trước đó.',
              isOffline: false,
            });
          } else {
            this.reviewError.set(
              parseAnalyticsApiError(err, 'Không thể tạo đánh giá tuần lúc này.')
            );
          }
          return throwError(() => err);
        }),
        finalize(() => {
          this.isGeneratingReview.set(false);
        })
      );
  }
}
