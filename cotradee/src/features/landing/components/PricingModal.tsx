import React, { useEffect, useState } from 'react';
import { X, Check } from 'lucide-react';
import { Link } from 'react-router-dom';
import ParticlesCanvas from './ParticlesCanvas';
import LandingHeader from './LandingHeader';

export default function PricingModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleOpen = () => {
      setIsOpen(true);
      document.body.style.overflow = 'hidden';
    };
    
    window.addEventListener('open-pricing-modal', handleOpen);
    return () => {
      window.removeEventListener('open-pricing-modal', handleOpen);
      document.body.style.overflow = 'auto';
    };
  }, []);

  const handleClose = () => {
    setIsOpen(false);
    document.body.style.overflow = 'auto';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[120] block bg-[#050505] animate-fade-in overflow-y-auto">
      {/* Background particle system */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[8%] left-[12%] w-[600px] h-[600px] bg-[#76b900] opacity-[0.08] blur-[120px] rounded-full" />
        <div className="absolute top-[32%] right-[22%] w-[400px] h-[400px] bg-[#76b900] opacity-[0.05] blur-[100px] rounded-full" />
        <div className="absolute bottom-[8%] left-[22%] w-[500px] h-[500px] bg-[#76b900] opacity-[0.04] blur-[120px] rounded-full" />
        <div 
          className="absolute inset-0 opacity-[0.03]" 
          style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\\\'0 0 256 256\\\' xmlns=\\\'http://www.w3.org/2000/svg\\\'%3E%3Cfilter id=\\\'n\\\'%3E%3CfeTurbulence type=\\\'fractalNoise\\\' baseFrequency=\\\'0.85\\\' numOctaves=\\\'4\\\' stitchTiles=\\\'stitch\\\'/%3E%3C/filter%3E%3Crect width=\\\'100%25\\\' height=\\\'100%25\\\' filter=\\\'url(%23n)\\\'/%3E%3C/svg%3E")' }}
        />
        <ParticlesCanvas />
      </div>

      <div className="relative z-10 w-full min-h-screen flex flex-col">
        
        {/* EXACT SAME HEADER FROM LANDING PAGE */}
        <LandingHeader forceScrolled={true} />

        {/* Global Close Button (Floating Top-Right, above header z-index) */}
        <button 
          onClick={handleClose}
          className="fixed top-5 right-6 z-[130] w-8 h-8 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-white/60 hover:text-white transition-all backdrop-blur-md border border-white/5"
          aria-label="Close Comparison"
        >
          <X size={18} />
        </button>

        {/* Main Content Area */}
        <div className="w-full max-w-[1000px] mx-auto px-6 pt-32 pb-32">
          <div className="text-center mb-16 mt-8">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white tracking-tight">
              Institutional-grade <span className="text-[#76b900]">intelligence</span>.
            </h2>
            <p className="text-white/40 text-lg max-w-2xl mx-auto">
              Choose the plan that fits your trading style. From casual analysis to institutional automation.
            </p>
          </div>

          <div className="flex items-center gap-4 mb-8">
            <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent to-white/10" />
            <span className="text-xs font-bold text-white/20 uppercase tracking-[0.3em] whitespace-nowrap">Full Comparison</span>
            <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent to-white/10" />
          </div>

          {/* Comparison Table */}
          <div className="w-full overflow-x-auto pb-8 hide-scrollbar">
            <div className="min-w-[600px] bg-[#0a0a0a] border border-white/5 rounded-2xl shadow-2xl relative">
              <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#76B900]/30 to-transparent" />

              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="py-6 px-6 md:px-8 w-1/3 font-medium text-white/40 uppercase tracking-widest text-xs">Features</th>
                    <th className="py-6 px-6 md:px-8 w-1/3 text-center font-bold text-[#76B900] uppercase tracking-widest text-xs">Free</th>
                    <th className="py-6 px-6 md:px-8 w-1/3 text-center font-bold text-white/80 uppercase tracking-widest text-xs">Pro</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  <Row title="Price" free="Free" pro="$49/mo" highlight />
                  <Row title="Account Required" free="Yes" pro="Yes" />
                  <Row title="Automated Execution" free="No" pro={<CheckIcon />} />
                  <Row title="Automated Scheduling" free="No" pro={<CheckIcon />} />
                  <Row title="AI Technical Analysis" free="1 per day" pro="Unlimited" />
                  <Row title="Custom Cycle Intervals" free="—" pro={<CheckIcon />} />
                  <Row title="Live Chart Updates" free="Real-time" pro="Real-time" />
                  <Row title="Risk Engine Safeguards" free={<CheckIcon />} pro={<CheckIcon />} />
                  <Row title="Trade Journal" free="Basic" pro="Advanced" />
                  <Row title="Telegram Alerts" free="—" pro={<CheckIcon />} />
                  <Row title="Support" free="Community" pro="Priority" />
                </tbody>
              </table>
            </div>
          </div>
          
          {/* Call to action at bottom */}
          <div className="mt-12 mb-16 flex justify-center text-center">
              <Link 
                to="/register?returnTo=/dashboard/settings/billing" 
                className="btn-cta-brand px-12 py-4 text-base"
              >
                Get Started Now
              </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ title, free, pro, highlight = false }: { title: string, free: React.ReactNode, pro: React.ReactNode, highlight?: boolean }) {
  return (
    <tr className={`hover:bg-white/[0.02] transition-colors ${highlight ? 'font-medium text-white' : 'text-white/70'}`}>
      <td className="py-5 px-6 md:px-8 whitespace-nowrap">{title}</td>
      <td className="py-5 px-6 md:px-8 text-center">{free}</td>
      <td className="py-5 px-6 md:px-8 text-center">{pro}</td>
    </tr>
  );
}

function CheckIcon() {
  return (
    <div className="flex justify-center">
      <div className="bg-[#76B900]/10 rounded-full p-1 border border-[#76B900]/20">
        <Check size={14} className="text-[#76B900]" />
      </div>
    </div>
  );
}
