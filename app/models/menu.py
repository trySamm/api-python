"""Menu-related models"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MenuItem(Base):
    """Menu items"""
    __tablename__ = "menu_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price_cents = Column(Integer, nullable=False)  # Price in cents to avoid float issues
    category = Column(String(100))  # Appetizers, Entrees, Desserts, Drinks, etc.
    subcategory = Column(String(100))  # Pizza, Pasta, Salads, etc.
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)  # Temporary availability
    dietary_info = Column(JSON, default=list)  # ["vegetarian", "gluten-free", etc.]
    allergens = Column(JSON, default=list)  # ["nuts", "dairy", etc.]
    preparation_time_minutes = Column(Integer)
    calories = Column(Integer)
    image_url = Column(String(500))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="menu_items")
    modifiers = relationship("MenuModifier", back_populates="menu_item", cascade="all, delete-orphan")


class MenuModifier(Base):
    """Modifiers/options for menu items"""
    __tablename__ = "menu_modifiers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey("menu_items.id"), nullable=False)
    name = Column(String(100), nullable=False)  # Size, Toppings, Cooking preference
    options_json = Column(JSON, nullable=False)  # [{"name": "Small", "price_cents": 0}, ...]
    is_required = Column(Boolean, default=False)
    max_selections = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    menu_item = relationship("MenuItem", back_populates="modifiers")

