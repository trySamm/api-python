"""Tests for tenant scoping and isolation"""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.tenant import Tenant
from app.models.menu import MenuItem


@pytest.mark.asyncio
async def test_tenant_isolation_menu(test_db, test_tenant, test_menu_items, authenticated_client: AsyncClient):
    """Test that menu items are isolated by tenant"""
    # Create another tenant with menu items
    other_tenant = Tenant(
        id=uuid4(),
        name="Other Restaurant",
        timezone="America/Los_Angeles",
    )
    test_db.add(other_tenant)
    await test_db.flush()
    
    other_item = MenuItem(
        tenant_id=other_tenant.id,
        name="Sushi Roll",
        description="Fresh salmon sushi",
        price_cents=1899,
        category="Sushi",
    )
    test_db.add(other_item)
    await test_db.commit()
    
    # Search should only return items from test_tenant
    response = await authenticated_client.post(
        "/tools/search_menu",
        json={
            "tenant_id": str(test_tenant.id),
            "query": "sushi",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    # Should not find sushi from other tenant
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_tenant_context_isolation(test_db, test_tenant, authenticated_client: AsyncClient):
    """Test that restaurant context is tenant-scoped"""
    # Create another tenant
    other_tenant = Tenant(
        id=uuid4(),
        name="Different Restaurant",
        timezone="Europe/London",
    )
    test_db.add(other_tenant)
    await test_db.commit()
    
    # Get context for test_tenant
    response = await authenticated_client.post(
        "/tools/get_context",
        json={"tenant_id": str(test_tenant.id)},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["restaurant_name"] == "Test Restaurant"
    
    # Get context for other_tenant (should work but return different data)
    response = await authenticated_client.post(
        "/tools/get_context",
        json={"tenant_id": str(other_tenant.id)},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["restaurant_name"] == "Different Restaurant"


@pytest.mark.asyncio
async def test_unauthorized_tenant_access(authenticated_client: AsyncClient, test_user):
    """Test that users can't access other tenants' data via API"""
    # Try to access a random tenant ID
    fake_tenant_id = str(uuid4())
    
    response = await authenticated_client.get(
        f"/tenants/{fake_tenant_id}/calls",
    )
    
    # Should be forbidden (user's tenant doesn't match)
    assert response.status_code in [403, 404]


@pytest.mark.asyncio
async def test_super_admin_can_access_all_tenants(admin_client: AsyncClient, test_tenant):
    """Test that super admin can access any tenant"""
    response = await admin_client.get(
        f"/tenants/{test_tenant.id}",
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Restaurant"

