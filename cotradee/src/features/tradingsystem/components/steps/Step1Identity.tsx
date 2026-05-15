import type { Identity } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: Identity;
  onChange: (next: Identity) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step1Identity({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  const set = <K extends keyof Identity>(key: K, v: Identity[K]) => onChange({ ...value, [key]: v });
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Trading Identity"
      description="Define who you are operationally. These answers shape how Exoper prioritises setups for you."
    >
      <div className="space-y-8">
      <div>
        <div className="text-[10px] text-black/30 dark:text-white/30 uppercase font-bold tracking-[0.15em] mb-3">1. Experience level</div>
        <RadioCardGroup
          name="experience"
          value={value.experience}
          onChange={(v) => set('experience', v)}
          options={[
            { value: 'beginner', label: 'Beginner', description: 'Learning the ropes' },
            { value: 'intermediate', label: 'Intermediate', description: 'Trading consistently' },
            { value: 'advanced', label: 'Advanced', description: 'Years of screen time' },
          ]}
        />
        <FieldError message={errors['identity.experience']} />
      </div>

      <div>
        <div className="text-[10px] text-black/30 dark:text-white/30 uppercase font-bold tracking-[0.15em] mb-3">2. Execution preference</div>
        <RadioCardGroup
          name="automation"
          value={value.automation}
          onChange={(v) => set('automation', v)}
          options={[
            { value: 'manual', label: 'Manual', description: 'I execute every trade myself' },
            { value: 'semi_automated', label: 'Semi-Automated', description: 'Exoper assists, I confirm' },
            { value: 'fully_automated', label: 'Fully Automated', description: 'Exoper executes for me' },
          ]}
        />
        <FieldError message={errors['identity.automation']} />
      </div>

      <div>
        <div className="text-[10px] text-black/30 dark:text-white/30 uppercase font-bold tracking-[0.15em] mb-3">3. Risk appetite</div>
        <RadioCardGroup
          name="risk_appetite"
          value={value.risk_appetite}
          onChange={(v) => set('risk_appetite', v)}
          options={[
            { value: 'conservative', label: 'Conservative', description: 'Protect capital first' },
            { value: 'balanced', label: 'Balanced', description: 'Steady, measured growth' },
            { value: 'aggressive', label: 'Aggressive', description: 'Chase larger moves' },
          ]}
        />
        <FieldError message={errors['identity.risk_appetite']} />
      </div>

      <div>
        <div className="text-[10px] text-black/30 dark:text-white/30 uppercase font-bold tracking-[0.15em] mb-3">4. Trader type</div>
        <RadioCardGroup
          name="trader_type"
          value={value.trader_type}
          onChange={(v) => set('trader_type', v)}
          options={[
            { value: 'precision', label: 'Precision', description: 'Few, high-quality trades' },
            { value: 'frequent', label: 'Frequent', description: 'Many opportunities per session' },
          ]}
        />
        <FieldError message={errors['identity.trader_type']} />
      </div>

      <div>
        <div className="text-[10px] text-black/30 dark:text-white/30 uppercase font-bold tracking-[0.15em] mb-3">5. Discipline style</div>
        <RadioCardGroup
          name="discipline"
          value={value.discipline}
          onChange={(v) => set('discipline', v)}
          options={[
            { value: 'rule_based', label: 'Rule-Based', description: 'Strict, repeatable system' },
            { value: 'flexible_discretion', label: 'Flexible Discretion', description: 'Adapt to context' },
          ]}
        />
        <FieldError message={errors['identity.discipline']} />
      </div>
      </div>
    </StepShell>
  );
}
