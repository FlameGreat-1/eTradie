import { useMemo } from 'react';
import { useActiveBrokerConnection } from '@/features/broker/api/brokerConnections';
import { useActiveLlmConnection } from '@/features/llm/api/llmConnections';
import { useSymbols } from '@/features/symbols/api/symbols';
import { useTradingSystemStatus } from '../api/hooks';

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
  completed: number;
  total: number;
  ready: boolean;
  loading: boolean;
}

export const ONBOARDING_TOTAL_STEPS = 8;

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
      billing: false,
      execution: tradingSystem.data?.status === 'active',
      ready: false,
    };
    perStep.ready =
      perStep.broker && perStep.symbols && perStep.tradingSystem && perStep.llm;

    const completed =
      (perStep.broker ? 2 : 0) +
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
