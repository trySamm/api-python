"""Reservation model"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Reservation(Base):
    """Table reservations"""
    __tablename__ = "reservations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"))
    
    # Customer information
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(255))
    
    # Reservation details
    party_size = Column(Integer, nullable=False)
    reservation_datetime = Column(DateTime, nullable=False)
    
    # Status
    status = Column(String(50), default="pending")  # pending, confirmed, seated, completed, cancelled, no_show
    
    # Notes
    notes = Column(Text)
    special_requests = Column(Text)
    
    # SMS/Email confirmation
    confirmation_sent = Column(DateTime)
    reminder_sent = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="reservations")
    call = relationship("Call", back_populates="reservation")

