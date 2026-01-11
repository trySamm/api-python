"""Reservation management API endpoints"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import (
    ReservationCreate,
    ReservationUpdate,
    ReservationResponse,
    ReservationListResponse,
    AvailabilityResponse,
    AvailabilitySlot,
)
from app.api.auth import get_current_active_user, verify_tenant_access

router = APIRouter()


@router.get("", response_model=ReservationListResponse)
async def list_reservations(
    tenant_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List reservations for a tenant with pagination"""
    await verify_tenant_access(tenant_id, current_user)
    
    query = select(Reservation).where(Reservation.tenant_id == tenant_id)
    count_query = select(func.count(Reservation.id)).where(Reservation.tenant_id == tenant_id)
    
    if status:
        query = query.where(Reservation.status == status)
        count_query = count_query.where(Reservation.status == status)
    
    if from_date:
        query = query.where(Reservation.reservation_datetime >= from_date)
        count_query = count_query.where(Reservation.reservation_datetime >= from_date)
    
    if to_date:
        query = query.where(Reservation.reservation_datetime <= to_date)
        count_query = count_query.where(Reservation.reservation_datetime <= to_date)
    
    # Get total
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Reservation.reservation_datetime.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    reservations = result.scalars().all()
    
    return ReservationListResponse(
        items=reservations,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    tenant_id: UUID,
    reservation_data: ReservationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new reservation"""
    await verify_tenant_access(tenant_id, current_user)
    
    reservation = Reservation(
        tenant_id=tenant_id,
        customer_name=reservation_data.customer_name,
        customer_phone=reservation_data.customer_phone,
        customer_email=reservation_data.customer_email,
        party_size=reservation_data.party_size,
        reservation_datetime=reservation_data.reservation_datetime,
        notes=reservation_data.notes,
        special_requests=reservation_data.special_requests,
        call_id=reservation_data.call_id,
        status="confirmed",
    )
    
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    
    return reservation


@router.get("/availability/check", response_model=AvailabilityResponse)
async def check_availability(
    tenant_id: UUID,
    date: str,
    time: str,
    party_size: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check reservation availability"""
    await verify_tenant_access(tenant_id, current_user)

    # Parse date and time
    try:
        requested_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time format")

    # Check existing reservations for that time slot
    slot_start = requested_datetime - timedelta(minutes=30)
    slot_end = requested_datetime + timedelta(minutes=30)

    result = await db.execute(
        select(func.count(Reservation.id)).where(
            Reservation.tenant_id == tenant_id,
            Reservation.status.in_(["pending", "confirmed"]),
            Reservation.reservation_datetime.between(slot_start, slot_end),
        )
    )
    existing_count = result.scalar()

    # Simple availability logic (max 10 reservations per slot)
    max_reservations = 10
    available = existing_count < max_reservations

    # Generate alternative slots if not available
    slots = []
    for hour_offset in range(-2, 3):
        for minute_offset in [0, 30]:
            alt_time = requested_datetime + timedelta(hours=hour_offset, minutes=minute_offset)
            if alt_time > datetime.now():
                slots.append(AvailabilitySlot(
                    time=alt_time.strftime("%H:%M"),
                    available=True,  # Simplified
                ))

    return AvailabilityResponse(
        date=date,
        party_size=party_size,
        available=available,
        slots=slots,
    )


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    tenant_id: UUID,
    reservation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get reservation details"""
    await verify_tenant_access(tenant_id, current_user)

    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id,
        )
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    return reservation


@router.put("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    tenant_id: UUID,
    reservation_id: UUID,
    reservation_data: ReservationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update reservation"""
    await verify_tenant_access(tenant_id, current_user)

    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id,
        )
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    for field, value in reservation_data.model_dump(exclude_unset=True).items():
        setattr(reservation, field, value)

    await db.commit()
    await db.refresh(reservation)

    return reservation


@router.delete("/{reservation_id}", status_code=204)
async def cancel_reservation(
    tenant_id: UUID,
    reservation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a reservation"""
    await verify_tenant_access(tenant_id, current_user)

    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id,
        )
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation.status = "cancelled"
    await db.commit()

