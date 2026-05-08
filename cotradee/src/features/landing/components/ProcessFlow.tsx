import React from 'react';
import { Network, Key, Sliders, BrainCircuit, ShieldCheck, LineChart, Globe, Zap, Briefcase, Cpu } from 'lucide-react';

const LEFT_INPUTS = [
  { title: 'Connect Broker/MT5', icon: <Network size={20} />, y: 15 },
  { title: 'Connect LLM API Key', icon: <Key size={20} />, y: 32.5 },
  { title: 'Configure Execution', icon: <Sliders size={20} />, y: 50 },
  { title: 'Technical Analysis', icon: <LineChart size={20} />, y: 67.5 },
  { title: 'Macroeconomic Analysis', icon: <Globe size={20} />, y: 85 },
];

const RIGHT_INTERNAL = [
  { title: 'Trading System', icon: <Cpu size={14} />, top: '15%', left: '12%' },
  { title: 'Execution', icon: <Zap size={14} />, top: '15%', right: '12%' },
  { title: 'Trade Management', icon: <Briefcase size={14} />, bottom: '12%', left: '50%', transform: 'translateX(-50%)' },
];

export default function ProcessFlow() {
  return (
    <section className="relative py-24 border-t border-white/5" id="process-flow">
      <div className="max-w-[1280px] mx-auto px-6 md:px-8">
        
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-lg opacity-68 leading-relaxed">
            Technical analysis, macroeconomic analysis, execution, and trade management are handled autonomously with you in the loop while the system trades with precision, discipline, and confidence.
          </p>
        </div>

        {/* ── SCROLLABLE WRAPPER FOR ALL DEVICES ── */}
        <div className="w-full overflow-x-auto pb-8 hide-scrollbar">
          <div className="relative min-w-[1024px] h-[600px] bg-[#080808] rounded-[2rem] border border-white/10 shadow-2xl overflow-hidden mx-auto">
            
            {/* Background Glows */}
            <div className="absolute top-[20%] left-[40%] w-[30%] h-[60%] bg-purple-600/10 blur-[120px] rounded-full pointer-events-none" />
            <div className="absolute top-[10%] left-[10%] w-[20%] h-[40%] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none" />

            {/* SVG Wires & Glowing Packets */}
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
              {/* Left to Center Lines */}
              {LEFT_INPUTS.map((input, i) => {
                const pathData = `M 24 ${input.y} C 36 ${input.y}, 36 50, 43 50`;
                return (
                  <g key={i}>
                    {/* Base wire */}
                    <path d={pathData} fill="none" stroke="#ffffff" strokeOpacity="0.15" strokeWidth="0.5" vectorEffect="non-scaling-stroke" />
                    {/* Animated glowing packet */}
                    <path d={pathData} fill="none" stroke="#d946ef" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeDasharray="10 1000" strokeLinecap="round" className="opacity-90 drop-shadow-[0_0_8px_rgba(217,70,239,1)]">
                      <animate attributeName="stroke-dashoffset" from="1000" to="0" dur={`${3 + i * 0.5}s`} repeatCount="indefinite" />
                    </path>
                  </g>
                );
              })}

              {/* Center to Right Line */}
              <g>
                <path d="M 57 50 L 73 50" fill="none" stroke="#ffffff" strokeOpacity="0.15" strokeWidth="0.5" vectorEffect="non-scaling-stroke" />
                <path d="M 57 50 L 73 50" fill="none" stroke="#d946ef" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeDasharray="10 1000" strokeLinecap="round" className="opacity-90 drop-shadow-[0_0_8px_rgba(217,70,239,1)]">
                  <animate attributeName="stroke-dashoffset" from="1000" to="0" dur="2s" repeatCount="indefinite" />
                </path>
              </g>
            </svg>

            {/* ── LEFT INPUT NODES ── */}
            {LEFT_INPUTS.map((input, i) => (
              <div 
                key={i} 
                className="absolute flex items-center gap-0 -translate-y-1/2"
                style={{ left: '4%', top: `${input.y}%`, zIndex: 10 }}
              >
                {/* Icon Box */}
                <div className="w-12 h-12 rounded-xl bg-[#121212] border border-white/10 flex items-center justify-center shadow-lg z-10 relative">
                  <div className="text-white/70">{input.icon}</div>
                </div>
                {/* Text Pill */}
                <div className="pl-6 pr-4 py-2.5 rounded-r-xl bg-[#111] border border-white/5 border-l-0 text-white/80 text-xs font-semibold shadow-md -ml-3 z-0">
                  {input.title}
                </div>
              </div>
            ))}

            {/* ── CENTER NODE (AI ALGORITHM) ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
              style={{ left: '50%', top: '50%' }}
            >
              <div className="w-36 h-36 bg-[#0a0a0a] border border-white/10 rounded-3xl flex flex-col items-center justify-center shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-indigo-600/10" />
                
                {/* Glowing Progress Ring */}
                <div className="relative w-16 h-16 rounded-full border-[3px] border-purple-900 flex items-center justify-center mb-3">
                  <div className="absolute inset-0 rounded-full border-[3px] border-purple-500 border-t-transparent animate-spin" style={{ animationDuration: '3s' }} />
                  <BrainCircuit size={24} className="text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
                </div>
                
                <span className="text-white/90 font-bold text-[11px] tracking-wide">AI Algorithm</span>
              </div>
            </div>

            {/* ── RIGHT NODE (OUTPUT & MANAGEMENT) ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-y-1/2 z-20"
              style={{ left: '73%', top: '50%', width: '23%' }}
            >
              <div className="w-full aspect-square bg-[#0c0c0c] border border-white/10 rounded-[2rem] flex flex-col items-center justify-center shadow-2xl relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent pointer-events-none" />

                {/* Background Stardust/Particles Effect */}
                <div className="absolute top-[20%] right-[30%] w-1 h-1 bg-white/40 rounded-full blur-[1px]" />
                <div className="absolute top-[40%] left-[20%] w-1 h-1 bg-white/20 rounded-full" />
                <div className="absolute bottom-[30%] right-[20%] w-1.5 h-1.5 bg-white/30 rounded-full blur-[2px]" />

                {/* Internal Scattered Capabilities */}
                {RIGHT_INTERNAL.map((item, i) => (
                  <div 
                    key={i} 
                    className="absolute flex flex-col items-center gap-1.5"
                    style={{ top: item.top, bottom: item.bottom, left: item.left, right: item.right, transform: item.transform }}
                  >
                    <div className="w-8 h-8 rounded-lg bg-[#1a1a1a] border border-white/10 flex items-center justify-center shadow-inner">
                      <div className="text-white/60">{item.icon}</div>
                    </div>
                    <span className="text-[9px] font-bold tracking-wider uppercase text-white/40">{item.title}</span>
                  </div>
                ))}

                {/* Main Node Content */}
                <ShieldCheck size={32} className="text-white mb-3 drop-shadow-[0_0_15px_rgba(255,255,255,0.4)]" />
                <span className="text-white font-bold text-sm tracking-wide">You Stay in Control</span>
              </div>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
}
