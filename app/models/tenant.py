"""Tenant-related models"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Tenant(Base):
    """Restaurant tenant"""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    timezone = Column(String(50), default="America/New_York")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # LLM Configuration
    llm_provider = Column(String(50), default="openai")
    llm_model = Column(String(100), default="gpt-4-turbo")
    fallback_llm_provider = Column(String(50), default="anthropic")
    fallback_llm_model = Column(String(100), default="claude-3-sonnet-20240229")
    
    # Relationships
    settings = relationship("RestaurantSettings", back_populates="tenant", uselist=False)
    phone_numbers = relationship("PhoneNumber", back_populates="tenant")
    staff_contacts = relationship("StaffContact", back_populates="tenant")
    menu_items = relationship("MenuItem", back_populates="tenant")
    calls = relationship("Call", back_populates="tenant")
    orders = relationship("Order", back_populates="tenant")
    reservations = relationship("Reservation", back_populates="tenant")
    users = relationship("User", back_populates="tenant")


class PhoneNumber(Base):
    """Phone numbers associated with tenants"""
    __tablename__ = "phone_numbers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    e164 = Column(String(20), unique=True, nullable=False)  # E.164 format: +15551234567
    provider = Column(String(50), default="twilio")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="phone_numbers")


class RestaurantSettings(Base):
    """Restaurant-specific settings"""
    __tablename__ = "restaurant_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), unique=True, nullable=False)
    
    # Business information
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    
    # Operating hours (JSON: {"monday": {"open": "09:00", "close": "21:00"}, ...})
    hours_json = Column(JSON, default=dict)
    
    # Policies and information
    policies_json = Column(JSON, default=dict)  # Cancellation, dietary, parking, etc.
    
    # Call settings
    recording_enabled = Column(Boolean, default=True)
    escalation_number = Column(String(20))  # Number to transfer calls to
    greeting_message = Column(Text)
    
    # Reservation settings
    max_party_size = Column(String(10), default="10")
    reservation_slot_minutes = Column(String(10), default="30")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="settings")


class StaffContact(Base):
    """Staff contacts for notifications"""
    __tablename__ = "staff_contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255))
    role = Column(String(50))  # manager, host, kitchen
    notify_on_order = Column(Boolean, default=True)
    notify_on_reservation = Column(Boolean, default=True)
    notify_on_escalation = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="staff_contacts")

