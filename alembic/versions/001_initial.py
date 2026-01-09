"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('timezone', sa.String(50), default='America/New_York'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('llm_provider', sa.String(50), default='openai'),
        sa.Column('llm_model', sa.String(100), default='gpt-4-turbo'),
        sa.Column('fallback_llm_provider', sa.String(50), default='anthropic'),
        sa.Column('fallback_llm_model', sa.String(100), default='claude-3-sonnet-20240229'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('role', sa.String(50), default='staff_viewer'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('refresh_token', sa.String(500)),
        sa.Column('last_login', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create phone_numbers table
    op.create_table(
        'phone_numbers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('e164', sa.String(20), unique=True, nullable=False),
        sa.Column('provider', sa.String(50), default='twilio'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create restaurant_settings table
    op.create_table(
        'restaurant_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), unique=True, nullable=False),
        sa.Column('address', sa.Text()),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(50)),
        sa.Column('zip_code', sa.String(20)),
        sa.Column('hours_json', postgresql.JSON(), default={}),
        sa.Column('policies_json', postgresql.JSON(), default={}),
        sa.Column('recording_enabled', sa.Boolean(), default=True),
        sa.Column('escalation_number', sa.String(20)),
        sa.Column('greeting_message', sa.Text()),
        sa.Column('max_party_size', sa.String(10), default='10'),
        sa.Column('reservation_slot_minutes', sa.String(10), default='30'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create staff_contacts table
    op.create_table(
        'staff_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255)),
        sa.Column('role', sa.String(50)),
        sa.Column('notify_on_order', sa.Boolean(), default=True),
        sa.Column('notify_on_reservation', sa.Boolean(), default=True),
        sa.Column('notify_on_escalation', sa.Boolean(), default=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create menu_items table
    op.create_table(
        'menu_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('subcategory', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_available', sa.Boolean(), default=True),
        sa.Column('dietary_info', postgresql.JSON(), default=[]),
        sa.Column('allergens', postgresql.JSON(), default=[]),
        sa.Column('preparation_time_minutes', sa.Integer()),
        sa.Column('calories', sa.Integer()),
        sa.Column('image_url', sa.String(500)),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create menu_modifiers table
    op.create_table(
        'menu_modifiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('menu_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('menu_items.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('options_json', postgresql.JSON(), nullable=False),
        sa.Column('is_required', sa.Boolean(), default=False),
        sa.Column('max_selections', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create calls table
    op.create_table(
        'calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('call_sid', sa.String(50), unique=True),
        sa.Column('stream_sid', sa.String(50)),
        sa.Column('from_number', sa.String(20), nullable=False),
        sa.Column('to_number', sa.String(20), nullable=False),
        sa.Column('direction', sa.String(20), default='inbound'),
        sa.Column('started_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('answered_at', sa.DateTime()),
        sa.Column('ended_at', sa.DateTime()),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('status', sa.String(50), default='initiated'),
        sa.Column('outcome', sa.String(50)),
        sa.Column('escalated', sa.Boolean(), default=False),
        sa.Column('escalation_reason', sa.Text()),
        sa.Column('recording_url', sa.String(500)),
        sa.Column('recording_duration_seconds', sa.Integer()),
        sa.Column('summary', sa.Text()),
        sa.Column('sentiment', sa.String(20)),
        sa.Column('metadata_json', postgresql.JSON(), default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id'), unique=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('text', sa.Text()),
        sa.Column('segments_json', postgresql.JSON(), default=[]),
        sa.Column('entities_json', postgresql.JSON(), default={}),
        sa.Column('is_final', sa.Boolean(), default=False),
        sa.Column('processed_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id')),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('customer_email', sa.String(255)),
        sa.Column('items_json', postgresql.JSON(), nullable=False),
        sa.Column('subtotal_cents', sa.Integer(), nullable=False, default=0),
        sa.Column('tax_cents', sa.Integer(), default=0),
        sa.Column('total_cents', sa.Integer(), nullable=False, default=0),
        sa.Column('pickup_time', sa.DateTime()),
        sa.Column('estimated_ready_time', sa.DateTime()),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('notes', sa.Text()),
        sa.Column('special_instructions', sa.Text()),
        sa.Column('confirmation_sent', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create reservations table
    op.create_table(
        'reservations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id')),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('customer_email', sa.String(255)),
        sa.Column('party_size', sa.Integer(), nullable=False),
        sa.Column('reservation_datetime', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('notes', sa.Text()),
        sa.Column('special_requests', sa.Text()),
        sa.Column('confirmation_sent', sa.DateTime()),
        sa.Column('reminder_sent', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True)),
        sa.Column('actor_type', sa.String(50)),
        sa.Column('actor_name', sa.String(255)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('data_json', postgresql.JSON()),
        sa.Column('ip_address', sa.String(50)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('ix_calls_tenant_id', 'calls', ['tenant_id'])
    op.create_index('ix_calls_started_at', 'calls', ['started_at'])
    op.create_index('ix_orders_tenant_id', 'orders', ['tenant_id'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_reservations_tenant_id', 'reservations', ['tenant_id'])
    op.create_index('ix_reservations_datetime', 'reservations', ['reservation_datetime'])
    op.create_index('ix_menu_items_tenant_id', 'menu_items', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('reservations')
    op.drop_table('orders')
    op.drop_table('transcripts')
    op.drop_table('calls')
    op.drop_table('menu_modifiers')
    op.drop_table('menu_items')
    op.drop_table('staff_contacts')
    op.drop_table('restaurant_settings')
    op.drop_table('phone_numbers')
    op.drop_table('users')
    op.drop_table('tenants')

