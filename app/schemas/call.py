"""Call schemas"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """Transcript segment"""
    speaker: str  # agent, customer
    text: str
    start_ms: int
    end_ms: int


class TranscriptResponse(BaseModel):
    """Transcript response"""
    id: UUID
    call_id: UUID
    text: Optional[str]
    segments: List[TranscriptSegment] = []
    entities: dict = {}
    is_final: bool
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CallResponse(BaseModel):
    """Call detail response"""
    id: UUID
    tenant_id: UUID
    call_sid: Optional[str]
    from_number: str
    to_number: str
    direction: str
    started_at: datetime
    answered_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    status: str
    outcome: Optional[str]
    escalated: bool
    escalation_reason: Optional[str]
    recording_url: Optional[str]
    summary: Optional[str]
    sentiment: Optional[str]
    transcript: Optional[TranscriptResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CallListResponse(BaseModel):
    """Paginated call list response"""
    items: List[CallResponse]
    total: int
    page: int
    page_size: int
    pages: int

