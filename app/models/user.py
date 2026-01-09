"""User model for dashboard authentication"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"
    RESTAURANT_ADMIN = "restaurant_admin"
    STAFF_VIEWER = "staff_viewer"


class User(Base):
    """Dashboard users"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255))
    phone = Column(String(20))
    
    # Role
    role = Column(Enum(UserRole), default=UserRole.STAFF_VIEWER)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Tokens
    refresh_token = Column(String(500))
    
    # Timestamps
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    
    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has at least the required role level"""
        role_hierarchy = {
            UserRole.STAFF_VIEWER: 1,
            UserRole.RESTAURANT_ADMIN: 2,
            UserRole.SUPER_ADMIN: 3,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)

