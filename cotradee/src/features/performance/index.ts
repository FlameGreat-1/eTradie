// Public barrel for the Performance Review feature.
//
// Re-exports the wire types, API client functions, React Query hooks,
// and the user-facing components so callers import from a single path:
//
//   import { usePerformanceReviewLatest, PerformanceReviewView }
//     from '@/features/performance';
//
// The internal file layout (types/, api/, components/) stays a private
// implementation detail of the feature module.

export * from './types';
export {
  getLatestReview,
  getReviewById,
  listReviewHistory,
  generateReview,
} from './api/client';
export {
  usePerformanceReviewLatest,
  usePerformanceReviewById,
  usePerformanceReviewHistory,
  useGeneratePerformanceReview,
  performanceReviewKeys,
} from './api/hooks';
