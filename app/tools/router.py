"""Tool execution API endpoints for the voice agent"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from twilio.rest import Client as TwilioClient
import structlog

from app.config import settings
from app.database import get_db
from app.models.tenant import Tenant, RestaurantSettings, StaffContact
from app.models.menu import MenuItem
from app.models.order import Order
from app.models.reservation import Reservation
from app.models.call import Call

router = APIRouter()
logger = structlog.get_logger()


# Request/Response schemas for tools
class GetContextRequest(BaseModel):
    tenant_id: str


class GetContextResponse(BaseModel):
    restaurant_name: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    phone: Optional[str]
    hours: Optional[dict]
    timezone: Optional[str]
    policies: Optional[dict]
    recording_enabled: bool = True
    escalation_number: Optional[str]


class SearchMenuRequest(BaseModel):
    tenant_id: str
    query: str


class MenuItemResult(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price_cents: int
    category: Optional[str]
    modifiers: List[dict] = []


class SearchMenuResponse(BaseModel):
    items: List[MenuItemResult]


class CreateOrderRequest(BaseModel):
    tenant_id: str
    customer_name: str
    customer_phone: str
    items: List[dict]
    pickup_time: Optional[str]
    notes: Optional[str]
    call_id: Optional[str]


class CreateOrderResponse(BaseModel):
    order_id: str
    total_cents: int
    estimated_time: Optional[str]


class CreateReservationRequest(BaseModel):
    tenant_id: str
    customer_name: str
    customer_phone: str
    party_size: int
    date_time: str
    notes: Optional[str]
    call_id: Optional[str]


class CreateReservationResponse(BaseModel):
    reservation_id: str
    confirmed_time: str


class GetAvailabilityRequest(BaseModel):
    tenant_id: str
    date: str
    time: str
    party_size: int


class GetAvailabilityResponse(BaseModel):
    available: bool
    available_times: List[str] = []


class SendSMSRequest(BaseModel):
    tenant_id: str
    to: str
    message: str


class SendSMSResponse(BaseModel):
    success: bool
    message_sid: Optional[str]


class TransferCallRequest(BaseModel):
    tenant_id: str
    phone_number: Optional[str]
    reason: Optional[str]


class TransferCallResponse(BaseModel):
    success: bool
    transfer_number: str


class CreateTicketRequest(BaseModel):
    tenant_id: str
    call_id: str
    summary: str
    transcript: Optional[str]


class CreateTicketResponse(BaseModel):
    ticket_id: str


@router.post("/get_context", response_model=GetContextResponse)
async def get_context(
    request: GetContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Get restaurant context for the AI agent"""
    logger.info("Tool: get_context", tenant_id=request.tenant_id)
    
    result = await db.execute(
        select(Tenant)
        .where(Tenant.id == UUID(request.tenant_id))
        .options(selectinload(Tenant.settings))
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    settings_obj = tenant.settings
    
    return GetContextResponse(
        restaurant_name=tenant.name,
        address=settings_obj.address if settings_obj else None,
        city=settings_obj.city if settings_obj else None,
        state=settings_obj.state if settings_obj else None,
        phone=None,  # Can be added from phone_numbers
        hours=settings_obj.hours_json if settings_obj else None,
        timezone=tenant.timezone,
        policies=settings_obj.policies_json if settings_obj else None,
        recording_enabled=settings_obj.recording_enabled if settings_obj else True,
        escalation_number=settings_obj.escalation_number if settings_obj else None,
    )


@router.post("/search_menu", response_model=SearchMenuResponse)
async def search_menu(
    request: SearchMenuRequest,
    db: AsyncSession = Depends(get_db),
):
    """Search menu items"""
    logger.info("Tool: search_menu", tenant_id=request.tenant_id, query=request.query)
    
    search_term = f"%{request.query.lower()}%"
    
    result = await db.execute(
        select(MenuItem)
        .where(
            MenuItem.tenant_id == UUID(request.tenant_id),
            MenuItem.is_active == True,
            MenuItem.is_available == True,
            or_(
                MenuItem.name.ilike(search_term),
                MenuItem.description.ilike(search_term),
                MenuItem.category.ilike(search_term),
            ),
        )
        .options(selectinload(MenuItem.modifiers))
        .limit(10)
    )
    items = result.scalars().all()
    
    return SearchMenuResponse(
        items=[
            MenuItemResult(
                id=str(item.id),
                name=item.name,
                description=item.description,
                price_cents=item.price_cents,
                category=item.category,
                modifiers=[
                    {"name": mod.name, "options": mod.options_json}
                    for mod in item.modifiers
                ],
            )
            for item in items
        ]
    )


@router.post("/create_order", response_model=CreateOrderResponse)
async def create_order(
    request: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new order"""
    logger.info(
        "Tool: create_order",
        tenant_id=request.tenant_id,
        customer=request.customer_name,
        item_count=len(request.items),
    )
    
    # Calculate totals
    subtotal = sum(
        (item.get("price_cents", 0) or 0) * item.get("quantity", 1)
        for item in request.items
    )
    tax = int(subtotal * 0.0875)
    total = subtotal + tax
    
    # Parse pickup time
    pickup_time = None
    if request.pickup_time:
        try:
            pickup_time = datetime.fromisoformat(request.pickup_time)
        except ValueError:
            # Try parsing common formats
            try:
                pickup_time = datetime.strptime(request.pickup_time, "%I:%M %p")
                pickup_time = pickup_time.replace(
                    year=datetime.now().year,
                    month=datetime.now().month,
                    day=datetime.now().day,
                )
            except ValueError:
                pass
    
    # Create order
    order = Order(
        tenant_id=UUID(request.tenant_id),
        customer_name=request.customer_name,
        customer_phone=request.customer_phone,
        items_json=request.items,
        subtotal_cents=subtotal,
        tax_cents=tax,
        total_cents=total,
        pickup_time=pickup_time,
        notes=request.notes,
        status="confirmed",
        call_id=UUID(request.call_id) if request.call_id else None,
    )
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Send confirmation SMS
    await _send_order_confirmation_sms(request.tenant_id, order, db)
    
    # Notify staff
    await _notify_staff_new_order(request.tenant_id, order, db)
    
    estimated_time = None
    if pickup_time:
        estimated_time = pickup_time.strftime("%I:%M %p")
    
    return CreateOrderResponse(
        order_id=str(order.id),
        total_cents=total,
        estimated_time=estimated_time,
    )


@router.post("/create_reservation", response_model=CreateReservationResponse)
async def create_reservation(
    request: CreateReservationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new reservation"""
    logger.info(
        "Tool: create_reservation",
        tenant_id=request.tenant_id,
        customer=request.customer_name,
        party_size=request.party_size,
    )
    
    # Parse datetime
    try:
        reservation_datetime = datetime.fromisoformat(request.date_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")
    
    # Create reservation
    reservation = Reservation(
        tenant_id=UUID(request.tenant_id),
        customer_name=request.customer_name,
        customer_phone=request.customer_phone,
        party_size=request.party_size,
        reservation_datetime=reservation_datetime,
        notes=request.notes,
        status="confirmed",
        call_id=UUID(request.call_id) if request.call_id else None,
    )
    
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    
    # Send confirmation SMS
    await _send_reservation_confirmation_sms(request.tenant_id, reservation, db)
    
    # Notify staff
    await _notify_staff_new_reservation(request.tenant_id, reservation, db)
    
    return CreateReservationResponse(
        reservation_id=str(reservation.id),
        confirmed_time=reservation_datetime.strftime("%A, %B %d at %I:%M %p"),
    )


@router.post("/get_availability", response_model=GetAvailabilityResponse)
async def get_availability(
    request: GetAvailabilityRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check reservation availability"""
    logger.info(
        "Tool: get_availability",
        tenant_id=request.tenant_id,
        date=request.date,
        time=request.time,
        party_size=request.party_size,
    )
    
    # Parse requested datetime
    try:
        requested_datetime = datetime.strptime(
            f"{request.date} {request.time}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        # Try alternative formats
        try:
            requested_datetime = datetime.strptime(
                f"{request.date} {request.time}",
                "%Y-%m-%d %I:%M %p",
            )
        except ValueError:
            return GetAvailabilityResponse(
                available=False,
                available_times=[],
            )
    
    # Simple availability check (in production, would check capacity)
    available = True
    available_times = []
    
    # Generate alternative times
    for hour_offset in [-1, 0, 1]:
        for minute_offset in [0, 30]:
            alt_time = requested_datetime + timedelta(
                hours=hour_offset,
                minutes=minute_offset - requested_datetime.minute,
            )
            if alt_time > datetime.now():
                available_times.append(alt_time.strftime("%I:%M %p"))
    
    return GetAvailabilityResponse(
        available=available,
        available_times=available_times[:6],
    )


@router.post("/send_sms", response_model=SendSMSResponse)
async def send_sms(
    request: SendSMSRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send SMS to customer"""
    logger.info(
        "Tool: send_sms",
        tenant_id=request.tenant_id,
        to=request.to[-4:],  # Log last 4 digits only
    )
    
    try:
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        
        message = client.messages.create(
            body=request.message,
            from_=settings.twilio_phone_number,
            to=request.to,
        )
        
        return SendSMSResponse(success=True, message_sid=message.sid)
        
    except Exception as e:
        logger.error("Failed to send SMS", error=str(e))
        return SendSMSResponse(success=False, message_sid=None)


@router.post("/transfer_call", response_model=TransferCallResponse)
async def transfer_call(
    request: TransferCallRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transfer call to human staff"""
    logger.info(
        "Tool: transfer_call",
        tenant_id=request.tenant_id,
        reason=request.reason,
    )
    
    # Get escalation number from settings
    transfer_number = request.phone_number
    
    if not transfer_number:
        result = await db.execute(
            select(RestaurantSettings).where(
                RestaurantSettings.tenant_id == UUID(request.tenant_id)
            )
        )
        settings_obj = result.scalar_one_or_none()
        
        if settings_obj and settings_obj.escalation_number:
            transfer_number = settings_obj.escalation_number
    
    if not transfer_number:
        raise HTTPException(status_code=400, detail="No escalation number configured")
    
    return TransferCallResponse(
        success=True,
        transfer_number=transfer_number,
    )


@router.post("/create_ticket", response_model=CreateTicketResponse)
async def create_ticket(
    request: CreateTicketRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a support ticket for follow-up"""
    logger.info(
        "Tool: create_ticket",
        tenant_id=request.tenant_id,
        call_id=request.call_id,
    )
    
    # In a real implementation, this would create a ticket in a support system
    # For now, we just log and return a mock ticket ID
    import uuid
    
    ticket_id = str(uuid.uuid4())[:8]
    
    return CreateTicketResponse(ticket_id=ticket_id)


# Helper functions
async def _send_order_confirmation_sms(
    tenant_id: str,
    order: Order,
    db: AsyncSession,
):
    """Send order confirmation SMS"""
    try:
        result = await db.execute(
            select(Tenant).where(Tenant.id == UUID(tenant_id))
        )
        tenant = result.scalar_one_or_none()
        
        message = f"Thank you for your order from {tenant.name}! "
        message += f"Order #{str(order.id)[:8]}. "
        message += f"Total: ${order.total_cents / 100:.2f}. "
        
        if order.pickup_time:
            message += f"Pickup at {order.pickup_time.strftime('%I:%M %p')}."
        
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=order.customer_phone,
        )
        
        order.confirmation_sent = datetime.utcnow()
        await db.commit()
        
    except Exception as e:
        logger.error("Failed to send order confirmation SMS", error=str(e))


async def _send_reservation_confirmation_sms(
    tenant_id: str,
    reservation: Reservation,
    db: AsyncSession,
):
    """Send reservation confirmation SMS"""
    try:
        result = await db.execute(
            select(Tenant).where(Tenant.id == UUID(tenant_id))
        )
        tenant = result.scalar_one_or_none()
        
        message = f"Your reservation at {tenant.name} is confirmed! "
        message += f"{reservation.party_size} guests on "
        message += f"{reservation.reservation_datetime.strftime('%A, %B %d at %I:%M %p')}. "
        message += "Reply to modify or cancel."
        
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=reservation.customer_phone,
        )
        
        reservation.confirmation_sent = datetime.utcnow()
        await db.commit()
        
    except Exception as e:
        logger.error("Failed to send reservation confirmation SMS", error=str(e))


async def _notify_staff_new_order(tenant_id: str, order: Order, db: AsyncSession):
    """Notify staff of new order"""
    try:
        result = await db.execute(
            select(StaffContact).where(
                StaffContact.tenant_id == UUID(tenant_id),
                StaffContact.notify_on_order == True,
                StaffContact.is_active == True,
            )
        )
        staff_contacts = result.scalars().all()
        
        message = f"New order! #{str(order.id)[:8]} - {order.customer_name}. "
        message += f"${order.total_cents / 100:.2f}. "
        
        if order.pickup_time:
            message += f"Pickup: {order.pickup_time.strftime('%I:%M %p')}"
        
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        
        for contact in staff_contacts:
            try:
                client.messages.create(
                    body=message,
                    from_=settings.twilio_phone_number,
                    to=contact.phone,
                )
            except Exception as e:
                logger.error(
                    "Failed to notify staff",
                    contact=contact.name,
                    error=str(e),
                )
                
    except Exception as e:
        logger.error("Failed to notify staff of new order", error=str(e))


async def _notify_staff_new_reservation(
    tenant_id: str,
    reservation: Reservation,
    db: AsyncSession,
):
    """Notify staff of new reservation"""
    try:
        result = await db.execute(
            select(StaffContact).where(
                StaffContact.tenant_id == UUID(tenant_id),
                StaffContact.notify_on_reservation == True,
                StaffContact.is_active == True,
            )
        )
        staff_contacts = result.scalars().all()
        
        message = f"New reservation! {reservation.customer_name}, "
        message += f"{reservation.party_size} guests. "
        message += f"{reservation.reservation_datetime.strftime('%a %m/%d %I:%M %p')}"
        
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        
        for contact in staff_contacts:
            try:
                client.messages.create(
                    body=message,
                    from_=settings.twilio_phone_number,
                    to=contact.phone,
                )
            except Exception as e:
                logger.error(
                    "Failed to notify staff",
                    contact=contact.name,
                    error=str(e),
                )
                
    except Exception as e:
        logger.error("Failed to notify staff of new reservation", error=str(e))

