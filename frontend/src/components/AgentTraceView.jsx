import React, { useState } from 'react';
import { Play, Database, Search, Cpu, CheckCircle, HelpCircle, Activity, UserCheck } from 'lucide-react';

const nodeIcons = {
  intake: <Play className="w-4.5 h-4.5 text-blue-400" />,
  retrieve_structured: <Database className="w-4.5 h-4.5 text-indigo-400" />,
  retrieve_unstructured: <Search className="w-4.5 h-4.5 text-purple-400" />,
  reasoning: <Cpu className="w-4.5 h-4.5 text-pink-400" />,
  decision: <CheckCircle className="w-4.5 h-4.5 text-emerald-400" />,
  human_reviewer: <UserCheck className="w-4.5 h-4.5 text-amber-400" />
};

export default function AgentTraceView({ traces }) {
  const [expandedTrace, setExpandedTrace] = useState(null);

  if (!traces || traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-brand-textMuted glass-panel rounded-xl">
        <Activity className="w-8 h-8 mb-2 animate-pulse text-brand-accent/40" />
        <p className="text-sm">No agent traces logged yet. Process the claim to view routing timeline.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-brand-accent text-glow-violet">
        Foundry Engine Node Timeline
      </h3>
      <div className="relative pl-6 border-l border-white/10 space-y-6">
        {traces.map((trace, idx) => {
          const isExpanded = expandedTrace === trace.id;
          const nodeNamePretty = trace.node_name.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
          
          return (
            <div key={trace.id} className="relative group">
              {/* Timeline dot */}
              <div className="absolute -left-[35px] top-1 w-7.5 h-7.5 rounded-full bg-brand-dark flex items-center justify-center border border-white/10 group-hover:border-brand-accent/50 transition-all">
                {nodeIcons[trace.node_name] || <HelpCircle className="w-4 h-4 text-gray-400" />}
              </div>

              {/* Card content */}
              <div className="glass-panel p-4 rounded-xl transition-all hover:bg-white/[0.02]">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <h4 className="font-medium text-white text-sm">{nodeNamePretty}</h4>
                    <p className="text-xs text-brand-textMuted">
                      {trace.latency_ms > 0 ? `Latency: ${trace.latency_ms}ms` : 'Instant'} 
                      {trace.confidence !== null && ` | Confidence: ${Math.round(trace.confidence * 100)}%`}
                    </p>
                  </div>
                  <button
                    onClick={() => setExpandedTrace(isExpanded ? null : trace.id)}
                    className="text-xs text-brand-accent hover:text-brand-accentHover font-medium underline cursor-pointer"
                  >
                    {isExpanded ? 'Hide Details' : 'View Payload'}
                  </button>
                </div>

                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-white/5 space-y-2 text-left">
                    {trace.input_state && (
                      <div>
                        <span className="text-[10px] uppercase font-bold text-brand-textMuted">Input State:</span>
                        <pre className="text-[11px] font-mono bg-black/30 p-2 rounded-lg text-gray-300 max-h-40 overflow-y-auto whitespace-pre-wrap">
                          {JSON.stringify(trace.input_state, null, 2)}
                        </pre>
                      </div>
                    )}
                    {trace.output_state && (
                      <div>
                        <span className="text-[10px] uppercase font-bold text-brand-textMuted">Output State:</span>
                        <pre className="text-[11px] font-mono bg-black/30 p-2 rounded-lg text-gray-300 max-h-40 overflow-y-auto whitespace-pre-wrap">
                          {JSON.stringify(trace.output_state, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
