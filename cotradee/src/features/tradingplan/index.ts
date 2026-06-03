// Public barrel for the Trading Plan feature.
//
// Re-exports the wire types, API client functions, React Query hooks,
// and the Excel exporter so callers import from a single path:
//
//   import { useTradingPlan, downloadPlanAsExcel } from '@/features/tradingplan';
//
// The internal file layout (types/, api/, lib/, components/) stays a
// private implementation detail of the feature.

export * from './types';
export * from './api/hooks';
export {
  generateTradingPlan,
  getTradingPlan,
  getTradingPlanJournal,
  getTradingPlanStatus,
  resetTradingPlan,
  updateTradingPlan,
  upsertJournalAnnotation,
} from './api/client';
export { downloadPlanAsExcel, downloadJournalAsExcel } from './lib/excel';
