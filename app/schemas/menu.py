"""Menu schemas"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel


class MenuModifierCreate(BaseModel):
    """Create menu modifier"""
    name: str
    options_json: List[dict]  # [{"name": "Small", "price_cents": 0}, ...]
    is_required: bool = False
    max_selections: int = 1


class MenuModifierResponse(BaseModel):
    """Menu modifier response"""
    id: UUID
    name: str
    options_json: List[dict]
    is_required: bool
    max_selections: int

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    """Create menu item request"""
    name: str
    description: Optional[str] = None
    price_cents: int
    category: Optional[str] = None
    subcategory: Optional[str] = None
    is_active: bool = True
    dietary_info: List[str] = []
    allergens: List[str] = []
    preparation_time_minutes: Optional[int] = None
    calories: Optional[int] = None
    modifiers: List[MenuModifierCreate] = []


class MenuItemUpdate(BaseModel):
    """Update menu item request"""
    name: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None
    dietary_info: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    preparation_time_minutes: Optional[int] = None
    calories: Optional[int] = None


class MenuItemResponse(BaseModel):
    """Menu item response"""
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    price_cents: int
    category: Optional[str]
    subcategory: Optional[str]
    is_active: bool
    is_available: bool
    dietary_info: List[str]
    allergens: List[str]
    preparation_time_minutes: Optional[int]
    calories: Optional[int]
    modifiers: List[MenuModifierResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuSearchResult(BaseModel):
    """Menu search result for tools"""
    items: List[MenuItemResponse]
    total: int

