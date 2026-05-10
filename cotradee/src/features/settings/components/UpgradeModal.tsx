import { useEffect, useState } from 'react';
import { X, Check, CreditCard, ShieldCheck, Zap, ExternalLink } from 'lucide-react';
import { useToast } from '@/hooks/useToast';

interface Subscription {
  tier: string;
  status: string;
}

export default function UpgradeModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentSub, setCurrentSub] = useState<Subscription | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    const handleOpen = () => {
      setIsOpen(true);
      document.body.style.overflow = 'hidden';
      fetchSubscription();
    };
    
    window.addEventListener('open-upgrade-modal', handleOpen);
    return () => {
      window.removeEventListener('open-upgrade-modal', handleOpen);
      document.body.style.overflow = 'auto';
    };
  }, []);

  const fetchSubscription = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/billing/subscription', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentSub(data);
      }
    } catch (err) {
      console.error('Failed to fetch subscription:', err);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    document.body.style.overflow = 'auto';
  };

  const handleUpgrade = async (tier: string) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/billing/checkout', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ provider: 'paddle', tier })
      });

      if (!response.ok) throw new Error('Failed to initiate checkout');
      
      const { checkout_url } = await response.json();
      
      toast({
        title: "Redirecting to checkout",
        description: "Please complete your payment on the secure provider page.",
      });

      // In a real app, you'd redirect to the checkout URL
      window.location.href = checkout_url;
    } catch (err) {
      toast({
        title: "Upgrade Failed",
        description: "Unable to connect to the payment provider. Please try again later.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-300 px-4">
      <div className="relative w-full max-w-2xl bg-[#0a0a0a] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
        {/* NVIDIA-style Glow */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-[#76b900]/10 blur-[80px] rounded-full pointer-events-none" />
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="bg-[#76b900]/20 p-2 rounded-lg border border-[#76b900]/20">
              <Zap className="text-[#76b900] w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Upgrade to Pro</h2>
              <p className="text-xs text-white/40">Unlock institutional-grade trading tools</p>
            </div>
          </div>
          <button onClick={handleClose} className="text-white/40 hover:text-white transition-colors p-1">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Features List */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider">What's Included</h3>
              <ul className="space-y-3">
                <FeatureItem text="Unlimited symbols tracking" />
                <FeatureItem text="Automated trade execution" />
                <FeatureItem text="Institutional risk guard" />
                <FeatureItem text="Advanced P&L analytics" />
                <FeatureItem text="Priority 24/7 support" />
              </ul>
            </div>

            {/* Pricing Options */}
            <div className="space-y-6">
              <div className="bg-white/5 rounded-xl p-5 border border-white/10 hover:border-[#76b900]/50 transition-colors group">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <span className="text-xs font-bold text-[#76b900] bg-[#76b900]/10 px-2 py-0.5 rounded-full uppercase tracking-widest">Enterprise Grade</span>
                    <h4 className="text-lg font-bold text-white mt-1">Pro Membership</h4>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-bold text-white">$49</span>
                    <span className="text-xs text-white/40">/mo</span>
                  </div>
                </div>
                
                <p className="text-xs text-white/60 mb-6 leading-relaxed">
                  Full access to the eTradie platform with managed infrastructure and automated execution.
                </p>

                <button 
                  onClick={() => handleUpgrade('pro_managed')}
                  disabled={isLoading || currentSub?.tier === 'pro'}
                  className="w-full btn-cta-brand py-3 text-sm flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                  ) : currentSub?.tier === 'pro' ? (
                    'Current Plan'
                  ) : (
                    <>
                      Proceed to Checkout
                      <ExternalLink size={14} />
                    </>
                  )}
                </button>
              </div>

              <div className="flex items-center gap-2 text-[10px] text-white/40 justify-center">
                <ShieldCheck size={12} className="text-[#76b900]" />
                Secure payments handled by Paddle & Lemon Squeezy
              </div>
            </div>
          </div>
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

function FeatureItem({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-2.5 text-sm text-white/80">
      <div className="mt-1 bg-[#76b900]/20 rounded-full p-0.5">
        <Check size={10} className="text-[#76b900]" />
      </div>
      {text}
    </li>
  );
}
