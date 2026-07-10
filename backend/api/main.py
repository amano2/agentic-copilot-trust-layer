import os
import sys
import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

# Add parent backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

print("[TRACE] Importing database components...")
from db.database import get_db, Base, engine
print("[TRACE] Importing models...")
from db.models import Claim, ReviewQueue, AgentTrace
print("[TRACE] Importing agent graph...")
from agents.graph import run_agentic_pipeline

# Create tables
print("[TRACE] Creating database tables (Base.metadata.create_all)...")
Base.metadata.create_all(bind=engine)
print("[TRACE] Database tables created successfully.")

print("[TRACE] Instantiating FastAPI app...")
app = FastAPI(
    title="Regulated Agentic Copilot - Backend API",
    description="Backend services for the agentic enterprise copilot decision support system.",
    version="1.0.0"
)
print("[TRACE] FastAPI app instantiated.")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Pydantic Schemas
class AdjudicationRequest(BaseModel):
    action: str # "APPROVED" or "REJECTED"
    reviewer_notes: str

class ClaimProcessResponse(BaseModel):
    claim_id: int
    claim_number: str
    decision: str
    confidence_score: float
    rationale: str
    errors: List[str]

@app.get("/")
def read_root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

# 2. Endpoints
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/api/claims")
def get_claims(db: Session = Depends(get_db)):
    """
    Get all claims in the system.
    """
    claims = db.query(Claim).order_by(Claim.id.desc()).all()
    return claims

@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db)):
    """
    Get details of a specific claim.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@app.get("/api/review-queue")
def get_review_queue(db: Session = Depends(get_db)):
    """
    Get all items in the human review queue, including claim details.
    """
    results = db.query(ReviewQueue).order_by(ReviewQueue.created_at.desc()).all()
    
    queue_list = []
    for rq in results:
        claim = db.query(Claim).filter(Claim.id == rq.claim_id).first()
        queue_list.append({
            "id": rq.id,
            "claim_id": rq.claim_id,
            "claim_number": claim.claim_number if claim else "N/A",
            "claimant_name": claim.claimant_name if claim else "N/A",
            "incident_type": claim.incident_type if claim else "N/A",
            "estimated_loss_amount": claim.estimated_loss_amount if claim else 0,
            "incident_description": claim.incident_description if claim else "",
            "status": rq.status,
            "confidence_score": rq.confidence_score,
            "agent_reasoning": rq.agent_reasoning,
            "retrieved_sources": rq.retrieved_sources,
            "reviewer_notes": rq.reviewer_notes,
            "reviewed_at": rq.reviewed_at.isoformat() if rq.reviewed_at else None,
            "created_at": rq.created_at.isoformat()
        })
        
    return queue_list

@app.post("/api/claims/process/{claim_id}")
def process_claim(claim_id: int, db: Session = Depends(get_db)):
    """
    Triggers the supervisor-driven LangGraph pipeline for a specific claim.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    try:
        final_state = run_agentic_pipeline(claim_id)
        
        return {
            "claim_id": final_state["claim_id"],
            "claim_number": final_state["claim_number"],
            "decision": final_state["decision"],
            "confidence_score": final_state["confidence_score"],
            "rationale": final_state["rationale"],
            "errors": final_state["errors"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

@app.post("/api/review-queue/{review_id}/adjudicate")
def adjudicate_review(review_id: int, payload: AdjudicationRequest, db: Session = Depends(get_db)):
    """
    Action for human reviewer to approve or reject a claim pending in the review queue.
    """
    rq_entry = db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
    if not rq_entry:
        raise HTTPException(status_code=404, detail="Review queue entry not found")
        
    if rq_entry.status != "PENDING":
        raise HTTPException(status_code=400, detail="This claim has already been adjudicated")
        
    action = payload.action.upper()
    if action not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Action must be 'APPROVED' or 'REJECTED'")
        
    try:
        # 1. Update review entry
        rq_entry.status = action
        rq_entry.reviewer_notes = payload.reviewer_notes
        rq_entry.reviewed_at = datetime.datetime.utcnow()
        
        # 2. Update claim status
        claim = db.query(Claim).filter(Claim.id == rq_entry.claim_id).first()
        if claim:
            claim.claim_status = action
            
        # 3. Log an agent trace for the human decision
        trace = AgentTrace(
            claim_id=rq_entry.claim_id,
            node_name="human_reviewer",
            input_state={"action_requested": action, "notes": payload.reviewer_notes},
            output_state={"adjudication_result": action, "status": "COMPLETED"},
            latency_ms=0,
            confidence=1.0
        )
        db.add(trace)
        db.commit()
        
        return {"status": "success", "message": f"Claim {claim.claim_number if claim else ''} has been {action}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/claims/{claim_id}/trace")
def get_claim_traces(claim_id: int, db: Session = Depends(get_db)):
    """
    Get the execution node traces logged for a specific claim.
    """
    traces = db.query(AgentTrace).filter(AgentTrace.claim_id == claim_id).order_by(AgentTrace.created_at.asc()).all()
    return traces

if __name__ == "__main__":
    import uvicorn
    # Read port from env
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=False)
