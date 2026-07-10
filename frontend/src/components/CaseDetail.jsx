import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, FileText, Send, User, Calendar, CreditCard, ChevronRight, AlertCircle, Bookmark } from 'lucide-react';
import AgentTraceView from './AgentTraceView';

export default function CaseDetail({ review, onAdjudicate, onClose }) {
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [traces, setTraces] = useState([]);
  const [activeTab, setActiveTab] = useState('passes'); // 'passes' or 'sources'

  // Fetch traces for this claim
  useEffect(() => {
    if (review && review.claim_id) {
      fetch(`http://localhost:8000/api/claims/${review.claim_id}/trace`)
        .then(res => {
          if (!res.ok) throw new Error('Failed to fetch execution traces');
          return res.json();
        })
        .then(data => setTraces(data))
        .catch(err => console.error(err));
    }
  }, [review]);

  if (!review) return null;

  const handleAction = async (action) => {
    if (!notes.strip) {
      // Basic strip check
      if (notes.trim() === '') {
        setError('Please enter reviewer notes explaining your adjudication decision.');
        return;
      }
    }
    
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/review-queue/${review.id}/adjudicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, reviewer_notes: notes })
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to adjudicate claim');
      }
      
      onAdjudicate();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const formattedDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <div className="fixed inset-0 bg-brand-dark/80 backdrop-blur-md flex items-center justify-end z-50 transition-all duration-300">
      <div className="w-full max-w-6xl h-full bg-brand-dark/95 border-l border-white/10 shadow-2xl flex flex-col relative overflow-hidden">
        
        {/* Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold bg-brand-accent/20 text-brand-accent px-2.5 py-0.5 rounded-full uppercase">
                RightAction Human-In-the-Loop Queue
              </span>
              <span className="text-xs font-semibold bg-amber-500/20 text-amber-400 px-2.5 py-0.5 rounded-full uppercase">
                Confidence: {Math.round(review.confidence_score * 100)}%
              </span>
            </div>
            <h2 className="text-xl font-bold text-white mt-1">
              Adjudicate Claim {review.claim_number}
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-white px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all cursor-pointer"
          >
            Close Panel
          </button>
        </div>

        {/* Content Body Grid */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Column 1: Claim Structured Data & Description */}
          <div className="space-y-6">
            <div className="glass-panel p-5 rounded-2xl space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-brand-accent text-glow-violet flex items-center gap-1.5">
                <User className="w-4 h-4" /> Claimant Metadata
              </h3>
              
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-brand-textMuted block">Claimant Name</span>
                  <span className="font-medium text-white text-sm">{review.claimant_name}</span>
                </div>
                <div>
                  <span className="text-brand-textMuted block">Incident Date</span>
                  <span className="font-medium text-white text-sm">{formattedDate(review.incident_description ? review.created_at : null) || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-brand-textMuted block">Estimated Loss</span>
                  <span className="font-medium text-brand-danger text-sm">${review.estimated_loss_amount?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-brand-textMuted block">Deductible</span>
                  <span className="font-medium text-white text-sm">${review.estimated_loss_amount ? '500' : '0'}</span>
                </div>
              </div>
            </div>

            <div className="glass-panel p-5 rounded-2xl space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-brand-accent text-glow-violet flex items-center gap-1.5">
                <FileText className="w-4 h-4" /> First Notice of Loss (FNOL)
              </h3>
              <div className="bg-black/30 p-4 rounded-xl border border-white/5">
                <p className="text-sm text-gray-200 leading-relaxed italic">
                  "{review.incident_description}"
                </p>
              </div>
            </div>
          </div>

          {/* Column 2: Agent Timeline & Observability Traces */}
          <div className="glass-panel p-5 rounded-2xl overflow-y-auto max-h-[60vh] lg:max-h-none">
            <AgentTraceView traces={traces} />
          </div>

          {/* Column 3: Trust Layer - Self Consistency & Sources */}
          <div className="glass-panel p-5 rounded-2xl flex flex-col h-[60vh] lg:h-auto overflow-hidden">
            <div className="flex border-b border-white/10 mb-4">
              <button
                onClick={() => setActiveTab('passes')}
                className={`flex-1 pb-3 text-sm font-medium transition-all border-b-2 cursor-pointer ${
                  activeTab === 'passes' 
                    ? 'text-brand-accent border-brand-accent' 
                    : 'text-brand-textMuted border-transparent hover:text-white'
                }`}
              >
                Self-Consistency passes
              </button>
              <button
                onClick={() => setActiveTab('sources')}
                className={`flex-1 pb-3 text-sm font-medium transition-all border-b-2 cursor-pointer ${
                  activeTab === 'sources' 
                    ? 'text-brand-accent border-brand-accent' 
                    : 'text-brand-textMuted border-transparent hover:text-white'
                }`}
              >
                Retrieved Policy Sources
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4">
              {activeTab === 'passes' ? (
                <div className="space-y-4">
                  <div className="p-3 bg-white/5 border border-white/5 rounded-xl text-xs space-y-2">
                    <span className="font-semibold text-brand-accent">Consensus Summary:</span>
                    <p className="text-gray-300 leading-relaxed">{review.agent_reasoning}</p>
                  </div>
                  
                  {/* Retrieved Passes */}
                  {review.retrieved_sources && (
                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-brand-textMuted">Individual Runs Context:</span>
                      <div className="text-[11px] font-mono bg-black/40 p-3 rounded-xl max-h-48 overflow-y-auto space-y-2 text-gray-300">
                        <p className="text-brand-accent font-bold">Consensus Decision Agreement: {Math.round(review.confidence_score * 100)}%</p>
                        <p>Confidence score is based on agreement between two independent runs with different temperatures.</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {review.retrieved_sources && Array.isArray(review.retrieved_sources) ? (
                    review.retrieved_sources
                      .filter(s => s.type === 'unstructured_policy')
                      .map((src, idx) => (
                        <div key={idx} className="p-4 bg-white/5 border border-white/5 rounded-xl space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-brand-accent flex items-center gap-1">
                              <Bookmark className="w-3.5 h-3.5" /> Chunk {idx + 1}
                            </span>
                            <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-gray-300">
                              Dist: {src.distance?.toFixed(4) || 'N/A'}
                            </span>
                          </div>
                          <p className="text-xs font-semibold text-gray-200">{src.name}</p>
                          <p className="text-xs text-brand-textMuted leading-relaxed bg-black/20 p-2 rounded border border-white/5">
                            {src.content}
                          </p>
                        </div>
                      ))
                  ) : (
                    <p className="text-xs text-brand-textMuted">No unstructured sources retrieved.</p>
                  )}
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Adjudication Footer Action Area */}
        <div className="p-6 border-t border-white/10 bg-brand-dark/95 space-y-4">
          {error && (
            <div className="p-3.5 bg-brand-danger/10 border border-brand-danger/20 text-brand-danger text-xs rounded-xl flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 w-full text-left">
              <label className="block text-xs font-bold text-brand-textMuted uppercase mb-1.5">
                Reviewer Adjudication Notes (Mandatory)
              </label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Enter detailed compliance notes and regulatory justification for approving or rejecting this claim..."
                className="w-full h-20 bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-brand-accent/50 focus:ring-1 focus:ring-brand-accent/30 transition-all resize-none"
                disabled={submitting}
              />
            </div>
            
            <div className="flex gap-3 w-full md:w-auto">
              <button
                onClick={() => handleAction('REJECTED')}
                disabled={submitting}
                className="flex-1 md:flex-none px-6 py-3 bg-brand-danger/20 hover:bg-brand-danger/35 text-brand-danger border border-brand-danger/40 rounded-xl font-bold transition-all active:scale-[0.98] flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <ShieldAlert className="w-5 h-5" /> Reject Claim
              </button>
              <button
                onClick={() => handleAction('APPROVED')}
                disabled={submitting}
                className="flex-1 md:flex-none px-6 py-3 bg-brand-success/20 hover:bg-brand-success/35 text-brand-success border border-brand-success/40 rounded-xl font-bold transition-all active:scale-[0.98] flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <ShieldCheck className="w-5 h-5" /> Approve Claim
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
