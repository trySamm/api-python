"""Call history API endpoints"""

from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.call import Call, Transcript
from app.models.user import User
from app.schemas.call import CallResponse, CallListResponse, TranscriptResponse
from app.api.auth import get_current_active_user, verify_tenant_access

router = APIRouter()


@router.get("", response_model=CallListResponse)
async def list_calls(
    tenant_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List calls for a tenant with pagination and filtering"""
    await verify_tenant_access(tenant_id, current_user)
    
    # Build query
    query = select(Call).where(Call.tenant_id == tenant_id)
    count_query = select(func.count(Call.id)).where(Call.tenant_id == tenant_id)
    
    if status:
        query = query.where(Call.status == status)
        count_query = count_query.where(Call.status == status)
    
    if outcome:
        query = query.where(Call.outcome == outcome)
        count_query = count_query.where(Call.outcome == outcome)
    
    if from_date:
        query = query.where(Call.started_at >= from_date)
        count_query = count_query.where(Call.started_at >= from_date)
    
    if to_date:
        query = query.where(Call.started_at <= to_date)
        count_query = count_query.where(Call.started_at <= to_date)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Call.started_at.desc()).offset(offset).limit(page_size)
    query = query.options(selectinload(Call.transcript))
    
    result = await db.execute(query)
    calls = result.scalars().all()
    
    return CallListResponse(
        items=calls,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    tenant_id: UUID,
    call_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get call details with transcript"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(
        select(Call)
        .where(Call.id == call_id, Call.tenant_id == tenant_id)
        .options(selectinload(Call.transcript))
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return call


@router.get("/{call_id}/transcript", response_model=TranscriptResponse)
async def get_call_transcript(
    tenant_id: UUID,
    call_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get call transcript"""
    await verify_tenant_access(tenant_id, current_user)
    
    result = await db.execute(
        select(Transcript).where(
            Transcript.call_id == call_id,
            Transcript.tenant_id == tenant_id,
        )
    )
    transcript = result.scalar_one_or_none()
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    return TranscriptResponse(
        id=transcript.id,
        call_id=transcript.call_id,
        text=transcript.text,
        segments=transcript.segments_json or [],
        entities=transcript.entities_json or {},
        is_final=transcript.is_final,
        processed_at=transcript.processed_at,
    )


@router.get("/stats/summary")
async def get_call_stats(
    tenant_id: UUID,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get call statistics summary"""
    await verify_tenant_access(tenant_id, current_user)
    
    # Base query
    base_query = select(Call).where(Call.tenant_id == tenant_id)
    
    if from_date:
        base_query = base_query.where(Call.started_at >= from_date)
    if to_date:
        base_query = base_query.where(Call.started_at <= to_date)
    
    # Total calls
    total_result = await db.execute(
        select(func.count(Call.id)).where(Call.tenant_id == tenant_id)
    )
    total_calls = total_result.scalar()
    
    # Escalated calls
    escalated_result = await db.execute(
        select(func.count(Call.id)).where(
            Call.tenant_id == tenant_id,
            Call.escalated == True,
        )
    )
    escalated_calls = escalated_result.scalar()
    
    # Average duration
    avg_duration_result = await db.execute(
        select(func.avg(Call.duration_seconds)).where(
            Call.tenant_id == tenant_id,
            Call.duration_seconds.isnot(None),
        )
    )
    avg_duration = avg_duration_result.scalar() or 0
    
    # Outcome breakdown
    outcome_result = await db.execute(
        select(Call.outcome, func.count(Call.id))
        .where(Call.tenant_id == tenant_id, Call.outcome.isnot(None))
        .group_by(Call.outcome)
    )
    outcomes = {row[0]: row[1] for row in outcome_result.fetchall()}
    
    return {
        "total_calls": total_calls,
        "escalated_calls": escalated_calls,
        "escalation_rate": escalated_calls / total_calls if total_calls > 0 else 0,
        "avg_duration_seconds": round(avg_duration, 1),
        "outcomes": outcomes,
    }

