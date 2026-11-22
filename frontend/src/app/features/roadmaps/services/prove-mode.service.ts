import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import { HTTP_TIMEOUT_MS } from '../../../core/interceptors/timeout.interceptor';
import { EntityInvalidationService } from '../../../core/services/entity-invalidation.service';
import type { components } from '../../../core/api/schema';

export type GenerateProofResponseDTO = components['schemas']['GenerateProofResponseDTO'];
export type SubmitProofRequestDTO = components['schemas']['SubmitProofRequestDTO'];
export type MilestoneProofResponseDTO = components['schemas']['MilestoneProofResponseDTO'];
export type LatestMilestoneProofResponseDTO =
  components['schemas']['LatestMilestoneProofResponseDTO'];

export interface CachedMilestoneProof {
  readonly id: string;
  readonly milestone_id: string;
  readonly status: string;
  readonly score: number | null;
  readonly confidence: number | null;
  readonly corrective_action: string | null;
  readonly is_verified: boolean;
  readonly calibration_error: number | null;
}

@Injectable({
  providedIn: 'root',
})
export class ProveModeService {
  private readonly http = inject(HttpClient);
  private readonly entityInvalidation = inject(EntityInvalidationService);

  private readonly _proofByMilestone = signal<Record<string, CachedMilestoneProof>>({});
  readonly proofByMilestone = this._proofByMilestone.asReadonly();

  getLatestProof(milestoneId: string): Observable<LatestMilestoneProofResponseDTO | null> {
    return this.http
      .get<LatestMilestoneProofResponseDTO | null>(
        API_ENDPOINTS.EVALUATION.MILESTONE_PROOF_LATEST(milestoneId),
        { withCredentials: true }
      )
      .pipe(
        tap((latest) => {
          if (latest) {
            this.cacheProof(milestoneId, {
              id: latest.id,
              milestone_id: latest.milestone_id,
              status: latest.status,
              score: latest.score ?? null,
              confidence: latest.confidence ?? null,
              corrective_action: latest.corrective_action ?? null,
              is_verified: latest.is_verified,
              calibration_error: latest.calibration_error ?? null,
            });
          }
        })
      );
  }

  generateProof(milestoneId: string): Observable<GenerateProofResponseDTO> {
    return this.http.post<GenerateProofResponseDTO>(
      API_ENDPOINTS.EVALUATION.MILESTONE_PROOF_GENERATE(milestoneId),
      {},
      {
        withCredentials: true,
        context: new HttpContext().set(HTTP_TIMEOUT_MS, 35_000),
      }
    );
  }

  submitProof(
    milestoneId: string,
    proofId: string,
    payload: SubmitProofRequestDTO
  ): Observable<MilestoneProofResponseDTO> {
    return this.http
      .post<MilestoneProofResponseDTO>(
        API_ENDPOINTS.EVALUATION.MILESTONE_PROOF_SUBMIT(milestoneId, proofId),
        payload,
        {
          withCredentials: true,
          context: new HttpContext().set(HTTP_TIMEOUT_MS, 40_000),
        }
      )
      .pipe(
        tap((result) => {
          this.cacheProof(milestoneId, {
            id: result.id,
            milestone_id: result.milestone_id,
            status: result.status,
            score: result.score,
            confidence: result.confidence,
            corrective_action: result.corrective_action,
            is_verified: result.is_verified,
            calibration_error: result.calibration_error ?? null,
          });
          this.entityInvalidation.invalidate('roadmaps', 'dashboard', 'analytics');
        })
      );
  }

  private cacheProof(milestoneId: string, summary: CachedMilestoneProof): void {
    this._proofByMilestone.update((current) => ({
      ...current,
      [milestoneId]: summary,
    }));
  }
}
