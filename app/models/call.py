"""Call-related models"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Call(Base):
    """Call records"""
    __tablename__ = "calls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Twilio identifiers
    call_sid = Column(String(50), unique=True)
    stream_sid = Column(String(50))
    
    # Call details
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)
    direction = Column(String(20), default="inbound")  # inbound/outbound
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Status and outcome
    status = Column(String(50), default="initiated")  # initiated, in-progress, completed, failed
    outcome = Column(String(50))  # order_placed, reservation_made, faq_answered, escalated, abandoned
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text)
    
    # Recording
    recording_url = Column(String(500))
    recording_duration_seconds = Column(Integer)
    
    # Summary
    summary = Column(Text)  # AI-generated call summary
    sentiment = Column(String(20))  # positive, neutral, negative
    
    # Metadata
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="calls")
    transcript = relationship("Transcript", back_populates="call", uselist=False)
    order = relationship("Order", back_populates="call", uselist=False)
    reservation = relationship("Reservation", back_populates="call", uselist=False)


class Transcript(Base):
    """Call transcripts"""
    __tablename__ = "transcripts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), unique=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Full transcript text
    text = Column(Text)
    
    # Segmented transcript with timestamps
    # [{"speaker": "agent|customer", "text": "...", "start_ms": 0, "end_ms": 1000}, ...]
    segments_json = Column(JSON, default=list)
    
    # Extracted entities
    entities_json = Column(JSON, default=dict)  # {"customer_name": "John", "items": [...]}
    
    # Processing status
    is_final = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    call = relationship("Call", back_populates="transcript")

