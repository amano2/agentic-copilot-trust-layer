import os
import sys

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db.database import SessionLocal
from db.models import Claim
from vectorstore.chroma_store import get_collection, query_policy

def main():
    # Ensure correct working directory context
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=== Verification Script: Data Foundation Retrieval ===")
    
    # 1. Check claim in DB
    db = SessionLocal()
    try:
        claims = db.query(Claim).all()
        if not claims:
            print("[ERROR] No claims found in database. Run generate_synthetic.py first.")
            sys.exit(1)
            
        print(f"[SUCCESS] Found {len(claims)} claims in Postgres:")
        for c in claims:
            print(f" - ID: {c.id} | Claim: {c.claim_number} | Claimant: {c.claimant_name} | Type: {c.incident_type}")
            
        # Select Claim CLM-003 (Rideshare accident) to test policy retrieval
        test_claim = db.query(Claim).filter(Claim.claim_number == "CLM-003").first()
        if not test_claim:
            # Fallback to first claim if CLM-003 is not found
            test_claim = claims[0]
            
        print(f"\nTesting Retrieval for claim: {test_claim.claim_number}")
        print(f" Claimant: {test_claim.claimant_name}")
        print(f" Description: \"{test_claim.incident_description}\"")
        
        # 2. Query vectorstore
        print("\nQuerying ChromaDB for policy matches...")
        collection = get_collection()
        # Query ChromaDB with the incident description
        matches = query_policy(collection, test_claim.incident_description, n_results=3)
        
        if not matches:
            print("[ERROR] No policy matches found in ChromaDB.")
        else:
            print(f"[SUCCESS] Found {len(matches)} matching policy chunks:")
            for idx, match in enumerate(matches):
                print(f"\n--- Match {idx + 1} (Source: {match['metadata']['source_file']}, Similarity Distance: {match['distance']:.4f}) ---")
                print(match['content'])
                
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
