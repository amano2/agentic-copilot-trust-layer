import os
import sys
import time
import re
from typing import Dict, List, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

# Add parent backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db.database import SessionLocal
from db.models import Claim, AgentTrace, ReviewQueue
from vectorstore.chroma_store import get_collection, query_policy
from agents.llm_client import call_llm
from trust.trust_layer import evaluate_trust

# 1. State Definition
class ClaimState(TypedDict):
    claim_id: int
    claim_number: str
    incident_type: str
    incident_description: str
    retrieved_structured: bool
    retrieved_unstructured: bool
    structured_data: Optional[Dict[str, Any]]
    unstructured_context: List[Dict[str, Any]]
    reasoning_passes: List[Dict[str, Any]] # Saves outputs of independent runs
    decision: Optional[str] # APPROVED, REJECTED, PENDING_HUMAN_REVIEW
    confidence_score: Optional[float] # 0.0 to 1.0
    rationale: Optional[str]
    sources: List[Dict[str, Any]]
    missing_fields: List[str]
    errors: List[str]
    trace_log: List[Dict[str, Any]] # Accumulates step-by-step logs for database saving

# Helper to record trace
def record_trace(state: ClaimState, node_name: str, input_data: Any, output_data: Any, latency_ms: int, confidence: Optional[float] = None) -> None:
    trace_entry = {
        "node_name": node_name,
        "input_state": input_data,
        "output_state": output_data,
        "latency_ms": latency_ms,
        "confidence": confidence,
        "timestamp": time.time()
    }
    state["trace_log"].append(trace_entry)

# 2. Graph Nodes
def intake_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Intake] Processing Claim ID {state['claim_id']} ---")
    
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.id == state["claim_id"]).first()
        if not claim:
            error_msg = f"Claim with ID {state['claim_id']} not found in database."
            state["errors"].append(error_msg)
            record_trace(state, "intake", {"claim_id": state["claim_id"]}, {"error": error_msg}, int((time.time() - start_time) * 1000))
            return state
            
        state["claim_number"] = claim.claim_number
        state["incident_type"] = claim.incident_type
        state["incident_description"] = claim.incident_description
        
        output_data = {
            "claim_number": claim.claim_number,
            "incident_type": claim.incident_type,
            "incident_description": claim.incident_description
        }
        record_trace(state, "intake", {"claim_id": state["claim_id"]}, output_data, int((time.time() - start_time) * 1000))
        
    except Exception as e:
        state["errors"].append(str(e))
        record_trace(state, "intake", {"claim_id": state["claim_id"]}, {"error": str(e)}, int((time.time() - start_time) * 1000))
    finally:
        db.close()
        
    return state

def retrieve_structured_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Retrieve Structured] Fetching record for {state['claim_number']} ---")
    
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(Claim.id == state["claim_id"]).first()
        if not claim:
            state["errors"].append("Claim not found during structured retrieval.")
            return state
            
        # Formulate structured data dict
        structured = {
            "claim_number": claim.claim_number,
            "policy_number": claim.policy_number,
            "claimant_name": claim.claimant_name,
            "incident_date": claim.incident_date.isoformat() if hasattr(claim.incident_date, "isoformat") else str(claim.incident_date),
            "filing_date": claim.filing_date.isoformat() if hasattr(claim.filing_date, "isoformat") else str(claim.filing_date),
            "incident_type": claim.incident_type,
            "estimated_loss_amount": claim.estimated_loss_amount,
            "deductible": claim.deductible,
            "coverage_limit": claim.coverage_limit,
            "claim_status": claim.claim_status
        }
        
        state["structured_data"] = structured
        state["retrieved_structured"] = True
        
        # Add to sources
        state["sources"].append({
            "type": "structured_database",
            "name": f"Postgres Claim Record ({claim.claim_number})",
            "details": structured
        })
        
        record_trace(state, "retrieve_structured", {"claim_id": state["claim_id"]}, {"structured_data": structured}, int((time.time() - start_time) * 1000))
        
    except Exception as e:
        state["errors"].append(str(e))
        record_trace(state, "retrieve_structured", {"claim_id": state["claim_id"]}, {"error": str(e)}, int((time.time() - start_time) * 1000))
    finally:
        db.close()
        
    return state

def retrieve_unstructured_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Retrieve Unstructured] Searching vector store for policy chunks ---")
    
    try:
        collection = get_collection()
        # Query with description and type to yield high-quality matches
        query_text = f"Incident Type: {state['incident_type']}. Description: {state['incident_description']}"
        matches = query_policy(collection, query_text, n_results=3)
        
        state["unstructured_context"] = matches
        state["retrieved_unstructured"] = True
        
        # Add matches to sources
        for m in matches:
            state["sources"].append({
                "type": "unstructured_policy",
                "name": f"Policy chunk from {m['metadata']['source_file']}",
                "content": m["content"],
                "distance": m["distance"]
            })
            
        record_trace(state, "retrieve_unstructured", {"query": query_text}, {"matches_count": len(matches)}, int((time.time() - start_time) * 1000))
        
    except Exception as e:
        state["errors"].append(str(e))
        record_trace(state, "retrieve_unstructured", {}, {"error": str(e)}, int((time.time() - start_time) * 1000))
        
    return state

def reasoning_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Reasoning] Invoking reasoning agent with self-consistency ---")
    
    try:
        # Call the evaluate_trust function to run two passes and compile results
        trust_result = evaluate_trust(state["structured_data"], state["unstructured_context"])
        
        # Save to state
        state["decision"] = trust_result["decision"]
        state["confidence_score"] = trust_result["confidence_score"]
        state["rationale"] = trust_result["rationale"]
        state["reasoning_passes"] = trust_result["passes"]
        
        record_trace(
            state, 
            "reasoning", 
            {"claim_id": state["claim_id"]}, 
            {"decision": trust_result["decision"], "confidence_score": trust_result["confidence_score"]}, 
            int((time.time() - start_time) * 1000), 
            trust_result["confidence_score"]
        )
        
    except Exception as e:
        state["errors"].append(str(e))
        state["decision"] = "PENDING_HUMAN_REVIEW"
        state["confidence_score"] = 0.0
        state["rationale"] = f"Self-consistency evaluation failed due to LLM error: {e}"
        record_trace(state, "reasoning", {"claim_id": state["claim_id"]}, {"error": str(e)}, int((time.time() - start_time) * 1000), 0.0)
        
    return state


def decision_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Decision] Finalizing state and writing traces to DB ---")
    
    db = SessionLocal()
    try:
        # 1. Determine database claim status based on decision & confidence threshold
        confidence_threshold = 0.8
        is_low_confidence = state["confidence_score"] < confidence_threshold
        
        if state["decision"] == "PENDING_HUMAN_REVIEW" or is_low_confidence:
            new_status = "PENDING_HUMAN_REVIEW"
        elif state["decision"] == "APPROVED":
            new_status = "AUTO_APPROVED"
        elif state["decision"] == "REJECTED":
            new_status = "AUTO_REJECTED"
        else:
            new_status = "PENDING_HUMAN_REVIEW"
            
        claim = db.query(Claim).filter(Claim.id == state["claim_id"]).first()
        if claim:
            claim.claim_status = new_status
            db.commit()
            print(f"Updated Claim status in DB to: {new_status}")
            
        # 2. Insert into Review Queue if routed to human review
        if new_status == "PENDING_HUMAN_REVIEW":
            existing_review = db.query(ReviewQueue).filter(ReviewQueue.claim_id == state["claim_id"]).first()
            if not existing_review:
                review_item = ReviewQueue(
                    claim_id=state["claim_id"],
                    status="PENDING",
                    confidence_score=state["confidence_score"],
                    agent_reasoning=state["rationale"],
                    retrieved_sources=state["sources"]
                )
                db.add(review_item)
                db.commit()
                print(f"Added Claim CLM-{state['claim_id']} to human Review Queue.")
            else:
                # Update existing queue entry if present
                existing_review.status = "PENDING"
                existing_review.confidence_score = state["confidence_score"]
                existing_review.agent_reasoning = state["rationale"]
                existing_review.retrieved_sources = state["sources"]
                db.commit()
                print(f"Updated existing Review Queue entry for claim ID {state['claim_id']}.")
                
        # 3. Write all accumulated traces in state["trace_log"] to the agent_traces database table
        for entry in state["trace_log"]:
            trace = AgentTrace(
                claim_id=state["claim_id"],
                node_name=entry["node_name"],
                input_state=entry["input_state"],
                output_state=entry["output_state"],
                latency_ms=entry["latency_ms"],
                confidence=entry["confidence"]
            )
            db.add(trace)
        db.commit()
        print(f"Saved {len(state['trace_log'])} trace records to DB.")
        
        record_trace(state, "decision", {}, {"final_status": new_status}, int((time.time() - start_time) * 1000))
        
    except Exception as e:
        print(f"Error finalizing decision: {e}")
        db.rollback()
    finally:
        db.close()
        
    return state

# 3. Router Edge Logic
def supervisor_router(state: ClaimState) -> str:
    """
    Supervisor router node that decides where to go next based on state flags.
    """
    if state["errors"]:
        return "decision" # If we hit hard errors, jump to finalize decision
        
    if not state.get("retrieved_structured"):
        return "retrieve_structured"
        
    if not state.get("retrieved_unstructured"):
        return "retrieve_unstructured"
        
    # Both structured and unstructured info are successfully loaded, proceed to reasoning
    return "reasoning"

# Helpers
def json_format(d: Any) -> str:
    import json
    return json.dumps(d, indent=2)

def parse_reasoning_output(text: str):
    decision_match = re.search(r"DECISION:\s*(APPROVED|REJECTED|PENDING_HUMAN_REVIEW)", text, re.IGNORECASE)
    confidence_match = re.search(r"CONFIDENCE:\s*(HIGH|MEDIUM|LOW)", text, re.IGNORECASE)
    
    decision = decision_match.group(1).upper() if decision_match else "PENDING_HUMAN_REVIEW"
    confidence = confidence_match.group(1).upper() if confidence_match else "LOW"
    
    # Rationale is the text after RATIONALE:
    rationale_split = re.split(r"RATIONALE:\s*", text, flags=re.IGNORECASE)
    rationale = rationale_split[1].strip() if len(rationale_split) > 1 else text.strip()
    
    return decision, confidence, rationale

# 4. Build LangGraph Graph
workflow = StateGraph(ClaimState)

# Add nodes
workflow.add_node("intake", intake_node)
workflow.add_node("retrieve_structured", retrieve_structured_node)
workflow.add_node("retrieve_unstructured", retrieve_unstructured_node)
workflow.add_node("reasoning", reasoning_node)
workflow.add_node("decision", decision_node)

# Add entry point
workflow.set_entry_point("intake")

# Connect intake to supervisor router
# Note: In LangGraph, we can define the entry point, and then define edges.
# We define a conditional edge from 'intake' using supervisor_router
workflow.add_conditional_edges(
    "intake",
    supervisor_router,
    {
        "retrieve_structured": "retrieve_structured",
        "retrieve_unstructured": "retrieve_unstructured",
        "reasoning": "reasoning",
        "decision": "decision"
    }
)

# Connect retrievers back to supervisor router
workflow.add_conditional_edges(
    "retrieve_structured",
    supervisor_router,
    {
        "retrieve_structured": "retrieve_structured",
        "retrieve_unstructured": "retrieve_unstructured",
        "reasoning": "reasoning",
        "decision": "decision"
    }
)

workflow.add_conditional_edges(
    "retrieve_unstructured",
    supervisor_router,
    {
        "retrieve_structured": "retrieve_structured",
        "retrieve_unstructured": "retrieve_unstructured",
        "reasoning": "reasoning",
        "decision": "decision"
    }
)

# Connect reasoning directly to decision
workflow.add_edge("reasoning", "decision")

# Connect decision to END
workflow.add_edge("decision", END)

# Compile graph
app = workflow.compile()

def run_agentic_pipeline(claim_id: int) -> ClaimState:
    """
    Executes the supervisor-driven LangGraph pipeline for a specific claim.
    """
    initial_state = ClaimState(
        claim_id=claim_id,
        claim_number="",
        incident_type="",
        incident_description="",
        retrieved_structured=False,
        retrieved_unstructured=False,
        structured_data=None,
        unstructured_context=[],
        reasoning_passes=[],
        decision=None,
        confidence_score=None,
        rationale=None,
        sources=[],
        missing_fields=[],
        errors=[],
        trace_log=[]
    )
    
    print(f"Starting Agentic Graph execution for Claim ID: {claim_id}")
    final_state = app.invoke(initial_state)
    return final_state

if __name__ == "__main__":
    # Test execution
    if len(sys.argv) > 1:
        cid = int(sys.argv[1])
    else:
        cid = 1 # default to CLM-001 (first claim seeded)
        
    res = run_agentic_pipeline(cid)
    print("\n=== Agentic Graph Final Result ===")
    print(f"Claim ID: {res['claim_id']}")
    print(f"Claim Number: {res['claim_number']}")
    print(f"Decision: {res['decision']}")
    print(f"Confidence: {res['confidence_score']}")
    print(f"Rationale:\n{res['rationale']}")
    print(f"Errors: {res['errors']}")
