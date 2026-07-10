import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String, unique=True, index=True, nullable=False)
    policy_number = Column(String, index=True, nullable=False)
    claimant_name = Column(String, nullable=False)
    incident_date = Column(DateTime, nullable=False)
    filing_date = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    incident_type = Column(String, nullable=False) # e.g. "Auto Accident", "Water Damage", "Theft", "Property Fire"
    incident_description = Column(Text, nullable=False)
    estimated_loss_amount = Column(Float, nullable=False)
    deductible = Column(Float, nullable=False)
    coverage_limit = Column(Float, nullable=False)
    claim_status = Column(String, nullable=False, default="UNDER_REVIEW") # UNDER_REVIEW, AUTO_APPROVED, AUTO_REJECTED, PENDING_HUMAN_REVIEW, APPROVED, REJECTED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    reviews = relationship("ReviewQueue", back_populates="claim", cascade="all, delete-orphan")

class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED
    confidence_score = Column(Float, nullable=False) # 0.0 to 1.0
    agent_reasoning = Column(Text, nullable=False) # detailed markdown reasoning
    retrieved_sources = Column(JSON, nullable=False) # JSON list of sources used (structured + unstructured)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    claim = relationship("Claim", back_populates="reviews")

class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, index=True, nullable=False)
    node_name = Column(String, nullable=False) # e.g. intake, supervisor, retrieve_unstructured, etc.
    input_state = Column(JSON, nullable=True)
    output_state = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
