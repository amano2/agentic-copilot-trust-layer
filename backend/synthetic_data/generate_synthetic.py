import os
import sys
import datetime
from sqlalchemy.orm import Session

# Add parent backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db.database import engine, Base, SessionLocal
from db.models import Claim
from vectorstore.chroma_store import get_collection, add_documents

# Helper for date generation
def days_ago(n):
    return datetime.datetime.utcnow() - datetime.timedelta(days=n)

def seed_database():
    print("Seeding PostgreSQL Database...")
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(Claim).count() > 0:
            print("Claims table already contains records. Skipping seed.")
        else:
            claims = [
                Claim(
                    claim_number="CLM-001",
                    policy_number="POL-AUTO-982",
                    claimant_name="Alice Vance",
                    incident_date=days_ago(5),
                    filing_date=days_ago(0),
                    incident_type="Auto Accident",
                    incident_description="I was waiting at a stop light on Main Street when another car rear-ended me. The police arrived and filed an accident report, finding the other driver 100% at fault.",
                    estimated_loss_amount=4500.00,
                    deductible=500.00,
                    coverage_limit=50000.00,
                    claim_status="UNDER_REVIEW"
                ),
                Claim(
                    claim_number="CLM-002",
                    policy_number="POL-HOME-120",
                    claimant_name="Bob Miller",
                    incident_date=days_ago(60),
                    filing_date=days_ago(0),
                    incident_type="Water Damage",
                    incident_description="I noticed a water stain on my basement wall about two months ago. It has been growing and smells moldy. Yesterday I finally had a plumber look at it and he said it has been leaking slowly from a rusty pipe joint for several months.",
                    estimated_loss_amount=3200.00,
                    deductible=1000.00,
                    coverage_limit=100000.00,
                    claim_status="UNDER_REVIEW"
                ),
                Claim(
                    claim_number="CLM-003",
                    policy_number="POL-AUTO-234",
                    claimant_name="Charlie Ding",
                    incident_date=days_ago(2),
                    filing_date=days_ago(0),
                    incident_type="Auto Accident",
                    incident_description="I was driving back from dropping off a customer for my Uber rideshare shift when another vehicle swerved into my lane and hit my side mirror and door. I had my Uber app online waiting for the next ride.",
                    estimated_loss_amount=2800.00,
                    deductible=500.00,
                    coverage_limit=30000.00,
                    claim_status="UNDER_REVIEW"
                ),
                Claim(
                    claim_number="CLM-004",
                    policy_number="POL-HOME-445",
                    claimant_name="Diana Prince",
                    incident_date=days_ago(45),
                    filing_date=days_ago(0),
                    incident_type="Property Fire",
                    incident_description="There was a small electrical fire in my kitchen on May 26th. The stove and cabinets were damaged. I was hospitalized for severe smoke inhalation and post-accident recovery for 4 weeks immediately following the incident, which is why I am filing this claim late.",
                    estimated_loss_amount=6500.00,
                    deductible=1000.00,
                    coverage_limit=150000.00,
                    claim_status="UNDER_REVIEW"
                ),
                Claim(
                    claim_number="CLM-005",
                    policy_number="POL-RENT-771",
                    claimant_name="Evan Wright",
                    incident_date=days_ago(4),
                    filing_date=days_ago(0),
                    incident_type="Theft",
                    incident_description="My laptop and gym bag were stolen from the passenger seat of my car while it was parked in front of my gym. I did not file a police report because I was in a rush and didn't think the police would find it anyway.",
                    estimated_loss_amount=1800.00,
                    deductible=250.00,
                    coverage_limit=150000.00,
                    claim_status="UNDER_REVIEW"
                )
            ]
            db.bulk_save_objects(claims)
            db.commit()
            print(f"Successfully seeded {len(claims)} claim records into PostgreSQL.")
    except Exception as e:
        print(f"Error seeding PostgreSQL: {e}")
        db.rollback()
    finally:
        db.close()

def seed_chromadb():
    print("Seeding ChromaDB with Policy Documents...")
    try:
        collection = get_collection()
        
        # Check if collection has documents already
        if collection.count() > 0:
            print("ChromaDB policy collection already contains documents. Re-seeding to ensure fresh policies.")
            # Let's delete existing documents to prevent duplicates
            existing_ids = collection.get()['ids']
            if existing_ids:
                collection.delete(ids=existing_ids)
        
        # Read policies from backend/synthetic_data/policies
        policies_dir = os.path.join(os.path.dirname(__file__), "policies")
        if not os.path.exists(policies_dir):
            print(f"Error: Policies directory {policies_dir} not found.")
            return

        texts = []
        metadatas = []
        ids = []
        
        files = [f for f in os.listdir(policies_dir) if f.endswith(".txt")]
        print(f"Found {len(files)} policy files to ingest.")
        
        for file in files:
            path = os.path.join(policies_dir, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple chunking by paragraph or fixed headings
            # To keep things simple and clear for the retriever, we chunk by double newlines or sections
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            
            for idx, para in enumerate(paragraphs):
                chunk_id = f"{file.split('.')[0]}_chunk_{idx}"
                texts.append(para)
                metadatas.append({
                    "source_file": file,
                    "section": para.split("\n")[0] if "\n" in para else "General",
                    "chunk_index": idx
                })
                ids.append(chunk_id)
                
        if texts:
            add_documents(collection, texts, metadatas, ids)
            print(f"Successfully chunked and embedded {len(texts)} policy passages into ChromaDB.")
        else:
            print("No policy passages found to embed.")
            
    except Exception as e:
        print(f"Error seeding ChromaDB: {e}")

if __name__ == "__main__":
    # Ensure correct working directory context
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    seed_database()
    seed_chromadb()
    print("Data Foundation Seed Complete.")
