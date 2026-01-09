"""Test configuration and fixtures"""

import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from uuid import uuid4

from app.main import app
from app.database import Base, get_db
from app.models.tenant import Tenant, RestaurantSettings
from app.models.user import User, UserRole
from app.models.menu import MenuItem
from app.api.auth import get_password_hash


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_tenant(test_db):
    """Create a test tenant"""
    tenant = Tenant(
        id=uuid4(),
        name="Test Restaurant",
        timezone="America/New_York",
        llm_provider="openai",
        llm_model="gpt-4-turbo",
    )
    test_db.add(tenant)
    await test_db.flush()
    
    settings = RestaurantSettings(
        tenant_id=tenant.id,
        address="123 Test St",
        hours_json={"monday": {"open": "09:00", "close": "21:00"}},
    )
    test_db.add(settings)
    await test_db.commit()
    
    return tenant


@pytest.fixture
async def test_user(test_db, test_tenant):
    """Create a test user"""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        role=UserRole.RESTAURANT_ADMIN,
        is_active=True,
        is_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    
    return user


@pytest.fixture
async def test_admin_user(test_db):
    """Create a super admin user"""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Admin User",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    
    return user


@pytest.fixture
async def test_menu_items(test_db, test_tenant):
    """Create test menu items"""
    items = [
        MenuItem(
            tenant_id=test_tenant.id,
            name="Margherita Pizza",
            description="Classic tomato and mozzarella",
            price_cents=1499,
            category="Pizza",
        ),
        MenuItem(
            tenant_id=test_tenant.id,
            name="Pepperoni Pizza",
            description="Pepperoni with mozzarella",
            price_cents=1699,
            category="Pizza",
        ),
        MenuItem(
            tenant_id=test_tenant.id,
            name="Caesar Salad",
            description="Romaine with caesar dressing",
            price_cents=1099,
            category="Salads",
        ),
    ]
    
    for item in items:
        test_db.add(item)
    
    await test_db.commit()
    return items


@pytest.fixture
async def client(test_db):
    """Create test client with overridden database"""
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(client, test_user):
    """Create authenticated test client"""
    from app.api.auth import create_access_token
    
    token = create_access_token(test_user)
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client


@pytest.fixture
async def admin_client(client, test_admin_user):
    """Create admin authenticated test client"""
    from app.api.auth import create_access_token
    
    token = create_access_token(test_admin_user)
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client

