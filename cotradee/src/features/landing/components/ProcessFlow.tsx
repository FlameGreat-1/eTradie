import React from 'react';
import { Network, Key, Sliders, BrainCircuit, ShieldCheck, LineChart, Globe, Zap, Briefcase, Cpu, Settings, Server } from 'lucide-react';

const LEFT_INPUTS = [
  { title: 'Broker/MT5', icon: <Network size={20} />, y: 15 },
  { title: 'Vault', icon: <Key size={20} />, y: 32.5 },
  { title: 'Execution', icon: <Sliders size={20} />, y: 50 },
  { title: 'Tech. Analysis', icon: <LineChart size={20} />, y: 67.5 },
  { title: 'Macro Analysis', icon: <Globe size={20} />, y: 85 },
];

const RIGHT_INTERNAL = [
  { title: 'Trading System', icon: <Cpu size={14} />, top: '15%', left: '12%' },
  { title: 'Execution', icon: <Zap size={14} />, top: '15%', right: '12%' },
  { title: 'Trade Management', icon: <Briefcase size={14} />, bottom: '12%', left: '50%', transform: 'translateX(-50%)' },
];

export default function ProcessFlow() {
  return (
    <section className="relative py-24 border-t border-slate-200 dark:border-white/5" id="process-flow">
      <div className="max-w-[1280px] mx-auto px-6 md:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-lg opacity-68 leading-relaxed">
            Technical analysis, macroeconomic analysis, execution, and trade management are handled autonomously with you in the loop while the system trades with precision, discipline, and confidence.
          </p>
        </div>
      </div>

      {/* ── DESKTOP LAYOUT (Horizontal Pipeline) ── */}
      <div className="w-full max-w-[1800px] mx-auto px-4 md:px-8 hidden lg:block">
        <div className="w-full overflow-x-auto pb-8 hide-scrollbar">
          <div className="relative w-full min-w-[1024px] h-[550px] xl:h-[600px] bg-slate-50 dark:bg-[#080808] rounded-[2rem] border border-slate-200 dark:border-white/10 shadow-xl dark:shadow-2xl overflow-hidden mx-auto">
            
            {/* Background Glows */}
            <div className="absolute top-[20%] left-[30%] w-[30%] h-[60%] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none" />
            <div className="absolute top-[10%] left-[55%] w-[30%] h-[40%] bg-purple-600/10 blur-[100px] rounded-full pointer-events-none" />

            {/* SVG Wires & Glowing Packets */}
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
              
              {/* Left Inputs -> Settings Node / Engine Node */}
              {LEFT_INPUTS.map((input, i) => {
                let pathData = "";
                let dur = 3;
                let strokeColor = "#06b6d4"; // Cyan for config and data entering engine

                if (i < 3) {
                  // Top 3 -> Settings Node
                  pathData = `M 18 ${input.y} C 21 ${input.y}, 21 32.5, 24 32.5`;
                  dur = 2 + i * 0.5;
                } else {
                  // Bottom 2 -> Engine Node directly
                  pathData = `M 18 ${input.y} C 28 ${input.y}, 28 50, 36 50`;
                  dur = 3 + (i - 3) * 0.5;
                }
                return (
                  <g key={i}>
                    <path d={pathData} fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                    <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                      <animateMotion dur={`${dur}s`} repeatCount="indefinite" rotate="auto" path={pathData} />
                    </image>
                  </g>
                );
              })}

              {/* Settings Node -> Engine Node */}
              <g>
                <path d="M 26 32.5 C 31 32.5, 31 50, 36 50" fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                  <animateMotion dur="2.5s" repeatCount="indefinite" rotate="auto" path="M 26 32.5 C 31 32.5, 31 50, 36 50" />
                </image>
              </g>

              {/* Engine Node -> AI Node */}
              <g>
                <path d="M 44 50 L 59 50" fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                  <animateMotion dur="2s" repeatCount="indefinite" rotate="auto" path="M 44 50 L 59 50" />
                </image>
              </g>

              {/* AI Node -> Output Node */}
              <g>
                <path d="M 69 50 L 77 50" fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                  <animateMotion dur="1.5s" repeatCount="indefinite" rotate="auto" path="M 69 50 L 77 50" />
                </image>
              </g>

              {/* Feedback Loop 1: Control (Top) -> Engine (Top) */}
              <g>
                <path d="M 87 27 L 87 10 L 40 10 L 40 38" fill="none" stroke="#06b6d4" strokeOpacity="0.3" strokeWidth="1" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
                <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                  <animateMotion dur="4s" repeatCount="indefinite" rotate="auto" path="M 87 27 L 87 10 L 40 10 L 40 38" />
                </image>
              </g>

              {/* Feedback Loop 2: Control (Bottom) -> AI (Bottom) */}
              <g>
                <path d="M 87 73 L 87 90 L 64 90 L 64 62" fill="none" stroke="#a855f7" strokeOpacity="0.3" strokeWidth="1" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
                <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                  <animateMotion dur="3s" repeatCount="indefinite" rotate="auto" path="M 87 73 L 87 90 L 64 90 L 64 62" />
                </image>
              </g>
            </svg>

            {/* ── LEFT INPUT NODES ── */}
            {LEFT_INPUTS.map((input, i) => (
              <div 
                key={i} 
                className="absolute flex items-center gap-0 -translate-y-1/2"
                style={{ left: '2%', top: `${input.y}%`, zIndex: 10 }}
              >
                {/* Icon Box */}
                <div className="w-12 h-12 rounded-xl bg-white dark:bg-[#121212] border border-slate-200 dark:border-white/10 flex items-center justify-center shadow-md z-10 relative">
                  <div className="text-slate-500 dark:text-white/70">{input.icon}</div>
                </div>
                {/* Text Pill */}
                <div className="pl-6 pr-4 py-2.5 rounded-r-xl bg-slate-50 dark:bg-[#111] border border-slate-200 dark:border-white/5 border-l-0 text-slate-700 dark:text-white/80 text-xs font-semibold shadow-sm dark:shadow-md -ml-3 z-0 w-[170px]">
                  {input.title}
                </div>
              </div>
            ))}

            {/* ── SETTINGS NODE (Configuration) ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
              style={{ left: '25%', top: '32.5%' }}
            >
              <div className="w-10 h-10 rounded-full bg-white dark:bg-[#111] border border-slate-300 dark:border-white/20 flex items-center justify-center shadow-md dark:shadow-[0_0_15px_rgba(255,255,255,0.05)]">
                <Settings size={18} className="text-slate-400 dark:text-white/60 animate-[spin_8s_linear_infinite]" />
              </div>
            </div>

            {/* ── ENGINE NODE ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
              style={{ left: '40%', top: '50%' }}
            >
              <div className="w-36 h-36 bg-white dark:bg-[#0a0a0a] border border-slate-200 dark:border-white/10 rounded-3xl flex flex-col items-center justify-center shadow-xl dark:shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 to-cyan-600/5 dark:from-blue-600/10 dark:to-cyan-600/10" />
                
                {/* Glowing Progress Ring */}
                <div className="relative w-16 h-16 rounded-full border-[3px] border-blue-100 dark:border-blue-900 flex items-center justify-center mb-3">
                  <div className="absolute inset-0 rounded-full border-[3px] border-blue-500 border-t-transparent animate-spin" style={{ animationDuration: '4s', animationDirection: 'reverse' }} />
                  <Server size={24} className="text-blue-600 dark:text-white dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
                </div>
                
                <span className="text-slate-800 dark:text-white/90 font-bold text-[11px] tracking-wide">Engine</span>
              </div>
            </div>

            {/* ── AI ALGORITHM NODE ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
              style={{ left: '64%', top: '50%' }}
            >
              <div className="w-36 h-36 bg-white dark:bg-[#0a0a0a] border border-slate-200 dark:border-white/10 rounded-3xl flex flex-col items-center justify-center shadow-xl dark:shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-600/5 to-indigo-600/5 dark:from-purple-600/10 dark:to-indigo-600/10" />
                
                {/* Glowing Progress Ring */}
                <div className="relative w-16 h-16 rounded-full border-[3px] border-purple-100 dark:border-purple-900 flex items-center justify-center mb-3">
                  <div className="absolute inset-0 rounded-full border-[3px] border-purple-500 border-t-transparent animate-spin" style={{ animationDuration: '3s' }} />
                  <BrainCircuit size={24} className="text-purple-600 dark:text-white dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
                </div>
                
                <span className="text-slate-800 dark:text-white/90 font-bold text-[11px] tracking-wide">Exoper AI</span>
              </div>
            </div>

            {/* ── RIGHT NODE (OUTPUT & MANAGEMENT) ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-y-1/2 z-20"
              style={{ left: '77%', top: '50%', width: '20%' }}
            >
              <div className="w-full aspect-square bg-slate-50 dark:bg-[#0c0c0c] border border-slate-200 dark:border-white/10 rounded-[2rem] flex flex-col items-center justify-center shadow-xl dark:shadow-2xl relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-200/50 to-transparent dark:from-white/5 dark:to-transparent pointer-events-none" />

                {/* Background Stardust/Particles Effect */}
                <div className="absolute top-[20%] right-[30%] w-1 h-1 bg-slate-400 dark:bg-white/40 rounded-full blur-[1px]" />
                <div className="absolute top-[40%] left-[20%] w-1 h-1 bg-slate-300 dark:bg-white/20 rounded-full" />
                <div className="absolute bottom-[30%] right-[20%] w-1.5 h-1.5 bg-slate-400 dark:bg-white/30 rounded-full blur-[2px]" />

                {/* Internal Scattered Capabilities */}
                {RIGHT_INTERNAL.map((item, i) => (
                  <div 
                    key={i} 
                    className="absolute flex flex-col items-center gap-1.5"
                    style={{ top: item.top, bottom: item.bottom, left: item.left, right: item.right, transform: item.transform }}
                  >
                    <div className="w-8 h-8 rounded-lg bg-white dark:bg-[#1a1a1a] border border-slate-200 dark:border-white/10 flex items-center justify-center shadow-sm dark:shadow-inner">
                      <div className="text-slate-500 dark:text-white/60">{item.icon}</div>
                    </div>
                    <span className="text-[9px] font-bold tracking-wider uppercase text-slate-500 dark:text-white/40">{item.title}</span>
                  </div>
                ))}

                {/* Main Node Content */}
                <ShieldCheck size={32} className="text-slate-800 dark:text-white mb-3 dark:drop-shadow-[0_0_15px_rgba(255,255,255,0.4)]" />
                <span className="text-slate-900 dark:text-white font-bold text-sm tracking-wide text-center">You Stay in Control</span>
              </div>
            </div>

          </div>
        </div>

      </div>

      {/* ── MOBILE LAYOUT (Vertical Top-to-Bottom Pipeline) ── */}
      <div className="w-full max-w-[500px] md:max-w-[900px] mx-auto px-4 block lg:hidden">
        <div className="relative w-full h-[1100px] md:h-[1600px] bg-slate-50 dark:bg-[#080808] rounded-[2rem] border border-slate-200 dark:border-white/10 shadow-xl dark:shadow-2xl overflow-hidden mt-8">
          
          {/* Background Glows */}
          <div className="absolute top-[10%] left-[20%] w-[60%] h-[30%] bg-cyan-600/10 blur-[80px] rounded-full pointer-events-none" />
          <div className="absolute bottom-[20%] left-[20%] w-[60%] h-[30%] bg-purple-600/10 blur-[80px] rounded-full pointer-events-none" />

          {/* SVG Wires & Glowing Packets (Vertical) */}
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
            {/* Top 3 Inputs -> Settings Node */}
            {[8, 18, 28].map((y, i) => {
              const pathDataMobile = i === 1 
                ? `M 50 18 L 75 18` 
                : `M 50 ${y} C 62.5 ${y}, 62.5 18, 75 18`;
                
              const pathDataTablet = i === 1 
                ? `M 35 18 L 75 18` 
                : `M 35 ${y} C 55 ${y}, 55 18, 75 18`;
                
              return (
                <g key={i}>
                  {/* Mobile (Orthogonal) */}
                  <g className="md:hidden">
                    <path d={pathDataMobile} fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                    <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                      <animateMotion dur={`${2 + i * 0.5}s`} repeatCount="indefinite" rotate="auto" path={pathDataMobile} />
                    </image>
                  </g>
                  {/* Tablet (Curved) */}
                  <g className="hidden md:block">
                    <path d={pathDataTablet} fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                    <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                      <animateMotion dur={`${2 + i * 0.5}s`} repeatCount="indefinite" rotate="auto" path={pathDataTablet} />
                    </image>
                  </g>
                </g>
              );
            })}

            {/* Settings Node -> Engine Node (Zero-Crossing Bus Route) */}
            <g>
              <path d="M 75 20 L 75 34 L 65 34 L 65 55 L 50 55 L 50 61" fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
              <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                <animateMotion dur="2.5s" repeatCount="indefinite" rotate="auto" path="M 75 20 L 75 34 L 65 34 L 65 55 L 50 55 L 50 61" />
              </image>
            </g>

            {/* Bottom 2 Inputs -> Engine Node (Merging into the Bus) */}
            {[40, 48].map((y, i) => {
              const pathDataMobile = `M 50 ${y} L 65 ${y} L 65 55 L 50 55 L 50 61`;
              const pathDataTablet = `M 35 ${y} L 65 ${y} L 65 55 L 50 55 L 50 61`;
              return (
                <g key={i}>
                  <g className="md:hidden">
                    <path d={pathDataMobile} fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                    <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                      <animateMotion dur={`${3 + i * 0.5}s`} repeatCount="indefinite" rotate="auto" path={pathDataMobile} />
                    </image>
                  </g>
                  <g className="hidden md:block">
                    <path d={pathDataTablet} fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
                    <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                      <animateMotion dur={`${3 + i * 0.5}s`} repeatCount="indefinite" rotate="auto" path={pathDataTablet} />
                    </image>
                  </g>
                </g>
              );
            })}

            {/* Engine Node -> AI Node */}
            <g>
              <path d="M 50 61 L 50 73" fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
              <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                <animateMotion dur="2s" repeatCount="indefinite" rotate="auto" path="M 50 61 L 50 73" />
              </image>
            </g>

            {/* AI Node -> Output Node */}
            <g>
              <path d="M 50 73 L 50 89" fill="none" strokeWidth="0.5" vectorEffect="non-scaling-stroke" className="stroke-slate-300 dark:stroke-white/15" />
              <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                <animateMotion dur="1.5s" repeatCount="indefinite" rotate="auto" path="M 50 73 L 50 89" />
              </image>
            </g>

            {/* Feedback Loop 1: Control -> Engine */}
            <g>
              <path d="M 90 89 L 95 89 L 95 61 L 55 61" fill="none" stroke="#06b6d4" strokeWidth="1" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" className="opacity-60 dark:opacity-30" />
              <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                <animateMotion dur="4s" repeatCount="indefinite" rotate="auto" path="M 90 89 L 95 89 L 95 61 L 55 61" />
              </image>
            </g>

            {/* Feedback Loop 2: Control -> AI */}
            <g>
              <path d="M 10 89 L 5 89 L 5 73 L 45 73" fill="none" stroke="#a855f7" strokeOpacity="0.3" strokeWidth="1" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
              <image href="/assets/landing/icons/electron.svg" width="4" height="2" x="-2" y="-1">
                <animateMotion dur="3s" repeatCount="indefinite" rotate="auto" path="M 10 89 L 5 89 L 5 73 L 45 73" />
              </image>
            </g>
          </svg>

          {/* ── MOBILE INPUT NODES ── */}
          {LEFT_INPUTS.map((input, i) => {
            const yMap = [8, 18, 28, 40, 48];
            return (
              <div 
                key={i} 
                className="absolute flex items-center gap-0 -translate-y-1/2 w-[45%] md:w-[30%]"
                style={{ left: '5%', top: `${yMap[i]}%`, zIndex: 10 }}
              >
                <div className="w-10 h-10 rounded-xl bg-white dark:bg-[#121212] border border-slate-200 dark:border-white/10 flex items-center justify-center shadow-md dark:shadow-lg z-10 relative flex-shrink-0">
                  <div className="text-slate-500 dark:text-white/70 scale-90">{input.icon}</div>
                </div>
                <div className="pl-4 pr-2 py-1.5 rounded-r-xl bg-slate-50 dark:bg-[#111] border border-slate-200 dark:border-white/5 border-l-0 text-slate-700 dark:text-white/80 text-[10px] font-semibold shadow-sm dark:shadow-md -ml-2 z-0 w-full truncate">
                  <span className="inline">{input.title}</span>
                </div>
              </div>
            );
          })}

          {/* ── MOBILE SETTINGS NODE ── */}
          <div 
            className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
            style={{ left: '75%', top: '18%' }}
          >
            <div className="w-8 h-8 rounded-full bg-white dark:bg-[#111] border border-slate-300 dark:border-white/20 flex items-center justify-center shadow-md dark:shadow-[0_0_15px_rgba(255,255,255,0.05)]">
              <Settings size={14} className="text-slate-400 dark:text-white/60 animate-[spin_8s_linear_infinite]" />
            </div>
          </div>

          {/* ── MOBILE ENGINE NODE ── */}
          <div 
            className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
            style={{ left: '50%', top: '61%' }}
          >
            <div className="w-24 h-24 bg-white dark:bg-[#0a0a0a] border border-slate-200 dark:border-white/10 rounded-2xl flex flex-col items-center justify-center shadow-xl dark:shadow-[0_0_30px_rgba(0,0,0,0.5)] relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 to-cyan-600/5 dark:from-blue-600/10 dark:to-cyan-600/10" />
              <div className="relative w-10 h-10 rounded-full border-2 border-blue-100 dark:border-blue-900 flex items-center justify-center mb-1.5">
                <div className="absolute inset-0 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" style={{ animationDuration: '4s', animationDirection: 'reverse' }} />
                <Server size={16} className="text-blue-600 dark:text-white dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
              </div>
              <span className="text-slate-800 dark:text-white/90 font-bold text-[9px] tracking-wide">Engine</span>
            </div>
          </div>

          {/* ── MOBILE AI ALGORITHM NODE ── */}
          <div 
            className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
            style={{ left: '50%', top: '73%' }}
          >
            <div className="w-24 h-24 md:w-32 md:h-32 bg-white dark:bg-[#0a0a0a] border border-slate-200 dark:border-white/10 rounded-2xl flex flex-col items-center justify-center shadow-xl dark:shadow-[0_0_30px_rgba(0,0,0,0.5)] relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600/5 to-indigo-600/5 dark:from-purple-600/10 dark:to-indigo-600/10" />
              <div className="relative w-14 h-14 rounded-full border-2 border-purple-100 dark:border-purple-900 flex items-center justify-center mb-2">
                <div className="absolute inset-0 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" style={{ animationDuration: '3s' }} />
                <BrainCircuit size={24} className="text-purple-600 dark:text-white dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
              </div>
              <span className="text-slate-800 dark:text-white/90 font-bold text-[11px] tracking-wide">Exoper AI</span>
            </div>
          </div>

          {/* ── MOBILE RIGHT NODE (OUTPUT & MANAGEMENT) ── */}
          <div 
            className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
            style={{ left: '50%', top: '89%', width: '80%' }}
          >
            <div className="w-full h-36 md:h-64 bg-slate-50 dark:bg-[#0c0c0c] border border-slate-200 dark:border-white/10 rounded-2xl flex flex-col items-center justify-center shadow-xl dark:shadow-2xl relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-200/50 to-transparent dark:from-white/5 dark:to-transparent pointer-events-none" />
              
              {/* Internal Scattered Capabilities (Mobile/Tablet) */}
              {[
                { title: 'System', fullTitle: 'Trading System', icon: <Cpu size={14} />, top: '15%', left: '10%' },
                { title: 'Execution', fullTitle: 'Execution', icon: <Zap size={14} />, top: '15%', right: '10%' },
                { title: 'Management', fullTitle: 'Trade Management', icon: <Briefcase size={14} />, bottom: '10%', left: '50%', transform: 'translateX(-50%)' },
              ].map((item, i) => (
                <div 
                  key={i} 
                  className="absolute flex flex-col items-center gap-1 md:gap-2"
                  style={{ top: item.top, bottom: item.bottom, left: item.left, right: item.right, transform: item.transform }}
                >
                  <div className="w-6 h-6 md:w-10 md:h-10 rounded bg-white dark:bg-[#1a1a1a] border border-slate-200 dark:border-white/10 flex items-center justify-center shadow-sm dark:shadow-inner">
                    <div className="text-slate-500 dark:text-white/60 scale-75 md:scale-110">{item.icon}</div>
                  </div>
                  <span className="text-[8px] font-bold tracking-wider uppercase text-slate-400 dark:text-white/40 md:hidden">{item.title}</span>
                  <span className="text-[9px] font-bold tracking-wider uppercase text-slate-400 dark:text-white/40 hidden md:inline whitespace-nowrap">{item.fullTitle}</span>
                </div>
              ))}

              {/* Centered Main Content Shifted Up */}
              <div className="flex flex-col items-center -translate-y-3 md:-translate-y-5 z-10">
                <ShieldCheck size={24} className="text-slate-800 dark:text-white mb-2 md:mb-4 md:w-10 md:h-10 dark:drop-shadow-[0_0_15px_rgba(255,255,255,0.4)]" />
                <span className="text-slate-900 dark:text-white font-bold text-xs md:text-sm tracking-wide text-center">You Stay in Control</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
