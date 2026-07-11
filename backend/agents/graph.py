import os
import sys
import time
import re
import asyncio
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
    reasoning_passes: List[Dict[str, Any]]
    decision: Optional[str] # APPROVED, REJECTED, PENDING_HUMAN_REVIEW
    confidence_score: Optional[float]
    rationale: Optional[str]
    sources: List[Dict[str, Any]]
    missing_fields: List[str]
    errors: List[str]
    trace_log: List[Dict[str, Any]]

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
async def intake_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Intake] Processing Claim ID {state['claim_id']} ---")
    
    def get_claim():
        db = SessionLocal()
        try:
            return db.query(Claim).filter(Claim.id == state["claim_id"]).first()
        finally:
            db.close()
            
    try:
        claim = await asyncio.to_thread(get_claim)
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
        
    return state

async def retrieve_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Retrieve] Concurrently fetching structured & unstructured data ---")
    
    # 1. Coroutine for structured retrieval
    async def run_structured():
        st_start = time.time()
        def fetch_claim_data():
            db = SessionLocal()
            try:
                claim = db.query(Claim).filter(Claim.id == state["claim_id"]).first()
                if not claim:
                    return None
                return {
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
            finally:
                db.close()
        try:
            res = await asyncio.to_thread(fetch_claim_data)
            return {"status": "success", "data": res, "latency": int((time.time() - st_start) * 1000)}
        except Exception as e:
            return {"status": "error", "error": str(e), "latency": int((time.time() - st_start) * 1000)}

    # 2. Coroutine for unstructured retrieval
    async def run_unstructured():
        ust_start = time.time()
        def fetch_policy_data():
            collection = get_collection()
            query_text = f"Incident Type: {state['incident_type']}. Description: {state['incident_description']}"
            return query_policy(collection, query_text, n_results=3)
        try:
            res = await asyncio.to_thread(fetch_policy_data)
            return {"status": "success", "data": res, "latency": int((time.time() - ust_start) * 1000)}
        except Exception as e:
            return {"status": "error", "error": str(e), "latency": int((time.time() - ust_start) * 1000)}

    # Run both concurrently in the event loop
    struct_res, unstruct_res = await asyncio.gather(run_structured(), run_unstructured())

    # Merge structured results into state
    if struct_res["status"] == "success" and struct_res["data"]:
        structured = struct_res["data"]
        state["structured_data"] = structured
        state["retrieved_structured"] = True
        state["sources"].append({
            "type": "structured_database",
            "name": f"Postgres Claim Record ({structured['claim_number']})",
            "details": structured
        })
        record_trace(state, "retrieve_structured", {"claim_id": state["claim_id"]}, {"structured_data": structured}, struct_res["latency"])
    else:
        err = struct_res.get("error", "Claim not found during structured retrieval.")
        state["errors"].append(err)
        record_trace(state, "retrieve_structured", {"claim_id": state["claim_id"]}, {"error": err}, struct_res["latency"])

    # Merge unstructured results into state
    if unstruct_res["status"] == "success":
        matches = unstruct_res["data"]
        state["unstructured_context"] = matches
        state["retrieved_unstructured"] = True
        for m in matches:
            state["sources"].append({
                "type": "unstructured_policy",
                "name": f"Policy chunk from {m['metadata']['source_file']}",
                "content": m["content"],
                "distance": m["distance"] if "distance" in m else None
            })
        record_trace(state, "retrieve_unstructured", {}, {"matches_count": len(matches)}, unstruct_res["latency"])
    else:
        err = unstruct_res["error"]
        state["errors"].append(err)
        record_trace(state, "retrieve_unstructured", {}, {"error": err}, unstruct_res["latency"])

    # Record trace for the overall retrieval step
    record_trace(state, "retrieve", {"claim_id": state["claim_id"]}, {"retrieved_structured": state["retrieved_structured"], "retrieved_unstructured": state["retrieved_unstructured"]}, int((time.time() - start_time) * 1000))
    return state

async def eval_state_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Eval State] Checking for missing fields ---")
    
    missing = []
    if not state.get("structured_data"):
        missing.append("structured_data")
    else:
        data = state["structured_data"]
        # Treat None or 0.0 as missing loss amount (conversational loophole test)
        if data.get("estimated_loss_amount") is None or data.get("estimated_loss_amount") == 0.0:
            missing.append("estimated_loss_amount")
        if not data.get("policy_number"):
            missing.append("policy_number")
        if not data.get("claimant_name"):
            missing.append("claimant_name")
            
    # Suspend if description is completely empty or trivial
    if not state.get("incident_description") or len(state["incident_description"].strip()) < 15:
        missing.append("incident_description")
        
    state["missing_fields"] = missing
    record_trace(state, "eval_state", {}, {"missing_fields": missing}, int((time.time() - start_time) * 1000))
    return state

async def loopback_request_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Loopback Request] Triggering missing document alerts ---")
    
    state["decision"] = "PENDING_HUMAN_REVIEW"
    state["confidence_score"] = 0.0
    state["rationale"] = f"Claim processing suspended. The following required information is missing: {', '.join(state['missing_fields'])}. A request has been dispatched to the claimant."
    
    def update_claim_loopback():
        db = SessionLocal()
        try:
            claim = db.query(Claim).filter(Claim.id == state["claim_id"]).first()
            if claim:
                claim.claim_status = "AWAITING_DOCUMENT"
                db.commit()
        finally:
            db.close()
            
    await asyncio.to_thread(update_claim_loopback)
    
    record_trace(
        state, 
        "loopback_request", 
        {"missing_fields": state["missing_fields"]}, 
        {"action": "awaiting_document_alert_sent", "new_status": "AWAITING_DOCUMENT"}, 
        int((time.time() - start_time) * 1000),
        0.0
    )
    return state

async def reasoning_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Reasoning] Invoking reasoning agent with self-consistency ---")
    
    try:
        # Run self-consistency evaluation in threadpool
        trust_result = await asyncio.to_thread(evaluate_trust, state["structured_data"], state["unstructured_context"])
        
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

async def challenger_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Challenger] Auditing reasoning output ---")
    
    prompt = f"""
    You are a Regulated Compliance Auditor and Challenger.
    Your task is to inspect the primary agent's claim adjudication and look for any loopholes, exclusions, or rules they might have overlooked.
    
    Claim Details:
    - Incident Type: {state['incident_type']}
    - Description: "{state['incident_description']}"
    - Structured Details: {state['structured_data']}
    
    Matching Policy Rules:
    {state['unstructured_context']}
    
    Primary Agent Assessment:
    - Decision: {state['decision']}
    - Rationale: {state['rationale']}
    
    Compliance Audit Guidelines:
    1. Check for commercial use exclusions (e.g. ridesharing, delivery services).
    2. Check for gradual damage exclusions (e.g. slow wear and tear, gradual plumbing leaks).
    3. Check for mandatory documentation (e.g. police reports for theft claims).
    4. Check for filing deadlines.
    
    Provide your response in the following format:
    AUDIT_AGREEMENT: [AGREE / DISAGREE]
    AUDIT_RATIONALE: <your detailed critique. Identify any policy exclusion codes like SEC-105 or SEC-102 that are violated or validly applied>
    """
    
    try:
        messages = [
            {"role": "system", "content": "You are a Regulated Compliance Auditor and Challenger."},
            {"role": "user", "content": prompt}
        ]
        # Call LLM auditor in threadpool with correct arguments
        audit_output = await asyncio.to_thread(call_llm, messages, role="reasoning", temperature=0.1)
        
        # Parse agreement
        agreement_match = re.search(r"AUDIT_AGREEMENT:\s*(AGREE|DISAGREE)", audit_output, re.IGNORECASE)
        agreement = agreement_match.group(1).upper() if agreement_match else "AGREE"
        
        audit_rationale_split = re.split(r"AUDIT_RATIONALE:\s*", audit_output, flags=re.IGNORECASE)
        audit_rationale = audit_rationale_split[1].strip() if len(audit_rationale_split) > 1 else audit_output.strip()
        
        # If the challenger disagrees, override decision to PENDING_HUMAN_REVIEW and lower confidence
        if agreement == "DISAGREE":
            print(f"[Challenger Override] Compliance audit disagreed with primary reasoning. Flagging for Human Review.")
            state["decision"] = "PENDING_HUMAN_REVIEW"
            state["confidence_score"] = 0.0
            state["rationale"] = f"{state['rationale']}\n\n[CHALLENGER OVERRIDE - COMPLIANCE ALERT]: {audit_rationale}"
        else:
            state["rationale"] = f"{state['rationale']}\n\n[CHALLENGER COMPLIANCE AUDIT]: {audit_rationale}"
            
        record_trace(state, "challenger", {"primary_decision": state["decision"]}, {"audit_agreement": agreement, "audit_rationale": audit_rationale}, int((time.time() - start_time) * 1000))
        
    except Exception as e:
        print(f"Challenger node execution error: {e}")
        state["errors"].append(f"Challenger compliance audit failed: {e}")
        record_trace(state, "challenger", {}, {"error": str(e)}, int((time.time() - start_time) * 1000))
        
    return state

async def decision_node(state: ClaimState) -> ClaimState:
    start_time = time.time()
    print(f"--- [Node: Decision] Finalizing state and writing traces to DB ---")
    
    def save_decision_data():
        db = SessionLocal()
        try:
            # 1. Determine database claim status based on decision & confidence threshold
            confidence_threshold = 0.8
            is_low_confidence = state["confidence_score"] < confidence_threshold
            
            # Keep AWAITING_DOCUMENT status if loopback triggered it
            claim = db.query(Claim).filter(Claim.id == state["claim_id"]).first()
            current_status = claim.claim_status if claim else ""
            
            if current_status == "AWAITING_DOCUMENT":
                new_status = "AWAITING_DOCUMENT"
            elif state["decision"] == "PENDING_HUMAN_REVIEW" or is_low_confidence:
                new_status = "PENDING_HUMAN_REVIEW"
            elif state["decision"] == "APPROVED":
                new_status = "AUTO_APPROVED"
            elif state["decision"] == "REJECTED":
                new_status = "AUTO_REJECTED"
            else:
                new_status = "PENDING_HUMAN_REVIEW"
                
            if claim:
                claim.claim_status = new_status
                db.commit()
                print(f"Updated Claim status in DB to: {new_status}")
                
            # 2. Insert into Review Queue if routed to human review (except loopback)
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
                else:
                    existing_review.status = "PENDING"
                    existing_review.confidence_score = state["confidence_score"]
                    existing_review.agent_reasoning = state["rationale"]
                    existing_review.retrieved_sources = state["sources"]
                db.commit()
                print(f"Added/Updated Claim CLM-{state['claim_id']} in human Review Queue.")
                
            # 3. Write all traces
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
            return new_status
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    try:
        new_status = await asyncio.to_thread(save_decision_data)
        record_trace(state, "decision", {}, {"final_status": new_status}, int((time.time() - start_time) * 1000))
    except Exception as e:
        print(f"Error finalizing decision: {e}")
        
    return state

# 3. Build LangGraph Graph
workflow = StateGraph(ClaimState)

# Add nodes
workflow.add_node("intake", intake_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("eval_state", eval_state_node)
workflow.add_node("loopback_request", loopback_request_node)
workflow.add_node("reasoning", reasoning_node)
workflow.add_node("challenger", challenger_node)
workflow.add_node("decision", decision_node)

# Add entry point
workflow.set_entry_point("intake")

# Linear pipeline with concurrent internal retrieve node
workflow.add_edge("intake", "retrieve")
workflow.add_edge("retrieve", "eval_state")

# Eval State branches conditional edges based on missing fields
def eval_state_router(state: ClaimState) -> str:
    if state["missing_fields"]:
        return "loopback_request"
    return "reasoning"

workflow.add_conditional_edges(
    "eval_state",
    eval_state_router,
    {
        "loopback_request": "loopback_request",
        "reasoning": "reasoning"
    }
)

# Connect loopback directly to decision
workflow.add_edge("loopback_request", "decision")

# Connect reasoning directly to challenger audit
workflow.add_edge("reasoning", "challenger")

# Connect challenger directly to decision
workflow.add_edge("challenger", "decision")

# Connect decision to END
workflow.add_edge("decision", END)

# Compile graph
app = workflow.compile()

async def run_agentic_pipeline(claim_id: int, on_node_complete=None) -> ClaimState:
    """
    Executes the supervisor-driven LangGraph pipeline for a specific claim.
    Streams execution node by node via app.astream.
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
    
    final_state = initial_state
    async for event in app.astream(initial_state):
        for node_name, output_state in event.items():
            final_state = output_state
            if on_node_complete:
                try:
                    await on_node_complete(node_name, output_state)
                except Exception as e:
                    print(f"WS Callback error: {e}")
                    
    return final_state

if __name__ == "__main__":
    # Test execution helper
    if len(sys.argv) > 1:
        cid = int(sys.argv[1])
    else:
        cid = 1
        
    async def run_test():
        res = await run_agentic_pipeline(cid)
        print("\n=== Agentic Graph Final Result ===")
        print(f"Claim ID: {res['claim_id']}")
        print(f"Claim status: {res['decision']}")
        print(f"Confidence: {res['confidence_score']}")
        print(f"Rationale:\n{res['rationale']}")
        print(f"Missing Fields: {res['missing_fields']}")
        print(f"Errors: {res['errors']}")
        
    asyncio.run(run_test())
