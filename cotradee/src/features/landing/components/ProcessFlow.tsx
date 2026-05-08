import React from 'react';
import { Network, Key, Sliders, BrainCircuit, ShieldCheck, LineChart, Globe, Zap, Briefcase } from 'lucide-react';

const FLOW_NODES = [
  { id: 1, title: 'Connect Broker/MT5', icon: <Network size={24} />, x: 12, y: 35 },
  { id: 2, title: 'Connect LLM API Key', icon: <Key size={24} />, x: 30, y: 15 },
  { id: 3, title: 'Configure Execution', icon: <Sliders size={24} />, x: 48, y: 35 },
  { id: 4, title: 'AI Algorithm Takes Over', icon: <BrainCircuit size={32} />, x: 70, y: 60, prominent: true },
  { id: 5, title: 'You Stay in Control', icon: <ShieldCheck size={24} />, x: 88, y: 40, badge: 'Human in the Loop' },
];

const CAPABILITIES = [
  { title: 'Technical Analysis', icon: <LineChart size={16} />, x: 16, y: 88 },
  { title: 'Macroeconomic Analysis', icon: <Globe size={16} />, x: 39, y: 88 },
  { title: 'Execution', icon: <Zap size={16} />, x: 61, y: 88 },
  { title: 'Trade Management', icon: <Briefcase size={16} />, x: 84, y: 88 },
];

export default function ProcessFlow() {
  return (
    <section className="relative py-24 border-t border-white/5" id="process-flow">
      <div className="max-w-[1280px] mx-auto px-6 md:px-8">
        
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Process Flow Architecture
          </h2>
          <p className="text-lg opacity-68 leading-relaxed">
            Technical analysis, macroeconomic analysis, execution, and trade management are handled autonomously with you in the loop while the system trades with precision, discipline, and confidence.
          </p>
        </div>

        {/* ── DESKTOP LAYOUT (Curved Path) ───────────────────────────────── */}
        <div className="hidden lg:block relative w-full h-[600px] bg-[#050505] rounded-[2rem] border border-white/10 overflow-hidden shadow-2xl">
          
          {/* Subtle Background Glows */}
          <div className="absolute top-[-10%] left-[20%] w-[40%] h-[50%] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none" />
          <div className="absolute bottom-[-10%] right-[20%] w-[40%] h-[50%] bg-purple-600/10 blur-[100px] rounded-full pointer-events-none" />
          <div className="absolute top-[40%] left-[60%] w-[30%] h-[40%] bg-cyan-600/10 blur-[100px] rounded-full pointer-events-none" />

          {/* SVG Connections */}
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
            <defs>
              <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.4" />
                <stop offset="50%" stopColor="#8b5cf6" stopOpacity="1" />
                <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.6" />
              </linearGradient>
            </defs>
            
            {/* Main curved path between nodes */}
            <path 
              d="M 12 35 C 20 35, 20 15, 30 15 C 40 15, 40 35, 48 35 C 58 35, 60 60, 70 60 C 80 60, 80 40, 88 40" 
              fill="none" 
              stroke="url(#flowGradient)" 
              strokeWidth="2" 
              vectorEffect="non-scaling-stroke"
              strokeDasharray="6 6" 
              className="opacity-70"
            />

            {/* Dotted lines from capabilities to AI Node (Node 4: 70, 60) */}
            {CAPABILITIES.map((cap, i) => (
              <path 
                key={i}
                d={`M ${cap.x} ${cap.y - 4} Q ${cap.x} 60, 68 60`} 
                fill="none" 
                stroke="#8b5cf6" 
                strokeOpacity="0.4"
                strokeWidth="1.5" 
                vectorEffect="non-scaling-stroke"
                strokeDasharray="4 4" 
              />
            ))}
          </svg>

          {/* Render Flow Nodes */}
          {FLOW_NODES.map((node) => (
            <div 
              key={node.id}
              className="absolute flex flex-col items-center justify-center -translate-x-1/2 -translate-y-1/2 group"
              style={{ left: `${node.x}%`, top: `${node.y}%`, zIndex: 10 }}
            >
              <div className={`
                relative flex items-center justify-center rounded-full border backdrop-blur-sm
                ${node.prominent 
                  ? 'w-28 h-28 bg-gradient-to-br from-indigo-900 to-purple-900 border-indigo-500 shadow-[0_0_40px_rgba(79,70,229,0.4)] z-20' 
                  : 'w-16 h-16 bg-[#111]/80 border-white/20 group-hover:border-indigo-400 group-hover:shadow-[0_0_20px_rgba(79,70,229,0.2)]'}
                transition-all duration-500
              `}>
                <div className={`text-white ${node.prominent ? 'scale-125 text-indigo-200' : 'opacity-80 group-hover:opacity-100 group-hover:text-indigo-300'} transition-colors`}>
                  {node.icon}
                </div>
                
                {node.badge && (
                  <div className="absolute -top-4 whitespace-nowrap bg-cyan-950 border border-cyan-500/50 text-cyan-300 text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                    {node.badge}
                  </div>
                )}
              </div>

              <div className="mt-4 text-center">
                <div className={`font-bold tracking-tight whitespace-nowrap ${node.prominent ? 'text-lg text-white' : 'text-sm text-white/80'}`}>
                  {node.id}. {node.title}
                </div>
              </div>
            </div>
          ))}

          {/* Render Capability Boxes */}
          {CAPABILITIES.map((cap, i) => (
            <div 
              key={i}
              className="absolute flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-[#111]/90 border border-white/10 backdrop-blur-md -translate-x-1/2 -translate-y-1/2 hover:border-purple-500/50 hover:bg-[#1a1a1a] transition-all cursor-default"
              style={{ left: `${cap.x}%`, top: `${cap.y}%`, zIndex: 5 }}
            >
              <div className="text-purple-400">{cap.icon}</div>
              <span className="text-xs font-semibold text-white/80 whitespace-nowrap">{cap.title}</span>
            </div>
          ))}
        </div>

        {/* ── MOBILE / TABLET LAYOUT (Vertical Timeline) ──────────────────── */}
        <div className="lg:hidden flex flex-col gap-6 relative bg-[#050505] rounded-3xl border border-white/10 p-6 sm:p-10 overflow-hidden">
          {/* Subtle Background Glows */}
          <div className="absolute top-0 right-0 w-[80%] h-[50%] bg-indigo-600/10 blur-[80px] rounded-full pointer-events-none" />
          
          <div className="absolute left-[39px] sm:left-[55px] top-[40px] bottom-[40px] w-px bg-gradient-to-b from-indigo-500/20 via-purple-500/50 to-cyan-500/20" />

          {FLOW_NODES.map((node) => (
            <div key={node.id} className="relative flex items-start gap-6">
              <div className={`
                relative flex-shrink-0 flex items-center justify-center rounded-full border backdrop-blur-sm z-10 mt-1
                ${node.prominent 
                  ? 'w-16 h-16 bg-gradient-to-br from-indigo-900 to-purple-900 border-indigo-500 shadow-[0_0_30px_rgba(79,70,229,0.3)]' 
                  : 'w-12 h-12 bg-[#111] border-white/20'}
              `}>
                <div className={`text-white ${node.prominent ? 'text-indigo-200' : 'opacity-80'}`}>
                  {node.icon}
                </div>
              </div>

              <div className="flex flex-col pt-2 sm:pt-3">
                {node.badge && (
                  <span className="inline-block w-fit mb-2 bg-cyan-950 border border-cyan-500/50 text-cyan-300 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                    {node.badge}
                  </span>
                )}
                <h3 className={`font-bold tracking-tight ${node.prominent ? 'text-lg text-white' : 'text-base text-white/90'}`}>
                  {node.id}. {node.title}
                </h3>
              </div>
            </div>
          ))}

          <div className="mt-8 pt-8 border-t border-white/10">
            <h4 className="text-xs font-bold uppercase tracking-widest text-center text-white/50 mb-6">Autonomous Capabilities</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {CAPABILITIES.map((cap, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[#111]/80 border border-white/10">
                  <div className="text-purple-400">{cap.icon}</div>
                  <span className="text-sm font-semibold text-white/80">{cap.title}</span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </section>
  );
}
