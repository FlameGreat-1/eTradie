import React from 'react';
import { Network, Key, Sliders, BrainCircuit, ShieldCheck, LineChart, Globe, Zap, Briefcase, Cpu, Settings, Server } from 'lucide-react';

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
          <div className="relative min-w-[1400px] h-[600px] bg-[#080808] rounded-[2rem] border border-white/10 shadow-2xl overflow-hidden mx-auto">
            
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
                    <path d={pathData} fill="none" stroke="#ffffff" strokeOpacity="0.15" strokeWidth="0.5" vectorEffect="non-scaling-stroke" />
                    <path d={pathData} fill="none" stroke={strokeColor} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeDasharray="10 1000" strokeLinecap="round" className="opacity-90" style={{ filter: `drop-shadow(0 0 8px ${strokeColor})` }}>
                      <animate attributeName="stroke-dashoffset" from="1000" to="0" dur={`${dur}s`} repeatCount="indefinite" />
                    </path>
                  </g>
                );
              })}

              {/* Settings Node -> Engine Node */}
              <g>
                <path d="M 26 32.5 C 31 32.5, 31 50, 36 50" fill="none" stroke="#ffffff" strokeOpacity="0.15" strokeWidth="0.5" vectorEffect="non-scaling-stroke" />
                <path d="M 26 32.5 C 31 32.5, 31 50, 36 50" fill="none" stroke="#06b6d4" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeDasharray="10 1000" strokeLinecap="round" className="opacity-90" style={{ filter: `drop-shadow(0 0 8px #06b6d4)` }}>
                  <animate attributeName="stroke-dashoffset" from="1000" to="0" dur="2.5s" repeatCount="indefinite" />
                </path>
              </g>

              {/* Engine Node -> AI Node */}
              <g>
                <path d="M 44 50 L 59 50" fill="none" stroke="#ffffff" strokeOpacity="0.15" strokeWidth="0.5" vectorEffect="non-scaling-stroke" />
                <path d="M 44 50 L 59 50" fill="none" stroke="#a855f7" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeDasharray="10 1000" strokeLinecap="round" className="opacity-90" style={{ filter: `drop-shadow(0 0 8px #a855f7)` }}>
                  <animate attributeName="stroke-dashoffset" from="1000" to="0" dur="2s" repeatCount="indefinite" />
                </path>
              </g>

              {/* AI Node -> Output Node */}
              <g>
                <path d="M 69 50 L 77 50" fill="none" stroke="#ffffff" strokeOpacity="0.15" strokeWidth="0.5" vectorEffect="non-scaling-stroke" />
                <path d="M 69 50 L 77 50" fill="none" stroke="#d946ef" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeDasharray="10 1000" strokeLinecap="round" className="opacity-90" style={{ filter: `drop-shadow(0 0 8px #d946ef)` }}>
                  <animate attributeName="stroke-dashoffset" from="1000" to="0" dur="1.5s" repeatCount="indefinite" />
                </path>
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
                <div className="w-12 h-12 rounded-xl bg-[#121212] border border-white/10 flex items-center justify-center shadow-lg z-10 relative">
                  <div className="text-white/70">{input.icon}</div>
                </div>
                {/* Text Pill */}
                <div className="pl-6 pr-4 py-2.5 rounded-r-xl bg-[#111] border border-white/5 border-l-0 text-white/80 text-xs font-semibold shadow-md -ml-3 z-0 w-[170px]">
                  {input.title}
                </div>
              </div>
            ))}

            {/* ── SETTINGS NODE (Configuration) ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
              style={{ left: '25%', top: '32.5%' }}
            >
              <div className="w-10 h-10 rounded-full bg-[#111] border border-white/20 flex items-center justify-center shadow-[0_0_15px_rgba(255,255,255,0.05)]">
                <Settings size={18} className="text-white/60 animate-[spin_8s_linear_infinite]" />
              </div>
            </div>

            {/* ── ENGINE NODE ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
              style={{ left: '40%', top: '50%' }}
            >
              <div className="w-36 h-36 bg-[#0a0a0a] border border-white/10 rounded-3xl flex flex-col items-center justify-center shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-cyan-600/10" />
                
                {/* Glowing Progress Ring */}
                <div className="relative w-16 h-16 rounded-full border-[3px] border-blue-900 flex items-center justify-center mb-3">
                  <div className="absolute inset-0 rounded-full border-[3px] border-blue-500 border-t-transparent animate-spin" style={{ animationDuration: '4s', animationDirection: 'reverse' }} />
                  <Server size={24} className="text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
                </div>
                
                <span className="text-white/90 font-bold text-[11px] tracking-wide">Engine</span>
              </div>
            </div>

            {/* ── AI ALGORITHM NODE ── */}
            <div 
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 z-20"
              style={{ left: '64%', top: '50%' }}
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
              style={{ left: '77%', top: '50%', width: '20%' }}
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
                <span className="text-white font-bold text-sm tracking-wide text-center">You Stay in Control</span>
              </div>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
}
