"""Order schemas"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


class OrderItemCreate(BaseModel):
    """Create order item"""
    item_id: Optional[UUID] = None
    name: str
    quantity: int = 1
    modifiers: List[str] = []
    price_cents: Optional[int] = None
    notes: Optional[str] = None


class OrderCreate(BaseModel):
    """Create order request"""
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    items: List[OrderItemCreate]
    pickup_time: Optional[datetime] = None
    notes: Optional[str] = None
    special_instructions: Optional[str] = None
    call_id: Optional[UUID] = None


class OrderUpdate(BaseModel):
    """Update order request"""
    status: Optional[str] = None
    pickup_time: Optional[datetime] = None
    estimated_ready_time: Optional[datetime] = None
    notes: Optional[str] = None
    special_instructions: Optional[str] = None


class OrderItemResponse(BaseModel):
    """Order item in response"""
    item_id: Optional[UUID]
    name: str
    quantity: int
    modifiers: List[str]
    price_cents: int
    notes: Optional[str]


class OrderResponse(BaseModel):
    """Order response"""
    id: UUID
    tenant_id: UUID
    call_id: Optional[UUID]
    customer_name: str
    customer_phone: str
    customer_email: Optional[str]
    items: List[OrderItemResponse]
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    pickup_time: Optional[datetime]
    estimated_ready_time: Optional[datetime]
    status: str
    notes: Optional[str]
    special_instructions: Optional[str]
    confirmation_sent: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Paginated order list"""
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int

