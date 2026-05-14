import { useMemo } from 'react';
import { useActiveBrokerConnection } from '@/features/broker/api/brokerConnections';
import { useActiveLlmConnection } from '@/features/llm/api/llmConnections';
import { useSymbols } from '@/features/symbols/api/symbols';
import { useTradingSystemStatus } from '../api/hooks';

/**
 * Per-step completion signals used by both the OnboardingChecklist
 * card and any dashboard chrome that needs to know whether the user
 * is still onboarding (e.g. the floating Resume Setup pill).
 *
 * Single source of truth: the rules for "is this step done?" live
 * here so the card and the pill cannot drift. Any future analytics
 * surface (admin dashboards, funnel reports) reads the same hook.
 */
export interface OnboardingStepFlags {
  broker: boolean;
  symbols: boolean;
  tradingSystem: boolean;
  llm: boolean;
  billing: boolean;
  execution: boolean;
  ready: boolean;
}

export interface OnboardingProgress {
  perStep: OnboardingStepFlags;
  /** Number of completed steps including the synthetic 'ready' step. */
  completed: number;
  /** Total number of steps in the checklist (currently 7). */
  total: number;
  /** Convenience: every functional pre-req is satisfied. */
  ready: boolean;
  /** True while any underlying probe is still loading on first mount. */
  loading: boolean;
}

export const ONBOARDING_TOTAL_STEPS = 7;

/**
 * useOnboardingProgress aggregates the four live-state probes that
 * back the seven-step onboarding checklist. Cheap to call from
 * anywhere because each probe is a React Query hook that is already
 * mounted by other dashboard surfaces.
 */
export function useOnboardingProgress(): OnboardingProgress {
  const broker = useActiveBrokerConnection();
  const llm = useActiveLlmConnection();
  const symbols = useSymbols();
  const tradingSystem = useTradingSystemStatus();

  return useMemo<OnboardingProgress>(() => {
    const perStep: OnboardingStepFlags = {
      broker: !!broker.data,
      symbols: (symbols.data?.symbols?.length ?? 0) > 0,
      tradingSystem: tradingSystem.data?.status === 'active',
      llm: !!llm.data,
      billing: false, // placeholder until billing exposes a status hook
      // Execution mode is implied by an active trading system
      // (Section 11 of the builder is mandatory).
      execution: tradingSystem.data?.status === 'active',
      ready: false, // computed below
    };
    perStep.ready =
      perStep.broker && perStep.symbols && perStep.tradingSystem && perStep.llm;

    const completed =
      (perStep.broker ? 1 : 0) +
      (perStep.symbols ? 1 : 0) +
      (perStep.tradingSystem ? 1 : 0) +
      (perStep.billing ? 1 : 0) +
      (perStep.llm ? 1 : 0) +
      (perStep.execution ? 1 : 0) +
      (perStep.ready ? 1 : 0);

    return {
      perStep,
      completed,
      total: ONBOARDING_TOTAL_STEPS,
      ready: perStep.ready,
      loading:
        broker.isLoading ||
        symbols.isLoading ||
        tradingSystem.isLoading ||
        llm.isLoading,
    };
  }, [broker, llm, symbols, tradingSystem]);
}
