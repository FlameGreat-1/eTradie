import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, Check, CreditCard, ShieldCheck, Zap, ExternalLink, KeyRound, Server } from 'lucide-react';
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
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-300 px-4 py-8 overflow-y-auto">
      <div className="relative w-full max-w-3xl bg-[#0a0a0a] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300 my-auto">
        {/* NVIDIA-style Glow */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-[#76b900]/10 blur-[80px] rounded-full pointer-events-none" />

        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="bg-transparent p-2 rounded-lg border border-[#76b900]">
              <Zap className="text-[#76b900] w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Upgrade to Pro</h2>
              <p className="text-xs text-white/40">Unlock institutional-grade trading tools</p>
            </div>
          </div>
          <button onClick={handleClose} className="text-white/40 hover:text-white transition-colors p-1" aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-8 space-y-8">
          {/* Provider selector */}
          <div>
            <h3 className="text-xs font-semibold text-white/60 uppercase tracking-wider mb-3">Payment Provider</h3>
            <div className="grid grid-cols-2 gap-3">
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
                subtitle="Cards, PayPal, regional methods"
              />
            </div>
          </div>

          {/* Tier cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <TierCard
              tier="pro_byok"
              title="Pro BYOK"
              priceLabel="$29"
              icon={<KeyRound className="text-[#76b900] w-4 h-4" />}
              tagline="Bring your own AI key"
              description="Full Pro access using your own Anthropic / OpenAI / Gemini API key. Best for power users with existing LLM credits."
              features={['Unlimited symbols', 'Automated execution', 'Trade management', 'Use your own LLM key']}
              currentTier={currentSub?.tier}
              isLoading={isLoading && loadingTier === 'pro_byok'}
              onUpgrade={() => handleUpgrade('pro_byok')}
            />
            <TierCard
              tier="pro_managed"
              title="Pro Managed"
              priceLabel="$49"
              icon={<Server className="text-[#76b900] w-4 h-4" />}
              tagline="We provide the AI key"
              description="Everything in Pro BYOK, plus the platform-managed AI key. No external accounts to set up."
              features={['Everything in Pro BYOK', 'Platform-managed LLM key', 'Higher rate limits', 'Priority 24/7 support']}
              currentTier={currentSub?.tier}
              isLoading={isLoading && loadingTier === 'pro_managed'}
              onUpgrade={() => handleUpgrade('pro_managed')}
              highlight
            />
          </div>

          <div className="flex items-center gap-2 text-[10px] text-white/40 justify-center">
            <ShieldCheck size={12} className="text-[#76b900]" />
            Secure payments handled by Paddle &amp; Lemon Squeezy. You can cancel anytime from this page.
          </div>

          {/* Checkout-time compliance footnote. Required for Paddle /
              Lemon Squeezy Merchant-of-Record platforms: the user
              must be able to reach the Terms, Billing Policy, Refund
              Policy, and Risk Disclosure at the moment of purchase. */}
          <p className="text-[10px] text-white/40 leading-relaxed text-center max-w-md mx-auto">
            By proceeding to checkout you agree to our{' '}
            <Link to="/terms" className="underline decoration-[#76b900]/60 underline-offset-2 hover:text-white/80" onClick={handleClose}>Terms of Service</Link>,{' '}
            <Link to="/billing-policy" className="underline decoration-[#76b900]/60 underline-offset-2 hover:text-white/80" onClick={handleClose}>Billing Policy</Link>,{' '}
            <Link to="/refund" className="underline decoration-[#76b900]/60 underline-offset-2 hover:text-white/80" onClick={handleClose}>Refund Policy</Link>, and{' '}
            <Link to="/risk-disclosure" className="underline decoration-[#76b900]/60 underline-offset-2 hover:text-white/80" onClick={handleClose}>Risk Disclosure</Link>.
          </p>
        </div>

        {/* Footer */}
        <div className="bg-white/[0.02] border-t border-white/5 p-4 flex items-center justify-center gap-6">
          <div className="flex items-center gap-2 grayscale opacity-40">
            <CreditCard size={14} className="text-white" />
            <span className="text-[10px] text-white font-medium">VISA / MASTERCARD</span>
          </div>
          <div className="h-3 w-[1px] bg-white/10" />
          <div className="text-[10px] text-white/40 font-medium">CANCEL ANYTIME</div>
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
      className={`text-left rounded-xl p-4 border transition-colors ${
        isSelected
          ? 'bg-[#76b900]/10 border-[#76b900]/50'
          : 'bg-white/5 border-white/10 hover:border-white/30'
      }`}
      aria-pressed={isSelected}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-semibold text-white">{title}</span>
        {isSelected && (
          <div className="bg-[#76b900]/20 rounded-full p-0.5">
            <Check size={10} className="text-[#76b900]" />
          </div>
        )}
      </div>
      <p className="text-[11px] text-white/50">{subtitle}</p>
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
      className={`relative bg-white/5 rounded-xl p-5 border transition-colors ${
        highlight ? 'border-[#76b900]/40 hover:border-[#76b900]/70' : 'border-white/10 hover:border-white/30'
      }`}
    >
      {highlight && (
        <span className="absolute -top-2 right-4 text-[10px] font-bold text-black bg-[#76b900] px-2 py-0.5 rounded-full uppercase tracking-widest">
          Most Popular
        </span>
      )}
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <h4 className="text-lg font-bold text-white">{title}</h4>
      </div>
      <p className="text-xs text-[#76b900] mb-3">{tagline}</p>
      <div className="flex items-baseline gap-1 mb-4">
        <span className="text-2xl font-bold text-white">{priceLabel}</span>
        <span className="text-xs text-white/40">/mo</span>
      </div>
      <p className="text-xs text-white/60 mb-5 leading-relaxed">{description}</p>
      <ul className="space-y-2 mb-6">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-white/80">
            <div className="mt-1 bg-[#76b900]/20 rounded-full p-0.5">
              <Check size={10} className="text-[#76b900]" />
            </div>
            {f}
          </li>
        ))}
      </ul>
      <button
        onClick={onUpgrade}
        disabled={isLoading || isCurrent}
        className="w-full py-3 text-sm flex items-center justify-center gap-2 disabled:opacity-60 rounded-xl bg-transparent border border-[#76b900] text-white hover:bg-[#76b900]/5 transition-colors font-semibold"
      >
        {isCurrent ? (
          'Current Plan'
        ) : isLoading ? (
          <div className="w-4 h-4 border-2 border-[#76b900]/20 border-t-[#76b900] rounded-full animate-spin" />
        ) : (
          <>
            Proceed to Checkout
            <ExternalLink size={14} className="text-[#76b900]" />
          </>
        )}
      </button>
    </div>
  );
}
