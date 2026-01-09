"""Menu management API endpoints"""

from typing import List, Optional
from uuid import UUID
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.menu import MenuItem, MenuModifier
from app.models.user import User, UserRole
from app.schemas.menu import (
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemResponse,
    MenuSearchResult,
)
from app.api.auth import get_current_active_user, verify_tenant_access

router = APIRouter()


@router.get("", response_model=List[MenuItemResponse])
async def list_menu_items(
    tenant_id: UUID,
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List menu items for a tenant"""
    await verify_tenant_access(tenant_id, current_user)
    
    query = select(MenuItem).where(MenuItem.tenant_id == tenant_id)
    
    if category:
        query = query.where(MenuItem.category == category)
    
    if is_active is not None:
        query = query.where(MenuItem.is_active == is_active)
    
    query = query.options(selectinload(MenuItem.modifiers))
    query = query.order_by(MenuItem.category, MenuItem.sort_order, MenuItem.name)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=MenuItemResponse, status_code=201)
async def create_menu_item(
    tenant_id: UUID,
    item_data: MenuItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu item"""
    await verify_tenant_access(tenant_id, current_user)
    
    if not current_user.has_permission(UserRole.RESTAURANT_ADMIN):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Create menu item
    item_dict = item_data.model_dump(exclude={"modifiers"})
    item = MenuItem(tenant_id=tenant_id, **item_dict)
    db.add(item)
    await db.flush()
    
    # Create modifiers
    for mod_data in item_data.modifiers:
        modifier = MenuModifier(
            tenant_id=tenant_id,
            menu_item_id=item.id,
            **mod_data.model_dump(),
        )
        db.add(modifier)
    
    await db.commit()
    await db.refresh(item)
    
    # Reload with modifiers
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.id == item.id)
        .options(selectinload(MenuItem.modifiers))
    )
    return result.scalar_one()


@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    tenant_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific menu item"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.id == item_id, MenuItem.tenant_id == tenant_id)
        .options(selectinload(MenuItem.modifiers))
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    return item


@router.put("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    tenant_id: UUID,
    item_id: UUID,
    item_data: MenuItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a menu item"""
    await verify_tenant_access(tenant_id, current_user)
    
    if not current_user.has_permission(UserRole.RESTAURANT_ADMIN):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.id == item_id, MenuItem.tenant_id == tenant_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    for field, value in item_data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    
    await db.commit()
    
    # Reload with modifiers
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.id == item.id)
        .options(selectinload(MenuItem.modifiers))
    )
    return result.scalar_one()


@router.delete("/{item_id}", status_code=204)
async def delete_menu_item(
    tenant_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a menu item (soft delete)"""
    await verify_tenant_access(tenant_id, current_user)
    
    if not current_user.has_permission(UserRole.RESTAURANT_ADMIN):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.id == item_id, MenuItem.tenant_id == tenant_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    item.is_active = False
    await db.commit()


@router.post("/import_csv")
async def import_menu_from_csv(
    tenant_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Import menu items from CSV file"""
    await verify_tenant_access(tenant_id, current_user)
    
    if not current_user.has_permission(UserRole.RESTAURANT_ADMIN):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    
    items_created = 0
    errors = []
    
    for row_num, row in enumerate(reader, start=2):
        try:
            item = MenuItem(
                tenant_id=tenant_id,
                name=row["name"],
                description=row.get("description"),
                price_cents=int(row["price_cents"]),
                category=row.get("category"),
                is_active=row.get("is_active", "true").lower() == "true",
            )
            db.add(item)
            items_created += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    await db.commit()
    
    return {
        "items_created": items_created,
        "errors": errors,
    }


@router.get("/search", response_model=MenuSearchResult)
async def search_menu(
    tenant_id: UUID,
    query: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Search menu items by name or description"""
    await verify_tenant_access(tenant_id, current_user)
    
    search_term = f"%{query.lower()}%"
    
    result = await db.execute(
        select(MenuItem)
        .where(
            MenuItem.tenant_id == tenant_id,
            MenuItem.is_active == True,
            or_(
                MenuItem.name.ilike(search_term),
                MenuItem.description.ilike(search_term),
                MenuItem.category.ilike(search_term),
            ),
        )
        .options(selectinload(MenuItem.modifiers))
        .limit(20)
    )
    items = result.scalars().all()
    
    return MenuSearchResult(items=items, total=len(items))

