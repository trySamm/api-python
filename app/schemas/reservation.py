"""Reservation schemas"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


class ReservationCreate(BaseModel):
    """Create reservation request"""
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    party_size: int
    reservation_datetime: datetime
    notes: Optional[str] = None
    special_requests: Optional[str] = None
    call_id: Optional[UUID] = None


class ReservationUpdate(BaseModel):
    """Update reservation request"""
    status: Optional[str] = None
    party_size: Optional[int] = None
    reservation_datetime: Optional[datetime] = None
    notes: Optional[str] = None
    special_requests: Optional[str] = None


class ReservationResponse(BaseModel):
    """Reservation response"""
    id: UUID
    tenant_id: UUID
    call_id: Optional[UUID]
    customer_name: str
    customer_phone: str
    customer_email: Optional[str]
    party_size: int
    reservation_datetime: datetime
    status: str
    notes: Optional[str]
    special_requests: Optional[str]
    confirmation_sent: Optional[datetime]
    reminder_sent: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReservationListResponse(BaseModel):
    """Paginated reservation list"""
    items: List[ReservationResponse]
    total: int
    page: int
    page_size: int


class AvailabilitySlot(BaseModel):
    """Available time slot"""
    time: str
    available: bool


class AvailabilityResponse(BaseModel):
    """Availability check response"""
    date: str
    party_size: int
    available: bool
    slots: List[AvailabilitySlot] = []

