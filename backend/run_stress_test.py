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
    print("=== Verification Script: Stress Testing Edge Cases ===")
    
    db = SessionLocal()
    try:
        # Clear existing reviews first
        db.query(ReviewQueue).delete()
        db.commit()
        
        claims = db.query(Claim).all()
        print(f"Ingested Claims Count: {len(claims)}")
        
        for c in claims:
            print("\n" + "="*70)
            print(f"PROCESSING CLAIM: {c.claim_number} ({c.claimant_name})")
            print(f"Incident Type:    {c.incident_type}")
            print(f"Description:      \"{c.incident_description}\"")
            print(f"Loss amount:      ${c.estimated_loss_amount}")
            print("="*70)
            
            res = run_agentic_pipeline(c.id)
            
            # Check review queue status
            rq = db.query(ReviewQueue).filter(ReviewQueue.claim_id == c.id).first()
            
            print(f"\nFinal State for {c.claim_number}:")
            print(f" - Decision:             {res['decision']}")
            print(f" - Trust/Confidence Score: {res['confidence_score']}")
            print(f" - Database Status:       {db.query(Claim).filter(Claim.id == c.id).first().claim_status}")
            print(f" - Routed to Review Queue? {'YES' if rq else 'NO'}")
            if rq:
                print(f"   - Queue Item ID:       {rq.id}")
                
    except Exception as e:
        print(f"\n[ERROR] Stress test run failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
