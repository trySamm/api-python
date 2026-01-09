"""Tenant schemas"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel


class TenantCreate(BaseModel):
    """Create tenant request"""
    name: str
    timezone: str = "America/New_York"


class TenantUpdate(BaseModel):
    """Update tenant request"""
    name: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Tenant response"""
    id: UUID
    name: str
    timezone: str
    is_active: bool
    llm_provider: str
    llm_model: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RestaurantSettingsUpdate(BaseModel):
    """Update restaurant settings"""
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    hours_json: Optional[Dict[str, Any]] = None
    policies_json: Optional[Dict[str, Any]] = None
    recording_enabled: Optional[bool] = None
    escalation_number: Optional[str] = None
    greeting_message: Optional[str] = None
    max_party_size: Optional[str] = None
    reservation_slot_minutes: Optional[str] = None


class RestaurantSettingsResponse(BaseModel):
    """Restaurant settings response"""
    id: UUID
    tenant_id: UUID
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    hours_json: Dict[str, Any]
    policies_json: Dict[str, Any]
    recording_enabled: bool
    escalation_number: Optional[str]
    greeting_message: Optional[str]
    max_party_size: str
    reservation_slot_minutes: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LLMConfigUpdate(BaseModel):
    """Update LLM configuration"""
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    fallback_llm_provider: Optional[str] = None
    fallback_llm_model: Optional[str] = None


class LLMConfigResponse(BaseModel):
    """LLM configuration response"""
    tenant_id: UUID
    llm_provider: str
    llm_model: str
    fallback_llm_provider: str
    fallback_llm_model: str
    available_providers: List[str] = ["openai", "anthropic", "gemini", "ollama"]

    class Config:
        from_attributes = True

