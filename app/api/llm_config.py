"""LLM configuration API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.tenant import LLMConfigUpdate, LLMConfigResponse
from app.api.auth import get_current_active_user, verify_tenant_access

router = APIRouter()


AVAILABLE_PROVIDERS = ["openai", "anthropic", "gemini", "azure_openai", "ollama"]

AVAILABLE_MODELS = {
    "openai": ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
    "azure_openai": [],  # Configured per deployment
    "ollama": ["llama2", "llama3", "mistral", "mixtral", "codellama"],
}


@router.get("", response_model=LLMConfigResponse)
async def get_llm_config(
    tenant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get LLM configuration for a tenant"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return LLMConfigResponse(
        tenant_id=tenant.id,
        llm_provider=tenant.llm_provider,
        llm_model=tenant.llm_model,
        fallback_llm_provider=tenant.fallback_llm_provider,
        fallback_llm_model=tenant.fallback_llm_model,
        available_providers=AVAILABLE_PROVIDERS,
    )


@router.put("", response_model=LLMConfigResponse)
async def update_llm_config(
    tenant_id: UUID,
    config: LLMConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update LLM configuration for a tenant"""
    await verify_tenant_access(tenant_id, current_user)
    
    if not current_user.has_permission(UserRole.RESTAURANT_ADMIN):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Validate provider
    if config.llm_provider and config.llm_provider not in AVAILABLE_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Available: {AVAILABLE_PROVIDERS}",
        )
    
    if config.fallback_llm_provider and config.fallback_llm_provider not in AVAILABLE_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fallback provider. Available: {AVAILABLE_PROVIDERS}",
        )
    
    # Update configuration
    for field, value in config.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    
    await db.commit()
    await db.refresh(tenant)
    
    return LLMConfigResponse(
        tenant_id=tenant.id,
        llm_provider=tenant.llm_provider,
        llm_model=tenant.llm_model,
        fallback_llm_provider=tenant.fallback_llm_provider,
        fallback_llm_model=tenant.fallback_llm_model,
        available_providers=AVAILABLE_PROVIDERS,
    )


@router.get("/models")
async def get_available_models(
    tenant_id: UUID,
    provider: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get available models for a provider"""
    if provider not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {
        "provider": provider,
        "models": AVAILABLE_MODELS[provider],
    }

