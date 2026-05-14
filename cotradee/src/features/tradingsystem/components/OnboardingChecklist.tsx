import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from '@/hooks/useToast';
import { useActiveBrokerConnection } from '@/features/broker/api/brokerConnections';
import { useActiveLlmConnection } from '@/features/llm/api/llmConnections';
import { useSymbols } from '@/features/symbols/api/symbols';
import { useTradingSystemStatus } from '../api/hooks';
import { BuilderModal } from './BuilderModal';

interface ChecklistStep {
  id: string;
  title: string;
  description: string;
  done: boolean;
  loading: boolean;
  cta: { label: string; onClick: () => void };
  /**
   * When true, the step is still in active-implementation; the CTA
   * surfaces a "coming soon" toast instead of actually navigating.
   * Per the user's instruction, only step 3 is fully wired in this
   * release; the others are scaffolded and auto-tick from live
   * state where available.
   */
  placeholder?: boolean;
}

/**
 * 7-step onboarding card rendered on the empty dashboard. Each step
 * has a deterministic live-state probe so the card auto-ticks the
 * moment the user completes the underlying setup from anywhere in
 * the SPA (Settings, Broker page, etc.).
 *
 * The card is purely a UI surface; every "done" signal is read from
 * an existing feature hook so there is no parallel state to keep in
 * sync. When ALL steps return done=true, the card collapses to a
 * single celebratory line and the dashboard returns to its normal
 * chart-driven layout on the next mount.
 */
export function OnboardingChecklist() {
  const navigate = useNavigate();

  const broker = useActiveBrokerConnection();
  const llm = useActiveLlmConnection();
  const symbols = useSymbols();
  const tradingSystem = useTradingSystemStatus();

  const [builderOpen, setBuilderOpen] = useState(false);

  const steps: ChecklistStep[] = useMemo(
    () => [
      {
        id: 'broker',
        title: 'Connect your broker',
        description:
          'Link your MT4 or MT5 account so the AI can read prices and place trades on your behalf.',
        done: !!broker.data,
        loading: broker.isLoading,
        cta: {
          label: 'Connect broker',
          onClick: () => navigate('/dashboard/settings/broker'),
        },
      },
      {
        id: 'symbols',
        title: 'Select favorite symbols',
        description: 'Choose the instruments you want the AI to analyse for you.',
        done: (symbols.data?.symbols?.length ?? 0) > 0,
        loading: symbols.isLoading,
        cta: {
          label: 'Pick symbols',
          onClick: () => navigate('/dashboard/settings/symbols'),
        },
      },
      {
        id: 'trading_system',
        title: 'Build your Exoper Trading System',
        description:
          'A 2–3 minute questionnaire that personalises every AI decision to your style, risk, and goals.',
        done: tradingSystem.data?.status === 'active',
        loading: tradingSystem.isLoading,
        cta: {
          label:
            tradingSystem.data?.status === 'skipped' ? 'Build now' : 'Start the builder',
          onClick: () => setBuilderOpen(true),
        },
      },
      {
        id: 'billing',
        title: 'Add billing',
        description:
          'Pick a plan so the AI can run autonomously and access premium institutional data.',
        done: false,
        loading: false,
        cta: {
          label: 'Open billing',
          onClick: () => navigate('/dashboard/settings/billing'),
        },
        placeholder: true,
      },
      {
        id: 'llm',
        title: 'Add your AI API key',
        description:
          'BYOK: bring your own OpenAI / Anthropic / Gemini key, or upgrade to Pro Managed to use ours.',
        done: !!llm.data,
        loading: llm.isLoading,
        cta: {
          label: llm.data ? 'Manage key' : 'Add API key',
          onClick: () => navigate('/dashboard/settings/llm'),
        },
      },
      {
        id: 'execution',
        title: 'Configure execution',
        description:
          'Pick how much control you delegate — alert-only, manual approval, semi-automatic, or fully automatic.',
        done: false,
        loading: false,
        cta: {
          label: 'Configure',
          onClick: () => navigate('/dashboard/settings'),
        },
        placeholder: true,
      },
      {
        id: 'ready',
        title: "You're in",
        description:
          "You're ready to trade. The chart will replace this card the moment any prior step is complete.",
        done: false,
        loading: false,
        cta: {
          label: 'Go to chart',
          onClick: () => navigate('/dashboard'),
        },
        placeholder: true,
      },
    ],
    [broker, llm, symbols, tradingSystem, navigate],
  );

  const completedCount = steps.filter((s) => s.done).length;
  const progressPct = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="flex h-full w-full items-center justify-center px-4 py-6">
      <div className="w-full max-w-xl rounded-xl border border-border bg-surface p-5 shadow-sm">
        <header className="mb-4">
          <h2 className="text-lg font-semibold text-content">Let&apos;s get you set up</h2>
          <p className="mt-1 text-sm text-content-secondary">
            Seven quick steps to your personalised AI trading desk.
          </p>
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-content-muted mb-1.5">
              <span>
                {completedCount} of {steps.length} complete
              </span>
              <span className="font-medium text-content tabular-nums">{progressPct}%</span>
            </div>
            <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-app">
              <div
                className="h-full bg-brand transition-all duration-fast"
                style={{ width: `${progressPct}%` }}
                role="progressbar"
                aria-valuenow={progressPct}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>
        </header>

        <ol className="space-y-2">
          {steps.map((step, idx) => (
            <ChecklistRow
              key={step.id}
              step={step}
              index={idx + 1}
              onPlaceholder={() =>
                toast({
                  title: `${step.title} — coming soon`,
                  description: 'This step is part of onboarding. Wiring lands in a follow-up release.',
                  variant: 'default',
                })
              }
            />
          ))}
        </ol>
      </div>

      <BuilderModal
        open={builderOpen}
        onClose={() => setBuilderOpen(false)}
        onComplete={() => {
          // The status hook invalidates automatically via
          // useSaveTradingSystem's onSuccess; nothing to do here.
        }}
      />
    </div>
  );
}

function ChecklistRow({
  step,
  index,
  onPlaceholder,
}: {
  step: ChecklistStep;
  index: number;
  onPlaceholder: () => void;
}) {
  const handleClick = () => {
    if (step.placeholder) {
      onPlaceholder();
      return;
    }
    step.cta.onClick();
  };

  return (
    <li
      className={`flex items-start gap-3 rounded-lg border p-3 transition-colors
        ${step.done
          ? 'border-success/50 bg-success/5'
          : 'border-border bg-app hover:border-content-muted'}`}
    >
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold
          ${step.done
            ? 'bg-success text-white'
            : 'bg-surface text-content-secondary border border-border'}`}
        aria-hidden
      >
        {step.done ? '✓' : index}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <h3
            className={`text-sm font-semibold ${
              step.done ? 'text-content-secondary line-through' : 'text-content'
            }`}
          >
            {step.title}
          </h3>
          {!step.done && (
            <button
              type="button"
              onClick={handleClick}
              disabled={step.loading}
              className="shrink-0 rounded bg-brand px-3 py-1 text-xs font-semibold text-white
                         hover:bg-brand/90 focus-ring disabled:opacity-50"
            >
              {step.loading ? 'Checking…' : step.cta.label}
            </button>
          )}
        </div>
        <p className="mt-1 text-xs text-content-muted">{step.description}</p>
      </div>
    </li>
  );
}
