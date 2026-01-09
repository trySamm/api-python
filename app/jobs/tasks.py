"""Background job tasks"""

from datetime import datetime, timedelta
from uuid import UUID
import asyncio
import structlog

from app.jobs.celery_app import celery_app
from app.config import settings

logger = structlog.get_logger()


def run_async(coro):
    """Helper to run async functions in sync context"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(name="finalize_transcript")
def finalize_transcript(call_id: str):
    """Finalize call transcript after call ends"""
    logger.info("Finalizing transcript", call_id=call_id)
    
    async def _finalize():
        from app.database import SessionLocal
        from app.models.call import Call, Transcript
        from sqlalchemy import select
        
        async with SessionLocal() as db:
            result = await db.execute(
                select(Transcript).where(Transcript.call_id == UUID(call_id))
            )
            transcript = result.scalar_one_or_none()
            
            if transcript:
                transcript.is_final = True
                transcript.processed_at = datetime.utcnow()
                await db.commit()
                
                logger.info("Transcript finalized", call_id=call_id)
    
    run_async(_finalize())


@celery_app.task(name="generate_call_summary")
def generate_call_summary(call_id: str):
    """Generate AI summary of the call"""
    logger.info("Generating call summary", call_id=call_id)
    
    async def _generate():
        from app.database import SessionLocal
        from app.models.call import Call, Transcript
        from app.llm.adapter import LLMAdapter
        from app.schemas.llm import LLMMessage
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        async with SessionLocal() as db:
            result = await db.execute(
                select(Call)
                .where(Call.id == UUID(call_id))
                .options(selectinload(Call.transcript))
            )
            call = result.scalar_one_or_none()
            
            if not call or not call.transcript:
                return
            
            # Generate summary using LLM
            adapter = LLMAdapter(
                provider="openai",
                model="gpt-3.5-turbo",
            )
            
            transcript_text = call.transcript.text or ""
            
            if len(transcript_text) < 50:
                call.summary = "Brief call - no significant content"
                await db.commit()
                return
            
            response = await adapter.generate(
                system_prompt="Summarize this phone call transcript in 2-3 sentences. Focus on the outcome and any actions taken.",
                messages=[
                    LLMMessage(
                        role="user",
                        content=f"Transcript:\n{transcript_text[:4000]}",
                    )
                ],
                tools=[],
                temperature=0.3,
                max_tokens=200,
            )
            
            if response.content:
                call.summary = response.content
                
                # Simple sentiment analysis
                lower_summary = response.content.lower()
                if any(word in lower_summary for word in ["successfully", "completed", "confirmed", "happy"]):
                    call.sentiment = "positive"
                elif any(word in lower_summary for word in ["frustrated", "cancelled", "complaint", "issue"]):
                    call.sentiment = "negative"
                else:
                    call.sentiment = "neutral"
                
                await db.commit()
                logger.info("Call summary generated", call_id=call_id)
    
    run_async(_generate())


@celery_app.task(name="send_reservation_reminders")
def send_reservation_reminders():
    """Send reminders for upcoming reservations"""
    logger.info("Sending reservation reminders")
    
    async def _send_reminders():
        from app.database import SessionLocal
        from app.models.reservation import Reservation
        from app.models.tenant import Tenant
        from twilio.rest import Client as TwilioClient
        from sqlalchemy import select, and_
        
        # Find reservations coming up in the next 2-4 hours that haven't been reminded
        now = datetime.utcnow()
        reminder_start = now + timedelta(hours=2)
        reminder_end = now + timedelta(hours=4)
        
        async with SessionLocal() as db:
            result = await db.execute(
                select(Reservation).where(
                    and_(
                        Reservation.reservation_datetime.between(reminder_start, reminder_end),
                        Reservation.status == "confirmed",
                        Reservation.reminder_sent.is_(None),
                    )
                )
            )
            reservations = result.scalars().all()
            
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            
            for reservation in reservations:
                try:
                    # Get tenant name
                    tenant_result = await db.execute(
                        select(Tenant).where(Tenant.id == reservation.tenant_id)
                    )
                    tenant = tenant_result.scalar_one_or_none()
                    
                    message = f"Reminder: Your reservation at {tenant.name} is coming up! "
                    message += f"{reservation.party_size} guests at "
                    message += f"{reservation.reservation_datetime.strftime('%I:%M %p')}. "
                    message += "See you soon!"
                    
                    client.messages.create(
                        body=message,
                        from_=settings.twilio_phone_number,
                        to=reservation.customer_phone,
                    )
                    
                    reservation.reminder_sent = datetime.utcnow()
                    await db.commit()
                    
                    logger.info(
                        "Sent reservation reminder",
                        reservation_id=str(reservation.id),
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to send reservation reminder",
                        reservation_id=str(reservation.id),
                        error=str(e),
                    )
    
    run_async(_send_reminders())


@celery_app.task(name="cleanup_old_calls")
def cleanup_old_calls():
    """Clean up old call data (older than 90 days)"""
    logger.info("Cleaning up old calls")
    
    async def _cleanup():
        from app.database import SessionLocal
        from app.models.call import Call
        from sqlalchemy import delete
        
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        async with SessionLocal() as db:
            # Note: In production, you might want to archive instead of delete
            # and handle recordings separately
            result = await db.execute(
                delete(Call).where(Call.started_at < cutoff_date)
            )
            deleted_count = result.rowcount
            await db.commit()
            
            logger.info("Cleaned up old calls", deleted_count=deleted_count)
    
    run_async(_cleanup())

