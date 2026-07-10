import os
import sys

# Add parent directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agents.graph import run_agentic_pipeline

def main():
    print("=== Verification Script: LangGraph Orchestration ===")
    
    # Determine claim ID to run
    if len(sys.argv) > 1:
        try:
            claim_id = int(sys.argv[1])
        except ValueError:
            print(f"[ERROR] Claim ID must be an integer, got: {sys.argv[1]}")
            sys.exit(1)
    else:
        # Default to claim 3 (the Uber rideshare collision - low confidence case)
        # to showcase routing, structured and unstructured retrieval, and exclusions
        claim_id = 3
        print(f"No Claim ID specified. Defaulting to Claim ID {claim_id} (Uber rideshare accident).")
        
    print(f"\nProcessing Claim ID: {claim_id}...")
    
    try:
        final_state = run_agentic_pipeline(claim_id)
        
        print("\n" + "="*50)
        print("AGENT EXECUTION TRACE LOG (Node Timeline):")
        print("="*50)
        
        for idx, entry in enumerate(final_state["trace_log"]):
            print(f"{idx+1}. Node: {entry['node_name']} | Latency: {entry['latency_ms']}ms | Confidence: {entry['confidence']}")
            if entry["node_name"] == "reasoning":
                print(f"   [LLM Output Preview]: {entry['output_state']}")
                
        print("\n" + "="*50)
        print("FINAL PIPELINE OUTPUT STATUS:")
        print("="*50)
        print(f"Claim Number:      {final_state['claim_number']}")
        print(f"Incident Type:     {final_state['incident_type']}")
        print(f"Pipeline Decision: {final_state['decision']}")
        print(f"Confidence Score:  {final_state['confidence_score']}")
        print(f"Rationale:\n{final_state['rationale']}")
        
        if final_state["errors"]:
            print(f"\n[WARNING] Pipeline encountered errors: {final_state['errors']}")
            
        print("\n" + "="*50)
        print("RETRIEVED SOURCES USED:")
        print("="*50)
        for s in final_state["sources"]:
            if s["type"] == "structured_database":
                print(f" - [Structured DB] {s['name']}")
            else:
                print(f" - [Unstructured Policy] {s['name']} (Distance: {s['distance']:.4f})")
                
        print("\n[SUCCESS] Agent graph executed successfully end-to-end.")
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline run failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
