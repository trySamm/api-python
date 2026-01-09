"""Tests for tool execution endpoints"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_context(authenticated_client: AsyncClient, test_tenant):
    """Test getting restaurant context"""
    response = await authenticated_client.post(
        "/tools/get_context",
        json={"tenant_id": str(test_tenant.id)},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["restaurant_name"] == "Test Restaurant"
    assert data["address"] == "123 Test St"


@pytest.mark.asyncio
async def test_search_menu(authenticated_client: AsyncClient, test_tenant, test_menu_items):
    """Test searching menu items"""
    response = await authenticated_client.post(
        "/tools/search_menu",
        json={
            "tenant_id": str(test_tenant.id),
            "query": "pizza",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert all("Pizza" in item["name"] for item in data["items"])


@pytest.mark.asyncio
async def test_search_menu_no_results(authenticated_client: AsyncClient, test_tenant, test_menu_items):
    """Test searching menu with no results"""
    response = await authenticated_client.post(
        "/tools/search_menu",
        json={
            "tenant_id": str(test_tenant.id),
            "query": "sushi",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0


@pytest.mark.asyncio
async def test_create_order(authenticated_client: AsyncClient, test_tenant):
    """Test creating an order"""
    response = await authenticated_client.post(
        "/tools/create_order",
        json={
            "tenant_id": str(test_tenant.id),
            "customer_name": "John Doe",
            "customer_phone": "+15551234567",
            "items": [
                {"name": "Margherita Pizza", "quantity": 1, "price_cents": 1499},
                {"name": "Caesar Salad", "quantity": 2, "price_cents": 1099},
            ],
            "pickup_time": "2024-01-15T18:00:00",
            "notes": "Extra napkins please",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "order_id" in data
    assert data["total_cents"] > 0


@pytest.mark.asyncio
async def test_create_reservation(authenticated_client: AsyncClient, test_tenant):
    """Test creating a reservation"""
    response = await authenticated_client.post(
        "/tools/create_reservation",
        json={
            "tenant_id": str(test_tenant.id),
            "customer_name": "Jane Smith",
            "customer_phone": "+15559876543",
            "party_size": 4,
            "date_time": "2024-01-20T19:00:00",
            "notes": "Birthday dinner",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "reservation_id" in data
    assert "confirmed_time" in data


@pytest.mark.asyncio
async def test_get_availability(authenticated_client: AsyncClient, test_tenant):
    """Test checking availability"""
    response = await authenticated_client.post(
        "/tools/get_availability",
        json={
            "tenant_id": str(test_tenant.id),
            "date": "2024-01-20",
            "time": "19:00",
            "party_size": 4,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "available_times" in data

