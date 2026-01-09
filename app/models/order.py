"""Order model"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Order(Base):
    """Takeout orders"""
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"))
    
    # Customer information
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(255))
    
    # Order details
    # [{"item_id": "...", "name": "...", "quantity": 1, "modifiers": [...], "price_cents": 1500}, ...]
    items_json = Column(JSON, nullable=False)
    
    # Pricing
    subtotal_cents = Column(Integer, nullable=False, default=0)
    tax_cents = Column(Integer, default=0)
    total_cents = Column(Integer, nullable=False, default=0)
    
    # Timing
    pickup_time = Column(DateTime)
    estimated_ready_time = Column(DateTime)
    
    # Status
    status = Column(String(50), default="pending")  # pending, confirmed, preparing, ready, completed, cancelled
    
    # Notes
    notes = Column(Text)
    special_instructions = Column(Text)
    
    # SMS confirmation
    confirmation_sent = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="orders")
    call = relationship("Call", back_populates="order")

