"""Authentication schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # User ID
    tenant_id: Optional[str] = None
    role: str
    exp: datetime


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class UserCreate(BaseModel):
    """Create user request"""
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.STAFF_VIEWER
    tenant_id: Optional[UUID] = None


class UserResponse(BaseModel):
    """User response"""
    id: UUID
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: UserRole
    tenant_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

