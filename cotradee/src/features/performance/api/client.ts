import { api } from '@/lib/axios';
import type {
  PerformanceReviewGenerateResponse,
  PerformanceReviewHistoryPage,
  PerformanceReviewPeriod,
  PerformanceReviewRecord,
} from '../types';

/**
 * Thin wrappers over the gateway's /api/v1/performance-review surface.
 *
 * Cookie authentication, CSRF token stamping, and silent 401 refresh
 * are inherited from the shared axios instance in @/lib/axios. The
 * only translation we do here is mapping the gateway's history
 * payload (already shaped server-side) into the SPA's typed shape.
 */

const BASE = '/api/v1/performance-review';

export async function getLatestReview(
  period: PerformanceReviewPeriod,
): Promise<PerformanceReviewRecord> {
  const params = new URLSearchParams({ period });
  const { data } = await api.gateway.get<PerformanceReviewRecord>(
    `${BASE}/latest?${params.toString()}`,
  );
  return data;
}

export async function getReviewById(
  id: number,
): Promise<PerformanceReviewRecord> {
  const { data } = await api.gateway.get<PerformanceReviewRecord>(
    `${BASE}/${encodeURIComponent(String(id))}`,
  );
  return data;
}

export async function listReviewHistory(
  period?: PerformanceReviewPeriod,
  offset = 0,
  limit = 20,
): Promise<PerformanceReviewHistoryPage> {
  const params = new URLSearchParams();
  if (period) params.set('period', period);
  params.set('offset', String(offset));
  params.set('limit', String(limit));
  const { data } = await api.gateway.get<PerformanceReviewHistoryPage>(
    `${BASE}/history?${params.toString()}`,
  );
  return data;
}

export async function generateReview(
  period: PerformanceReviewPeriod,
): Promise<PerformanceReviewGenerateResponse> {
  const { data } = await api.gateway.post<PerformanceReviewGenerateResponse>(
    `${BASE}/generate`,
    { period },
  );
  return data;
}
