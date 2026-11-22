import { describe, it, expect } from 'vitest';
import { API_ENDPOINTS } from './api-endpoints';

function collectEndpointPaths(obj: Record<string, unknown>): string[] {
  const paths: string[] = [];
  for (const value of Object.values(obj)) {
    if (typeof value === 'string') {
      paths.push(value);
    } else if (typeof value === 'function') {
      const sample = (value as (...args: string[]) => string)('id-1', 'id-2');
      if (typeof sample === 'string') {
        paths.push(sample);
      }
    } else if (value && typeof value === 'object') {
      paths.push(...collectEndpointPaths(value as Record<string, unknown>));
    }
  }
  return paths;
}

describe('API_ENDPOINTS (FE-API-01/02 OpenAPI 3.1 Contract)', () => {
  it('khớp các đường dẫn chuẩn OpenAPI 3.1 cho SETTINGS, EVALUATION và ROADMAPS.PROPOSAL_APPLY', () => {
    expect(API_ENDPOINTS.SETTINGS.PROFILE).toBe('/api/v1/account/profile');
    expect(API_ENDPOINTS.SETTINGS.QUOTA).toBe('/api/v1/account/quota');
    expect(API_ENDPOINTS.EVALUATION.DASHBOARD_SUMMARY).toBe('/api/v1/evaluation/dashboard-summary');
    expect(API_ENDPOINTS.ROADMAPS.PROPOSAL_APPLY('rm-1', 'prop-1')).toBe(
      '/api/v1/roadmaps/rm-1/proposals/prop-1/apply'
    );
    expect(API_ENDPOINTS.ROADMAPS.JOB_STREAM('job-1')).toBe('/api/v1/roadmaps/jobs/job-1/stream');
  });

  it('không còn bất kỳ đường dẫn legacy /api/v1/users/* nào trong API_ENDPOINTS', () => {
    const allPaths = collectEndpointPaths(API_ENDPOINTS as unknown as Record<string, unknown>);
    const legacyUsersPaths = allPaths.filter((p) => p.includes('/api/v1/users/'));
    expect(legacyUsersPaths).toEqual([]);
  });

  it('đã loại bỏ các ghost entries không tồn tại trong OpenAPI (BILLING, ADMIN, ROADMAPS legacy)', () => {
    const endpointsRecord = API_ENDPOINTS as unknown as Record<string, unknown>;
    expect(endpointsRecord['BILLING']).toBeUndefined();
    expect(endpointsRecord['ADMIN']).toBeUndefined();

    const roadmapsRecord = API_ENDPOINTS.ROADMAPS as unknown as Record<string, unknown>;
    expect(roadmapsRecord['GENERATE_JOB']).toBeUndefined();
    expect(roadmapsRecord['ACTIVE']).toBeUndefined();
    expect(roadmapsRecord['APPLY']).toBeUndefined();
    expect(roadmapsRecord['STREAM_JOB']).toBeUndefined();
  });
});
