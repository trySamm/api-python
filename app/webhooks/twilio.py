"""Twilio webhook handlers"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.voice_response import VoiceResponse, Connect
import structlog

from app.config import settings
from app.database import get_db
from app.models.tenant import PhoneNumber
from app.models.call import Call

router = APIRouter()
logger = structlog.get_logger()


@router.post("/voice")
async def handle_voice_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: str = Form(...),
    Direction: str = Form(default="inbound"),
    AccountSid: str = Form(default=""),
):
    """
    Handle incoming voice call from Twilio.
    Returns TwiML to connect to the media stream.
    """
    logger.info(
        "Incoming call",
        call_sid=CallSid,
        from_number=From,
        to_number=To,
        status=CallStatus,
    )
    
    # Find tenant by called number
    result = await db.execute(
        select(PhoneNumber).where(PhoneNumber.e164 == To, PhoneNumber.is_active == True)
    )
    phone_number = result.scalar_one_or_none()
    
    if not phone_number:
        logger.warning("Unknown phone number", to_number=To)
        response = VoiceResponse()
        response.say("Sorry, this number is not configured. Goodbye.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    
    tenant_id = phone_number.tenant_id
    
    # Create call record
    call = Call(
        tenant_id=tenant_id,
        call_sid=CallSid,
        from_number=From,
        to_number=To,
        direction=Direction,
        status="initiated",
        started_at=datetime.utcnow(),
    )
    db.add(call)
    await db.commit()
    
    logger.info(
        "Call record created",
        call_id=str(call.id),
        tenant_id=str(tenant_id),
    )
    
    # Generate TwiML to connect to media stream
    response = VoiceResponse()
    
    # Connect to the media stream WebSocket
    connect = Connect()
    
    # Use the call gateway URL
    gateway_url = settings.call_gateway_url.replace("http://", "ws://").replace("https://", "wss://")
    stream_url = f"{gateway_url}/media-stream"
    
    stream = connect.stream(url=stream_url)
    stream.parameter(name="tenant_id", value=str(tenant_id))
    stream.parameter(name="call_id", value=str(call.id))
    
    response.append(connect)
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def handle_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: Optional[str] = Form(default=None),
    RecordingUrl: Optional[str] = Form(default=None),
    RecordingDuration: Optional[str] = Form(default=None),
):
    """Handle call status updates from Twilio"""
    logger.info(
        "Call status update",
        call_sid=CallSid,
        status=CallStatus,
        duration=CallDuration,
    )
    
    # Find call by SID
    result = await db.execute(select(Call).where(Call.call_sid == CallSid))
    call = result.scalar_one_or_none()
    
    if not call:
        logger.warning("Call not found", call_sid=CallSid)
        return {"status": "ok"}
    
    # Update call status
    call.status = CallStatus
    
    if CallStatus in ["completed", "failed", "busy", "no-answer", "canceled"]:
        call.ended_at = datetime.utcnow()
        
        if CallDuration:
            call.duration_seconds = int(CallDuration)
    
    if RecordingUrl:
        call.recording_url = RecordingUrl
        
        if RecordingDuration:
            call.recording_duration_seconds = int(RecordingDuration)
    
    await db.commit()
    
    # Trigger background jobs if call completed
    if CallStatus == "completed":
        from app.jobs.celery_app import celery_app
        
        # Finalize transcript
        celery_app.send_task("finalize_transcript", args=[str(call.id)])
        
        # Generate summary
        celery_app.send_task("generate_call_summary", args=[str(call.id)])
    
    return {"status": "ok"}


@router.post("/recording")
async def handle_recording_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    CallSid: str = Form(...),
    RecordingUrl: str = Form(...),
    RecordingDuration: str = Form(...),
    RecordingSid: str = Form(...),
):
    """Handle recording completion webhook"""
    logger.info(
        "Recording ready",
        call_sid=CallSid,
        recording_sid=RecordingSid,
        duration=RecordingDuration,
    )
    
    result = await db.execute(select(Call).where(Call.call_sid == CallSid))
    call = result.scalar_one_or_none()
    
    if call:
        call.recording_url = RecordingUrl
        call.recording_duration_seconds = int(RecordingDuration)
        await db.commit()
    
    return {"status": "ok"}

