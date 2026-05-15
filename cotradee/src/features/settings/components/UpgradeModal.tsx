import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, Check, CreditCard, ShieldCheck, Zap, ExternalLink, KeyRound, Server, Sparkles } from 'lucide-react';
import { AxiosError } from 'axios';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useToast } from '@/hooks/useToast';
import { useAuth } from '@/features/auth';

interface Subscription {
  tier: string;
  status: string;
  current_period_end?: string | null;
}

/**
 * Canonical React Query key for the current user's billing
 * subscription. Exported (lowercase const) so the rest of the SPA can
 * import it for cache-key consistency, and so the realtime event map
 * (features/realtime/eventMap.ts) invalidates the same key when a
 * SUBSCRIPTION_* webhook lands.
 */
export const BILLING_SUBSCRIPTION_QUERY_KEY = ['billing', 'subscription'] as const;

/** Fetch the current subscription via the gateway's billing endpoint. */
async function fetchSubscription(): Promise<Subscription> {
  const { data } = await api.gateway.get<Subscription>('/api/v1/billing/subscription');
  return data;
}

/**
 * Shared hook so any caller (the modal, a Pro-gated feature, the header
 * badge) reads from the SAME React Query cache. A single SUBSCRIPTION_*
 * realtime event invalidates this key and every caller refetches in
 * lockstep.
 *
 * The query is gated on AuthContext.isAuthenticated so an unauthenticated
 * visitor never hits /api/v1/billing/subscription. That endpoint is
 * protected by RequireAuth; calling it as a guest returns 401, which
 * the global axios interceptor treats as a session-expiry signal -
 * triggering POST /auth/refresh and, when that fails (no refresh
 * cookie either, gateway responds 400 'refresh_token is required'),
 * a hard window.location.assign('/login'). Because UpgradeModal is
 * mounted globally in App.tsx (it must be reachable from any route
 * via the 'open-upgrade-modal' window event), an ungated query here
 * produces an infinite refresh -> redirect loop on first visit.
 * Disabling the query for guests keeps the modal mounted but quiet
 * until the user actually logs in.
 */
export function useBillingSubscription() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  return useQuery<Subscription>({
    queryKey: BILLING_SUBSCRIPTION_QUERY_KEY,
    queryFn: fetchSubscription,
    // Only fire after AuthContext has settled AND the user is
    // authenticated. The endpoint 401s for guests, and that 401
    // cannot be safely silent-refreshed (no refresh cookie either),
    // so the axios interceptor would otherwise navigate to /login
    // on every app mount and produce the observed reload loop.
    enabled: !authLoading && isAuthenticated,
    // Matches the gateway's in-process subscription cache TTL so we
    // don't hammer the API on rapid tab/page switches but still pick
    // up server-pushed invalidations promptly.
    staleTime: 30_000,
    retry: (failureCount, error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      // 401/403/404/429 are not retryable for this endpoint; everything
      // else gets one retry (covers the gateway's 503 transient response).
      if (status && status >= 400 && status < 500) return false;
      return failureCount < 1;
    },
  });
}

type Provider = 'paddle' | 'lemonsqueezy';
type Tier = 'pro_byok' | 'pro_managed';

// Post-Batch-11 the SPA no longer reads tokens from localStorage. The
// access token lives in an HttpOnly cookie that JS cannot see. Every
// authenticated request must go through `api.gateway`, which:
//   - sets withCredentials:true so the browser attaches the cookie jar,
//   - reads csrf_token from document.cookie and echoes it as the
//     X-CSRF-Token header on POST / PUT / PATCH / DELETE,
//   - handles silent token refresh via /auth/refresh and redirects
//     to /login on a hard 401.
//
// The previous implementation used raw fetch() + localStorage.getItem(
// 'access_token'). After Batch 11 that key never exists, so the
// Authorization header was `Bearer null` and the gateway responded
// with 401 'missing authorization header' on every modal open.
export default function UpgradeModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingTier, setLoadingTier] = useState<Tier | null>(null);
  const [provider, setProvider] = useState<Provider>('paddle');
  const { toast } = useToast();

  // Read subscription state from the shared React Query cache. The
  // realtime event provider invalidates this key when a SUBSCRIPTION_*
  // event arrives, so the modal reflects post-payment tier changes
  // without any extra wiring.
  const { data: currentSub } = useBillingSubscription();

  useEffect(() => {
    const handleOpen = () => {
      setIsOpen(true);
      document.body.style.overflow = 'hidden';
    };

    window.addEventListener('open-upgrade-modal', handleOpen);
    return () => {
      window.removeEventListener('open-upgrade-modal', handleOpen);
      document.body.style.overflow = 'auto';
    };
  }, []);

  const handleClose = () => {
    setIsOpen(false);
    document.body.style.overflow = 'auto';
  };

  const handleUpgrade = async (tier: Tier) => {
    setIsLoading(true);
    setLoadingTier(tier);
    try {
      const { data } = await api.gateway.post<{ checkout_url?: string }>(
        '/api/v1/billing/checkout',
        { provider, tier },
      );
      const checkoutURL = data.checkout_url;
      if (!checkoutURL) {
        throw new Error('Billing service returned an empty checkout URL.');
      }

      toast({
        title: 'Redirecting to checkout',
        description: 'Please complete your payment on the secure provider page.',
      });
      window.location.href = checkoutURL;
    } catch (err) {
      // Special case: 409 "already subscribed" from the gateway's
      // current-tier guard. The user is already on a paid plan and
      // the platform refuses to create a SECOND provider subscription
      // for them — this is the double-charge defence, not a bug.
      // Show a friendly toast that explains the existing state
      // instead of the generic "Upgrade Failed" message.
      if (
        err instanceof AxiosError &&
        err.response?.status === 409 &&
        (err.response.data as { error?: string } | undefined)?.error === 'already subscribed'
      ) {
        const body = err.response.data as {
          current_tier?: string;
          current_status?: string;
          current_period_end?: string | null;
        };
        const tierLabel = body.current_tier === 'pro_managed' ? 'Pro Managed' :
                          body.current_tier === 'pro_byok'    ? 'Pro BYOK'    :
                          body.current_tier ?? 'Pro';
        toast({
          title: 'Already on a Pro plan',
          description:
            `You're already subscribed to ${tierLabel}` +
            (body.current_status && body.current_status !== 'active'
              ? ` (status: ${body.current_status})`
              : '') +
            '. Cancel or change your plan from your provider dashboard before initiating a new checkout.',
        });
        return;
      }

      // Generic failure path — surface the server-side reason so the
      // user sees the real failure mode (`checkout rejected by
      // billing service`, `billing service unavailable`, etc.)
      // instead of a generic message. axios puts the parsed response
      // body on err.response.
      let serverMessage = 'Unable to start checkout.';
      if (err instanceof AxiosError) {
        const body = err.response?.data as { error?: string } | undefined;
        if (body?.error) serverMessage = body.error;
        else if (err.message) serverMessage = err.message;
      } else if (err instanceof Error) {
        serverMessage = err.message;
      }
      toast({
        title: 'Upgrade Failed',
        description: serverMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      setLoadingTier(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/95 backdrop-blur-md animate-in fade-in duration-500 px-4 py-8 overflow-y-auto selection:bg-brand selection:text-black">
      <div className="relative w-full max-w-3xl bg-white dark:bg-black border border-black/10 dark:border-white/10 rounded-[2.5rem] shadow-[0_0_100px_-20px_rgba(0,0,0,0.5)] overflow-hidden animate-in zoom-in-95 duration-500 my-auto">
        {/* Brand Accent Glow */}
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-brand/5 blur-[120px] rounded-full pointer-events-none" />

        {/* Header */}
        <div className="flex items-center justify-between p-8 border-b border-black/5 dark:border-white/5">
          <div className="flex items-center gap-4">
            <div className="space-y-0.5">
              <h2 className="text-xl font-black text-black dark:text-white uppercase tracking-tight">Upgrade to Pro</h2>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Unlock institutional-grade trading tools</p>
            </div>
          </div>
          <button onClick={handleClose} className="text-black/20 dark:text-white/20 hover:text-black dark:hover:text-white transition-all p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5" aria-label="Close">
            <X size={20} strokeWidth={3} />
          </button>
        </div>

        {/* Body */}
        <div className="p-8 md:p-10 space-y-10">
          {/* Provider selector */}
          <div className="space-y-4">
            <h3 className="text-[10px] font-black text-black/30 dark:text-white/30 uppercase tracking-[0.3em] ml-1">Payment Provider</h3>
            <div className="grid grid-cols-2 gap-4">
              <ProviderOption
                value="paddle"
                selected={provider}
                onSelect={setProvider}
                title="Paddle"
                subtitle="Cards, Apple Pay, Google Pay"
              />
              <ProviderOption
                value="lemonsqueezy"
                selected={provider}
                onSelect={setProvider}
                title="Lemon Squeezy"
                subtitle="Cards, PayPal, Regional"
              />
            </div>
          </div>

          {/* Tier cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <TierCard
              tier="pro_byok"
              title="Pro BYOK"
              priceLabel="$29"
              icon={<KeyRound className="text-brand w-4 h-4" strokeWidth={3} />}
              tagline="Bring your own AI key"
              description="Full Pro access using your own Anthropic, OpenAI, or Gemini keys. Best for heavy-volume power users."
              features={['Unlimited symbols', 'Automated execution', 'Trade management', 'Custom LLM usage']}
              currentTier={currentSub?.tier}
              isLoading={isLoading && loadingTier === 'pro_byok'}
              onUpgrade={() => handleUpgrade('pro_byok')}
            />
            <TierCard
              tier="pro_managed"
              title="Pro Managed"
              priceLabel="$49"
              icon={<Server className="text-brand w-4 h-4" strokeWidth={3} />}
              tagline="We provide the AI key"
              description="Everything in Pro BYOK, plus our internal platform-managed AI keys. No external accounts required."
              features={['Everything in Pro BYOK', 'Managed LLM keys', 'Higher rate limits', 'Priority 24/7 support']}
              currentTier={currentSub?.tier}
              isLoading={isLoading && loadingTier === 'pro_managed'}
              onUpgrade={() => handleUpgrade('pro_managed')}
              highlight
            />
          </div>

          {/* Security & Compliance */}
          <div className="space-y-8">
            <div className="flex items-center gap-3 text-[10px] font-bold text-black/40 dark:text-white/40 justify-center bg-black/5 dark:bg-white/5 py-3 px-6 rounded-2xl border border-black/5 dark:border-white/5">
              <ShieldCheck size={14} className="text-brand" strokeWidth={3} />
              Secure payments via encrypted gateways. Cancel anytime from this dashboard.
            </div>

            <p className="text-[9px] font-black uppercase tracking-widest text-black/20 dark:text-white/20 leading-relaxed text-center max-w-lg mx-auto">
              By proceeding to checkout you agree to our{' '}
              <Link to="/terms" className="text-black/40 dark:text-white/40 underline decoration-black/10 dark:decoration-white/10 underline-offset-4 hover:text-brand transition-colors" onClick={handleClose}>Terms</Link>,{' '}
              <Link to="/billing-policy" className="text-black/40 dark:text-white/40 underline decoration-black/10 dark:decoration-white/10 underline-offset-4 hover:text-brand transition-colors" onClick={handleClose}>Billing</Link>,{' '}
              <Link to="/refund" className="text-black/40 dark:text-white/40 underline decoration-black/10 dark:decoration-white/10 underline-offset-4 hover:text-brand transition-colors" onClick={handleClose}>Refund Policy</Link>, and{' '}
              <Link to="/risk-disclosure" className="text-black/40 dark:text-white/40 underline decoration-black/10 dark:decoration-white/10 underline-offset-4 hover:text-brand transition-colors" onClick={handleClose}>Risk Disclosure</Link>.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-black dark:bg-white p-6 flex items-center justify-between px-10">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <CreditCard size={14} className="text-white/40 dark:text-black/40" strokeWidth={3} />
              <span className="text-[9px] text-white/60 dark:text-black/60 font-black uppercase tracking-widest">VISA / MASTERCARD</span>
            </div>
            <div className="h-4 w-[1px] bg-white/10 dark:bg-black/10" />
            <div className="text-[9px] text-white/60 dark:text-black/60 font-black uppercase tracking-widest">NO COMMITMENT</div>
          </div>
          <div className="text-[10px] text-white dark:text-black font-black uppercase tracking-widest opacity-40">
            Secure Terminal
          </div>
        </div>
      </div>
    </div>
  );
}

interface ProviderOptionProps {
  value: Provider;
  selected: Provider;
  onSelect: (p: Provider) => void;
  title: string;
  subtitle: string;
}

function ProviderOption({ value, selected, onSelect, title, subtitle }: ProviderOptionProps) {
  const isSelected = value === selected;
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`text-left rounded-2xl p-5 border transition-all duration-300 ${
        isSelected
          ? 'bg-black dark:bg-white border-transparent shadow-2xl shadow-brand/20 -translate-y-0.5'
          : 'bg-black/[0.02] dark:bg-white/[0.02] border-black/10 dark:border-white/10 hover:border-black/30 dark:hover:border-white/30'
      }`}
      aria-pressed={isSelected}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className={`text-xs font-black uppercase tracking-widest ${isSelected ? 'text-white dark:text-black' : 'text-black/60 dark:text-white/60'}`}>{title}</span>
        {isSelected && (
          <div className="bg-brand rounded-full p-0.5">
            <Check size={10} className="text-black" strokeWidth={4} />
          </div>
        )}
      </div>
      <p className={`text-[10px] font-bold tracking-tight ${isSelected ? 'text-white/60 dark:text-black/60' : 'text-black/30 dark:text-white/30'}`}>{subtitle}</p>
    </button>
  );
}

interface TierCardProps {
  tier: Tier;
  title: string;
  priceLabel: string;
  icon: React.ReactNode;
  tagline: string;
  description: string;
  features: string[];
  currentTier: string | undefined;
  isLoading: boolean;
  onUpgrade: () => void;
  highlight?: boolean;
}

function TierCard({
  tier,
  title,
  priceLabel,
  icon,
  tagline,
  description,
  features,
  currentTier,
  isLoading,
  onUpgrade,
  highlight,
}: TierCardProps) {
  const isCurrent = currentTier === tier;
  return (
    <div
      className={`relative rounded-[2rem] p-6 border transition-all duration-500 overflow-hidden ${
        highlight 
          ? 'bg-black/[0.03] dark:bg-white/[0.03] border-brand/20 shadow-2xl shadow-brand/5' 
          : 'bg-black/[0.01] dark:bg-white/[0.01] border-black/10 dark:border-white/10'
      }`}
    >
      {highlight && (
        <div className="absolute top-4 right-6">
          <div className="flex items-center gap-1.5 bg-brand px-3 py-1 rounded-full shadow-lg shadow-brand/20">
            <Sparkles size={10} className="text-black" strokeWidth={4} />
            <span className="text-[9px] font-black text-black uppercase tracking-widest">
              Most Popular
            </span>
          </div>
        </div>
      )}
      
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 rounded-xl bg-black/5 dark:bg-white/5">
          {icon}
        </div>
        <h4 className="text-base font-black text-black dark:text-white uppercase tracking-tight">{title}</h4>
      </div>
      
      <p className="text-[10px] font-black text-brand uppercase tracking-widest mb-4">{tagline}</p>
      
      <div className="flex items-baseline gap-1.5 mb-6">
        <span className="text-4xl font-black text-black dark:text-white tracking-tighter">{priceLabel}</span>
        <span className="text-[10px] font-black uppercase tracking-widest text-black/20 dark:text-white/20">/ MONTH</span>
      </div>
      
      <p className="text-xs font-bold text-black/40 dark:text-white/40 mb-8 leading-relaxed">{description}</p>
      
      <ul className="space-y-3 mb-10">
        {features.map((f) => (
          <li key={f} className="flex items-center gap-3 text-[11px] font-bold text-black/60 dark:text-white/60">
            <div className="bg-brand/10 rounded-lg p-1">
              <Check size={12} className="text-brand" strokeWidth={4} />
            </div>
            {f}
          </li>
        ))}
      </ul>
      
      <button
        onClick={onUpgrade}
        disabled={isLoading || isCurrent}
        className={`w-full py-4 text-[10px] font-black uppercase tracking-[0.2em] flex items-center justify-center gap-2 rounded-2xl transition-all duration-300 disabled:opacity-40 active:scale-[0.98]
                   ${isCurrent 
                     ? 'bg-black/5 dark:bg-white/5 text-black/20 dark:text-white/20 cursor-default' 
                     : 'bg-black dark:bg-white text-white dark:text-black shadow-xl shadow-black/10 dark:shadow-white/10 hover:opacity-90'
                   }`}
      >
        {isCurrent ? (
          'Active Plan'
        ) : isLoading ? (
          <Loader2 size={16} className="animate-spin" strokeWidth={3} />
        ) : (
          <>
            Proceed to Checkout
            <ExternalLink size={14} strokeWidth={3} />
          </>
        )}
      </button>
    </div>
  );
}

function Loader2({ className, size, strokeWidth }: { className?: string; size?: number; strokeWidth?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size || 24}
      height={size || 24}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth || 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

