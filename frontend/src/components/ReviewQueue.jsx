import React from 'react';
import { AlertTriangle, Clock, ChevronRight, Eye } from 'lucide-react';

export default function ReviewQueue({ reviews, onSelect }) {
  const pendingReviews = reviews.filter(r => r.status === 'PENDING');

  if (pendingReviews.length === 0) {
    return (
      <div className="glass-panel p-8 rounded-2xl flex flex-col items-center justify-center text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-brand-success/10 flex items-center justify-center text-brand-success">
          <Clock className="w-6 h-6 animate-pulse" />
        </div>
        <h3 className="font-bold text-lg text-white">Review Queue is Clear</h3>
        <p className="text-sm text-brand-textMuted max-w-md">
          Great job! There are no loan pre-screenings or claims pending human review. All decisions have been resolved confidently by the Trust Layer.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" /> Claims Pending Adjudication ({pendingReviews.length})
        </h3>
        <span className="text-xs text-brand-textMuted">
          Adjudication decisions require manager signature.
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {pendingReviews.map(rq => (
          <div 
            key={rq.id} 
            className="glass-panel glass-panel-hover p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-left"
          >
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="font-bold text-white text-md">
                  Claim {rq.claim_number}
                </span>
                <span className="text-xs font-semibold bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded border border-amber-500/20">
                  {rq.incident_type}
                </span>
                <span className="text-xs text-brand-textMuted">
                  Claimant: {rq.claimant_name}
                </span>
              </div>
              <p className="text-xs text-gray-300 line-clamp-1 italic">
                "{rq.incident_description}"
              </p>
              <div className="flex items-center gap-4 text-[11px] text-brand-textMuted">
                <span>Loss Estimate: <strong className="text-brand-danger">${rq.estimated_loss_amount?.toLocaleString()}</strong></span>
                <span>•</span>
                <span>Trust Score: <strong className="text-amber-400">{Math.round(rq.confidence_score * 100)}%</strong></span>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto justify-end">
              <div className="w-24 bg-white/5 h-2 rounded-full overflow-hidden hidden sm:block border border-white/5">
                <div 
                  className="bg-amber-500 h-full rounded-full" 
                  style={{ width: `${Math.round(rq.confidence_score * 100)}%` }}
                />
              </div>
              <button
                onClick={() => onSelect(rq)}
                className="w-full md:w-auto px-4 py-2 bg-brand-accent/20 hover:bg-brand-accent/30 text-brand-accent border border-brand-accent/30 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer hover:border-brand-accent/50"
              >
                <Eye className="w-4 h-4" /> Review Details <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
