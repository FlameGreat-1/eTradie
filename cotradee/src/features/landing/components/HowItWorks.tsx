
import { 
  BrainCircuit, Eye,
  BookOpen, PieChart, ShieldAlert, Zap, Cpu, Lock 
} from 'lucide-react';

const HOW_IT_WORKS_STEPS = [
  {
    customAsset: "/assets/landing/icons/connect.svg",
    title: "Connect Broker",
    description: "Link your MT5 terminal securely and configure your risk parameters.",
    borderColor: "border-blue-200 dark:border-blue-900"
  },
  {
    icon: <img src="/assets/landing/icons/analysis.svg" alt="Analysis" className="w-8 h-8 object-contain" />,
    title: "Analysis",
    description: "Technical and Macroeconomics Analysis are executed in seconds."
  },
  {
    icon: <BrainCircuit className="text-slate-700 dark:text-slate-300" size={24} />,
    title: "Exoper AI",
    description: "Trades with our trading system with precision, discipline and confidence as discretionary trader would."
  },
  {
    icon: <Eye className="text-slate-700 dark:text-slate-300" size={24} />,
    title: "Exoper Watcher",
    description: "Monitors live trades and pending orders from execute to closure."
  },
  {
    customAsset: "/assets/landing/icons/control.svg",
    title: "Stay in Control",
    description: "Watch live performance, review analytics, and withdraw your funds at any time.",
    borderColor: "border-emerald-200 dark:border-emerald-900"
  },
  {
    customAsset: "/assets/landing/icons/security.svg",
    title: "Security",
    description: "Enterprise-grade encryption protecting your data and API credentials.",
    borderColor: "border-cyan-200 dark:border-cyan-900"
  }
];

const WHY_IT_WORKS_FEATURES = [
  {
    icon: <BookOpen className="text-slate-600 dark:text-slate-300" size={20} />,
    title: "Automated Journaling",
    description: "Every trade is meticulously logged with deep analytics for transparent performance review."
  },
  {
    icon: <PieChart className="text-slate-600 dark:text-slate-300" size={20} />,
    title: "Portfolio Optimization",
    description: "Dynamically balances lot sizing and asset allocation to maximize returns."
  },
  {
    icon: <ShieldAlert className="text-slate-600 dark:text-slate-300" size={20} />,
    title: "Risk Management",
    description: "Enforces strict daily drawdown limits and max exposure rules without emotional override."
  },
  {
    icon: <Zap className="text-slate-600 dark:text-slate-300" size={20} />,
    title: "Zero Latency",
    description: "Captures immediate market opportunities directly on the broker's server."
  },
  {
    icon: <Cpu className="text-slate-600 dark:text-slate-300" size={20} />,
    title: "Emotionless Logic",
    description: "Removes psychological errors by strictly adhering to mathematical rulesets."
  },
  {
    icon: <Lock className="text-slate-600 dark:text-slate-300" size={20} />,
    title: "Absolute Custody",
    description: "We never hold your funds. You retain 100% control in your own brokerage account."
  }
];

export default function HowItWorks() {
  return (
    <section className="relative py-24 border-t border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-[#050505]" id="how-it-works">
      <div className="max-w-[1280px] mx-auto px-6 md:px-8">
        
        {/* HOW IT WORKS SECTION */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white mb-6">
            How It Works
          </h2>
          <p className="text-lg text-slate-600 dark:text-white/60 leading-relaxed">
            The autonomous trading journey from connection to execution.
          </p>
        </div>

        {/* TIMELINE LAYOUT */}
        <div className="relative mb-32 max-w-5xl mx-auto">
          {/* Mobile Connecting Line */}
          <div className="md:hidden absolute top-[40px] bottom-[40px] left-[40px] w-[2px] bg-gradient-to-b from-slate-200 via-slate-300 to-slate-200 dark:from-white/5 dark:via-white/10 dark:to-white/5 z-0" />

          <div className="flex flex-col md:flex-row justify-between gap-12 md:gap-4 relative z-10">
            {HOW_IT_WORKS_STEPS.map((step, index) => {
              const lineAsset = index === 1 ? "/assets/landing/icons/line-1.svg" : index === 2 ? "/assets/landing/icons/Line-2.svg" : "/assets/landing/icons/Line-3.svg";
              
              return (
              <div key={index} className="flex flex-row md:flex-col items-start md:items-center text-left md:text-center flex-1 relative group">
                
                {/* Desktop Connecting Line */}
                {index < HOW_IT_WORKS_STEPS.length - 1 && (
                  <div className="hidden md:flex absolute top-[40px] left-[50%] w-full -translate-y-1/2 z-0 px-[40px] items-center pointer-events-none">
                    <img src={lineAsset} className="w-full h-[3px] object-cover" alt="" />
                  </div>
                )}
                
                {/* Icon Circle */}
                {step.customAsset ? (
                  <div className="w-20 h-20 flex-shrink-0 relative z-10 overflow-hidden group-hover:scale-105 transition-transform duration-300">
                    <img src={step.customAsset} alt={step.title} className="w-full h-full object-contain bg-white dark:bg-[#050505] rounded-full" />
                  </div>
                ) : (
                  <div className="w-20 h-20 rounded-full border-[2px] border-[#CCCCCC] dark:border-[#CCCCCC] bg-white dark:bg-[#050505] flex items-center justify-center flex-shrink-0 relative z-10 overflow-hidden group-hover:scale-105 transition-transform duration-300">
                    <div className="relative z-10 flex items-center justify-center">
                      {step.icon}
                    </div>
                  </div>
                )}

                {/* Text Content */}
                <div className="ml-6 md:ml-0 md:mt-6 flex flex-col items-start md:items-center">
                  <span className="text-xs font-black text-slate-400 dark:text-white/20 mb-1 uppercase tracking-wider">
                    Step 0{index + 1}
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                    {step.title}
                  </h3>
                  <p className="text-slate-600 dark:text-white/60 text-sm leading-relaxed max-w-[200px]">
                    {step.description}
                  </p>
                </div>
                
              </div>
              );
            })}
          </div>
        </div>

        {/* WHY IT WORKS SECTION */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white mb-6">
            Why It Works
          </h2>
          <p className="text-lg text-slate-600 dark:text-white/60 leading-relaxed">
            Built on institutional-grade architecture designed to protect capital and compound growth.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {WHY_IT_WORKS_FEATURES.map((feature, index) => (
            <div key={index} className="bg-white dark:bg-[#0c0c0c] rounded-2xl p-6 border border-slate-200 dark:border-white/5 shadow-md dark:shadow-xl hover:border-slate-300 dark:hover:border-white/10 transition-colors duration-300 flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-[#1a1a1a] border border-slate-200 dark:border-white/5 flex items-center justify-center flex-shrink-0 shadow-sm dark:shadow-inner">
                {feature.icon}
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-slate-600 dark:text-white/50 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
