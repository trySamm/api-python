"""Audit log model"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AuditLog(Base):
    """Audit trail for important actions"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    
    # Actor information
    actor_id = Column(UUID(as_uuid=True))  # User ID or null for system
    actor_type = Column(String(50))  # user, system, api
    actor_name = Column(String(255))
    
    # Action details
    action = Column(String(100), nullable=False)  # create_order, update_settings, etc.
    resource_type = Column(String(50))  # order, reservation, menu_item, etc.
    resource_id = Column(UUID(as_uuid=True))
    
    # Change data
    data_json = Column(JSON)  # {"before": {...}, "after": {...}}
    
    # Request context
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)

