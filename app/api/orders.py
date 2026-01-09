"""Order management API endpoints"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import Order
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderListResponse
from app.api.auth import get_current_active_user, verify_tenant_access

router = APIRouter()


@router.get("", response_model=OrderListResponse)
async def list_orders(
    tenant_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List orders for a tenant with pagination"""
    await verify_tenant_access(tenant_id, current_user)
    
    query = select(Order).where(Order.tenant_id == tenant_id)
    count_query = select(func.count(Order.id)).where(Order.tenant_id == tenant_id)
    
    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)
    
    if from_date:
        query = query.where(Order.created_at >= from_date)
        count_query = count_query.where(Order.created_at >= from_date)
    
    if to_date:
        query = query.where(Order.created_at <= to_date)
        count_query = count_query.where(Order.created_at <= to_date)
    
    # Get total
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    # Convert items_json to proper format
    order_responses = []
    for order in orders:
        order_dict = {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "call_id": order.call_id,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_email": order.customer_email,
            "items": order.items_json or [],
            "subtotal_cents": order.subtotal_cents,
            "tax_cents": order.tax_cents,
            "total_cents": order.total_cents,
            "pickup_time": order.pickup_time,
            "estimated_ready_time": order.estimated_ready_time,
            "status": order.status,
            "notes": order.notes,
            "special_instructions": order.special_instructions,
            "confirmation_sent": order.confirmation_sent,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }
        order_responses.append(order_dict)
    
    return OrderListResponse(
        items=order_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    tenant_id: UUID,
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new order"""
    await verify_tenant_access(tenant_id, current_user)
    
    # Calculate totals
    items_json = [item.model_dump() for item in order_data.items]
    subtotal = sum(
        (item.get("price_cents", 0) or 0) * item.get("quantity", 1)
        for item in items_json
    )
    tax = int(subtotal * 0.0875)  # 8.75% tax rate
    total = subtotal + tax
    
    order = Order(
        tenant_id=tenant_id,
        customer_name=order_data.customer_name,
        customer_phone=order_data.customer_phone,
        customer_email=order_data.customer_email,
        items_json=items_json,
        subtotal_cents=subtotal,
        tax_cents=tax,
        total_cents=total,
        pickup_time=order_data.pickup_time,
        notes=order_data.notes,
        special_instructions=order_data.special_instructions,
        call_id=order_data.call_id,
    )
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        call_id=order.call_id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_email=order.customer_email,
        items=order.items_json,
        subtotal_cents=order.subtotal_cents,
        tax_cents=order.tax_cents,
        total_cents=order.total_cents,
        pickup_time=order.pickup_time,
        estimated_ready_time=order.estimated_ready_time,
        status=order.status,
        notes=order.notes,
        special_instructions=order.special_instructions,
        confirmation_sent=order.confirmation_sent,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    tenant_id: UUID,
    order_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get order details"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        call_id=order.call_id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_email=order.customer_email,
        items=order.items_json,
        subtotal_cents=order.subtotal_cents,
        tax_cents=order.tax_cents,
        total_cents=order.total_cents,
        pickup_time=order.pickup_time,
        estimated_ready_time=order.estimated_ready_time,
        status=order.status,
        notes=order.notes,
        special_instructions=order.special_instructions,
        confirmation_sent=order.confirmation_sent,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    tenant_id: UUID,
    order_id: UUID,
    order_data: OrderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update order status or details"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    for field, value in order_data.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    
    await db.commit()
    await db.refresh(order)
    
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        call_id=order.call_id,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_email=order.customer_email,
        items=order.items_json,
        subtotal_cents=order.subtotal_cents,
        tax_cents=order.tax_cents,
        total_cents=order.total_cents,
        pickup_time=order.pickup_time,
        estimated_ready_time=order.estimated_ready_time,
        status=order.status,
        notes=order.notes,
        special_instructions=order.special_instructions,
        confirmation_sent=order.confirmation_sent,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

