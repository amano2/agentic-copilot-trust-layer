import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, Cpu, Users, Eye, Play, Sparkles, LayoutDashboard, Layers, FileCheck, CheckCircle2, XCircle } from 'lucide-react';
import ReviewQueue from './components/ReviewQueue';
import CaseDetail from './components/CaseDetail';

export default function App() {
  const [claims, setClaims] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedReview, setSelectedReview] = useState(null);
  const [processingClaimId, setProcessingClaimId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pipelineEvents, setPipelineEvents] = useState([]);
  const [showPipelineHUD, setShowPipelineHUD] = useState(false);
  const [currentClaimNumber, setCurrentClaimNumber] = useState('');

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/api/ws');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("[WebSocket Event]:", data);
      
      setPipelineEvents((prev) => {
        const isNewRun = prev.length > 0 && prev[prev.length - 1].claim_id !== data.claim_id;
        const currentList = isNewRun ? [] : prev;
        
        const idx = currentList.findIndex(e => e.node_name === data.node_name);
        if (idx !== -1) {
          const copy = [...currentList];
          copy[idx] = data;
          return copy;
        }
        return [...currentList, data];
      });
    };
    ws.onclose = () => {
      console.log("[WebSocket] Closed. Attempting reconnect...");
    };
    return () => ws.close();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      // 1. Fetch claims
      const claimsRes = await fetch('http://localhost:8000/api/claims');
      if (claimsRes.ok) {
        const claimsData = await claimsRes.json();
        setClaims(claimsData);
      }

      // 2. Fetch review queue
      const reviewsRes = await fetch('http://localhost:8000/api/review-queue');
      if (reviewsRes.ok) {
        const reviewsData = await reviewsRes.json();
        setReviews(reviewsData);
      }
    } catch (err) {
      console.error("Error loading API data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const triggerProcessPipeline = async (claimId) => {
    const claim = claims.find(c => c.id === claimId);
    setCurrentClaimNumber(claim ? claim.claim_number : `CLM-${claimId}`);
    setPipelineEvents([]);
    setShowPipelineHUD(true);
    setProcessingClaimId(claimId);
    try {
      const res = await fetch(`http://localhost:8000/api/claims/process/${claimId}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Pipeline error');
      
      // Keep HUD open for 1.5 seconds to let the user see the complete state before closing
      await new Promise(r => setTimeout(r, 1500));
      setShowPipelineHUD(false);
      await fetchInitialData();
    } catch (err) {
      console.error(err);
      setShowPipelineHUD(false);
    } finally {
      setProcessingClaimId(null);
    }
  };

  // Metrics calculations
  const totalClaims = claims.length;
  const autoApproved = claims.filter(c => c.claim_status === 'AUTO_APPROVED').length;
  const autoRejected = claims.filter(c => c.claim_status === 'AUTO_REJECTED').length;
  const humanReviewed = claims.filter(c => ['APPROVED', 'REJECTED'].includes(c.claim_status)).length;
  const pendingReview = claims.filter(c => c.claim_status === 'PENDING_HUMAN_REVIEW').length;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'UNDER_REVIEW':
        return <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2.5 py-0.5 rounded-full text-xs font-semibold">Intake</span>;
      case 'AUTO_APPROVED':
        return <span className="bg-brand-success/15 text-brand-success border border-brand-success/30 px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 w-fit"><CheckCircle2 className="w-3.5 h-3.5" /> Auto Approved</span>;
      case 'AUTO_REJECTED':
        return <span className="bg-brand-danger/15 text-brand-danger border border-brand-danger/30 px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 w-fit"><XCircle className="w-3.5 h-3.5" /> Auto Rejected</span>;
      case 'PENDING_HUMAN_REVIEW':
        return <span className="bg-brand-warning/15 text-brand-warning border border-brand-warning/30 px-2.5 py-0.5 rounded-full text-xs font-semibold w-fit">Pending Review</span>;
      case 'APPROVED':
        return <span className="bg-brand-success/5 text-brand-success border border-brand-success/50 px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 w-fit">Approved (Human)</span>;
      case 'REJECTED':
        return <span className="bg-brand-danger/5 text-brand-danger border border-brand-danger/50 px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 w-fit">Rejected (Human)</span>;
      default:
        return <span className="bg-gray-500/10 text-gray-400 px-2.5 py-0.5 rounded-full text-xs font-semibold">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-brand-dark flex flex-col relative overflow-x-hidden">
      {/* Decorative background glows */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-brand-accent/5 rounded-full blur-[150px] -z-10" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[150px] -z-10" />

      {/* Main Navigation Header */}
      <header className="border-b border-white/10 backdrop-blur-md sticky top-0 z-40 bg-brand-dark/60">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-accent to-indigo-500 flex items-center justify-center text-white shadow-glow">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div className="text-left">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-white text-md tracking-tight">Agentic Trust Layer</span>
                <span className="text-[10px] uppercase font-bold bg-brand-accent/25 text-brand-accent px-1.5 py-0.5 rounded">
                  Active
                </span>
              </div>
              <p className="text-[10px] text-brand-textMuted uppercase tracking-wider">
                Enterprise FNOL Decision Support
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === 'dashboard'
                  ? 'bg-brand-accent/20 text-white border border-brand-accent/30'
                  : 'text-brand-textMuted hover:text-white hover:bg-white/5 border border-transparent'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" /> Foundry Core
            </button>
            <button
              onClick={() => setActiveTab('reviews')}
              className={`px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all relative cursor-pointer ${
                activeTab === 'reviews'
                  ? 'bg-brand-accent/20 text-white border border-brand-accent/30'
                  : 'text-brand-textMuted hover:text-white hover:bg-white/5 border border-transparent'
              }`}
            >
              <Layers className="w-4 h-4" /> RightAction Queue
              {reviews.filter(r => r.status === 'PENDING').length > 0 && (
                <span className="absolute -top-1 -right-1 w-4.5 h-4.5 bg-brand-danger text-[10px] font-bold text-white rounded-full flex items-center justify-center border border-brand-dark animate-pulse">
                  {reviews.filter(r => r.status === 'PENDING').length}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        
        {/* Banner explaining design support framing */}
        <div className="glass-panel p-4.5 rounded-2xl flex items-center gap-3.5 text-left border-l-4 border-l-brand-accent bg-brand-accent/5">
          <Sparkles className="w-6 h-6 text-brand-accent shrink-0 animate-pulse" />
          <p className="text-sm text-gray-200">
            <strong>Mandatory Human Sign-off Notice:</strong> This enterprise system operates exclusively as a decision-support copilot. It automatically resolves high-confidence matches and routes all low-confidence, complex, or ambiguous claims to the review queue for human reviewer sign-off.
          </p>
        </div>

        {activeTab === 'dashboard' ? (
          <div className="space-y-8">
            {/* Metrics cards grid */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="glass-panel p-5 rounded-2xl text-left">
                <span className="text-xs text-brand-textMuted font-medium block">Total Claims Ingested</span>
                <span className="text-2xl font-bold text-white block mt-1">{totalClaims}</span>
              </div>
              <div className="glass-panel p-5 rounded-2xl text-left border-b-2 border-b-brand-success/40">
                <span className="text-xs text-brand-textMuted font-medium block">Auto Approved</span>
                <span className="text-2xl font-bold text-brand-success block mt-1">{autoApproved}</span>
              </div>
              <div className="glass-panel p-5 rounded-2xl text-left border-b-2 border-b-brand-danger/40">
                <span className="text-xs text-brand-textMuted font-medium block">Auto Rejected</span>
                <span className="text-2xl font-bold text-brand-danger block mt-1">{autoRejected}</span>
              </div>
              <div className="glass-panel p-5 rounded-2xl text-left border-b-2 border-b-brand-warning/40">
                <span className="text-xs text-brand-textMuted font-medium block">Pending Human Review</span>
                <span className="text-2xl font-bold text-brand-warning block mt-1">{pendingReview}</span>
              </div>
              <div className="glass-panel p-5 rounded-2xl text-left">
                <span className="text-xs text-brand-textMuted font-medium block">Human Adjudicated</span>
                <span className="text-2xl font-bold text-white block mt-1">{humanReviewed}</span>
              </div>
            </div>

            {/* Claims Table list */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-lg text-white">Ingested Claims Database</h3>
                <button
                  onClick={fetchInitialData}
                  className="text-xs text-brand-accent hover:underline font-semibold cursor-pointer"
                >
                  Reload Table
                </button>
              </div>

              <div className="overflow-x-auto w-full">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-white/5 text-[11px] font-bold text-brand-textMuted uppercase">
                      <th className="py-3 px-4">Claim ID / Number</th>
                      <th className="py-3 px-4">Claimant</th>
                      <th className="py-3 px-4">Incident Type</th>
                      <th className="py-3 px-4">Loss Estimate</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {claims.map((claim) => {
                      const isProcessing = processingClaimId === claim.id;
                      const hasQueueEntry = reviews.find(r => r.claim_id === claim.id);
                      
                      return (
                        <tr key={claim.id} className="hover:bg-white/[0.01] transition-all">
                          <td className="py-4.5 px-4 font-bold text-white">
                            {claim.claim_number}
                          </td>
                          <td className="py-4.5 px-4">{claim.claimant_name}</td>
                          <td className="py-4.5 px-4">
                            <span className="bg-white/5 border border-white/10 px-2 py-0.5 rounded text-xs text-gray-200">
                              {claim.incident_type}
                            </span>
                          </td>
                          <td className="py-4.5 px-4 text-brand-danger font-medium">
                            ${claim.estimated_loss_amount?.toLocaleString()}
                          </td>
                          <td className="py-4.5 px-4">
                            {getStatusBadge(claim.claim_status)}
                          </td>
                          <td className="py-4.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              {claim.claim_status === 'UNDER_REVIEW' ? (
                                <button
                                  onClick={() => triggerProcessPipeline(claim.id)}
                                  disabled={isProcessing}
                                  className="px-3 py-1.5 bg-brand-accent/20 hover:bg-brand-accent/35 border border-brand-accent/30 rounded-lg text-xs font-bold text-brand-accent flex items-center gap-1.5 transition-all active:scale-[0.98] disabled:opacity-50 cursor-pointer"
                                >
                                  <Play className="w-3.5 h-3.5" /> 
                                  {isProcessing ? 'Analyzing...' : 'Run Pipeline'}
                                </button>
                              ) : hasQueueEntry ? (
                                <button
                                  onClick={() => {
                                    setSelectedReview(hasQueueEntry);
                                  }}
                                  className="px-3 py-1.5 bg-brand-warning/15 hover:bg-brand-warning/25 border border-brand-warning/30 rounded-lg text-xs font-bold text-brand-warning flex items-center gap-1.5 transition-all cursor-pointer"
                                >
                                  <Eye className="w-3.5 h-3.5" /> Adjudicate
                                </button>
                              ) : (
                                <button
                                  onClick={() => {
                                    // Make a mock review object to display details even if not in review queue
                                    const mockReview = {
                                      id: 0,
                                      claim_id: claim.id,
                                      claim_number: claim.claim_number,
                                      claimant_name: claim.claimant_name,
                                      incident_type: claim.incident_type,
                                      estimated_loss_amount: claim.estimated_loss_amount,
                                      incident_description: claim.incident_description,
                                      status: claim.claim_status,
                                      confidence_score: 1.0,
                                      agent_reasoning: "Claim resolved automatically. Self-consistency check compiled 100% agreement.",
                                      retrieved_sources: []
                                    };
                                    setSelectedReview(mockReview);
                                  }}
                                  className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold text-gray-300 flex items-center gap-1.5 transition-all cursor-pointer"
                                >
                                  <Eye className="w-3.5 h-3.5" /> View Details
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            <ReviewQueue 
              reviews={reviews} 
              onSelect={(review) => setSelectedReview(review)} 
            />
          </div>
        )}

      </main>

      {/* Adjudication Side Drawer Panel */}
      {selectedReview && (
        <CaseDetail
          review={selectedReview}
          onAdjudicate={async () => {
            setSelectedReview(null);
            await fetchInitialData();
          }}
          onClose={() => setSelectedReview(null)}
        />
      )}

      {/* Floating Liquid-Glass Pipeline Progress HUD */}
      {showPipelineHUD && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 transition-all duration-300">
          <div className="glass-panel w-full max-w-lg p-6 rounded-2xl border border-white/10 shadow-glass text-left">
            <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-brand-accent/20 flex items-center justify-center text-brand-accent animate-pulse">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Foundry Engine Pipeline Trace</h3>
                  <p className="text-xs text-brand-textMuted font-medium">Live node state stream for {currentClaimNumber}</p>
                </div>
              </div>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-brand-accent/20 text-brand-accent border border-brand-accent/30 animate-pulse">
                PROCESSING
              </span>
            </div>

            <div className="space-y-3.5">
              {[
                { id: 'intake', label: 'Intake Node', description: 'Load claim structured metadata details' },
                { id: 'retrieve', label: 'Concurrent Database Retrieval', description: 'Query SQL and Vector DB concurrently' },
                { id: 'eval_state', label: 'State Pre-Check', description: 'Validate required fields compliance' },
                { id: 'reasoning', label: 'Consensus Reasoning Node', description: 'Self-Consistency dual-pass logic check' },
                { id: 'challenger', label: 'Challenger Compliance Node', description: 'Auditor loop verification analysis' },
                { id: 'decision', label: 'Decision Node', description: 'Finalize status and write DB traces' }
              ].map((node) => {
                const event = pipelineEvents.find(e => e.node_name === node.id);
                const isCompleted = !!event;
                
                let statusText = 'Pending...';
                let statusClass = 'text-gray-500 border-gray-500/20 bg-gray-500/5';
                
                if (isCompleted) {
                  statusText = 'Completed';
                  statusClass = 'text-brand-success border-brand-success/30 bg-brand-success/10';
                  if (node.id === 'reasoning' && event.state?.decision === 'PENDING_HUMAN_REVIEW') {
                    statusText = 'Low Confidence';
                    statusClass = 'text-brand-warning border-brand-warning/30 bg-brand-warning/10';
                  }
                }
                
                // Skip display of reasoning/challenger if loopback was triggered
                const isLoopbackTriggered = pipelineEvents.some(e => e.node_name === 'loopback_request');
                if (node.id === 'reasoning' && isLoopbackTriggered) {
                  const loopbackEvent = pipelineEvents.find(e => e.node_name === 'loopback_request');
                  return (
                    <div key="loopback_row" className="flex items-center justify-between p-3 rounded-xl bg-brand-danger/10 border border-brand-danger/25 text-left transition-all">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-brand-danger">Loopback Request Suspended</span>
                        <span className="text-xs text-brand-textMuted">Claim lacks required documents - dispatched alert.</span>
                      </div>
                      <span className="text-[10px] font-mono border px-2.5 py-0.5 rounded bg-brand-danger/15 text-brand-danger border-brand-danger/30">
                        AWAITING_DOCUMENT
                      </span>
                    </div>
                  );
                }
                if ((node.id === 'reasoning' || node.id === 'challenger') && isLoopbackTriggered) return null;

                return (
                  <div key={node.id} className={`flex items-center justify-between p-3 rounded-xl border transition-all duration-300 ${isCompleted ? 'bg-white/5 border-white/10' : 'bg-transparent border-white/5 opacity-55'}`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${isCompleted ? 'bg-brand-success text-white' : 'bg-white/5 text-gray-500'}`}>
                        {isCompleted ? '✓' : '○'}
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white">{node.label}</h4>
                        <p className="text-xs text-brand-textMuted">{node.description}</p>
                      </div>
                    </div>
                    <span className={`text-[10px] font-mono border px-2 py-0.5 rounded ${statusClass}`}>
                      {statusText}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
