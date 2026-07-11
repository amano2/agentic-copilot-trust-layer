import os
import sys

# Add parent directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db.database import SessionLocal
from db.models import Claim, ReviewQueue
from agents.graph import run_agentic_pipeline

def main():
    print("=== Verification Script: Trust Layer & Self-Consistency ===")
    
    db = SessionLocal()
    try:
        # Clear existing reviews first to ensure clean test
        db.query(ReviewQueue).delete()
        db.commit()
        
        # Test Case 1: CLM-001 (High-Confidence Auto-Approval Case)
        print("\n" + "="*60)
        print("RUNNING TEST CASE 1: CLM-001 (Alice Vance - Clear Auto Accident)")
        print("Expected outcome: AUTO_APPROVED with Confidence 1.0 (No Review Queue entry)")
        print("="*60)
        
        import asyncio
        state_1 = asyncio.run(run_agentic_pipeline(1))
        print(f"\nResult CLM-001:")
        print(f" - Decision: {state_1['decision']}")
        print(f" - Confidence: {state_1['confidence_score']}")
        print(f" - Final Status in DB: {db.query(Claim).filter(Claim.id == 1).first().claim_status}")
        
        # Check review queue count
        rq_count_1 = db.query(ReviewQueue).count()
        print(f" - Review Queue count: {rq_count_1}")
        
        # Test Case 2: CLM-003 (Low-Confidence / Complex Case)
        print("\n" + "="*60)
        print("RUNNING TEST CASE 2: CLM-003 (Charlie Ding - Uber Rideshare Collision)")
        print("Expected outcome: PENDING_HUMAN_REVIEW with Confidence < 0.8 (Created Review Queue entry)")
        print("="*60)
        
        state_2 = asyncio.run(run_agentic_pipeline(3))
        print(f"\nResult CLM-003:")
        print(f" - Decision: {state_2['decision']}")
        print(f" - Confidence: {state_2['confidence_score']}")
        print(f" - Final Status in DB: {db.query(Claim).filter(Claim.id == 3).first().claim_status}")
        
        # Check review queue
        rq_entry = db.query(ReviewQueue).filter(ReviewQueue.claim_id == 3).first()
        if rq_entry:
            print(f" - [SUCCESS] Review Queue Entry Created successfully!")
            print(f" - Queue Entry ID: {rq_entry.id}")
            print(f" - Queue Entry Status: {rq_entry.status}")
            print(f" - Queue Entry Confidence: {rq_entry.confidence_score}")
        else:
            print(f" - [FAILURE] No Review Queue entry created for CLM-003!")
            
    except Exception as e:
        print(f"\n[ERROR] Trust layer test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
