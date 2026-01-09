"""Tenant management API endpoints"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.tenant import Tenant, RestaurantSettings
from app.models.user import User, UserRole
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    RestaurantSettingsUpdate,
    RestaurantSettingsResponse,
)
from app.api.auth import get_current_active_user, require_role, verify_tenant_access

router = APIRouter()


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all tenants (SuperAdmin only)"""
    result = await db.execute(
        select(Tenant)
        .where(Tenant.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tenant (SuperAdmin only)"""
    tenant = Tenant(**tenant_data.model_dump())
    db.add(tenant)
    await db.flush()
    
    # Create default settings
    settings = RestaurantSettings(
        tenant_id=tenant.id,
        hours_json={
            "monday": {"open": "11:00", "close": "22:00"},
            "tuesday": {"open": "11:00", "close": "22:00"},
            "wednesday": {"open": "11:00", "close": "22:00"},
            "thursday": {"open": "11:00", "close": "22:00"},
            "friday": {"open": "11:00", "close": "23:00"},
            "saturday": {"open": "11:00", "close": "23:00"},
            "sunday": {"open": "12:00", "close": "21:00"},
        },
        policies_json={},
    )
    db.add(settings)
    await db.commit()
    await db.refresh(tenant)
    
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tenant details"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant"""
    await verify_tenant_access(tenant_id, current_user)
    
    # Require admin role for tenant updates
    if not current_user.has_permission(UserRole.RESTAURANT_ADMIN):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    for field, value in tenant_data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    
    await db.commit()
    await db.refresh(tenant)
    
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete tenant (soft delete - SuperAdmin only)"""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant.is_active = False
    await db.commit()


@router.get("/{tenant_id}/settings", response_model=RestaurantSettingsResponse)
async def get_tenant_settings(
    tenant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get restaurant settings"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.tenant_id == tenant_id)
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    return settings


@router.put("/{tenant_id}/settings", response_model=RestaurantSettingsResponse)
async def update_tenant_settings(
    tenant_id: UUID,
    settings_data: RestaurantSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update restaurant settings"""
    await verify_tenant_access(tenant_id, current_user)
    
    if not current_user.has_permission(UserRole.RESTAURANT_ADMIN):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    result = await db.execute(
        select(RestaurantSettings).where(RestaurantSettings.tenant_id == tenant_id)
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    for field, value in settings_data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    
    await db.commit()
    await db.refresh(settings)
    
    return settings

