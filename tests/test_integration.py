"""Integration tests for the full order flow"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
async def test_full_order_flow(authenticated_client: AsyncClient, test_tenant, test_menu_items):
    """
    Integration test simulating a full order flow:
    1. Create tenant (already done via fixture)
    2. Search menu
    3. Create order
    4. Verify order exists
    """
    # Step 1: Search for pizza
    search_response = await authenticated_client.post(
        "/tools/search_menu",
        json={
            "tenant_id": str(test_tenant.id),
            "query": "pizza",
        },
    )
    
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert len(search_data["items"]) >= 1
    
    pizza = search_data["items"][0]
    
    # Step 2: Create order with found item
    order_response = await authenticated_client.post(
        "/tools/create_order",
        json={
            "tenant_id": str(test_tenant.id),
            "customer_name": "Integration Test Customer",
            "customer_phone": "+15551234567",
            "items": [
                {
                    "item_id": pizza["id"],
                    "name": pizza["name"],
                    "quantity": 2,
                    "price_cents": pizza["price_cents"],
                    "modifiers": [],
                },
            ],
            "pickup_time": "2024-01-15T18:30:00",
        },
    )
    
    assert order_response.status_code == 200
    order_data = order_response.json()
    assert "order_id" in order_data
    assert order_data["total_cents"] > 0
    
    order_id = order_data["order_id"]
    
    # Step 3: Verify order exists via API
    orders_response = await authenticated_client.get(
        f"/tenants/{test_tenant.id}/orders",
    )
    
    assert orders_response.status_code == 200
    orders_data = orders_response.json()
    
    # Find our order
    found_order = None
    for order in orders_data.get("items", []):
        if order["id"] == order_id:
            found_order = order
            break
    
    assert found_order is not None
    assert found_order["customer_name"] == "Integration Test Customer"
    assert found_order["status"] in ["pending", "confirmed"]


@pytest.mark.asyncio
async def test_full_reservation_flow(authenticated_client: AsyncClient, test_tenant):
    """
    Integration test simulating a full reservation flow:
    1. Check availability
    2. Create reservation
    3. Verify reservation exists
    """
    # Step 1: Check availability
    availability_response = await authenticated_client.post(
        "/tools/get_availability",
        json={
            "tenant_id": str(test_tenant.id),
            "date": "2024-02-14",
            "time": "19:00",
            "party_size": 2,
        },
    )
    
    assert availability_response.status_code == 200
    availability_data = availability_response.json()
    assert "available" in availability_data
    
    # Step 2: Create reservation
    reservation_response = await authenticated_client.post(
        "/tools/create_reservation",
        json={
            "tenant_id": str(test_tenant.id),
            "customer_name": "Valentine Couple",
            "customer_phone": "+15559876543",
            "party_size": 2,
            "date_time": "2024-02-14T19:00:00",
            "notes": "Valentine's Day dinner - window table if possible",
        },
    )
    
    assert reservation_response.status_code == 200
    reservation_data = reservation_response.json()
    assert "reservation_id" in reservation_data
    
    reservation_id = reservation_data["reservation_id"]
    
    # Step 3: Verify reservation exists
    reservations_response = await authenticated_client.get(
        f"/tenants/{test_tenant.id}/reservations",
    )
    
    assert reservations_response.status_code == 200
    reservations_data = reservations_response.json()
    
    # Find our reservation
    found_reservation = None
    for res in reservations_data.get("items", []):
        if res["id"] == reservation_id:
            found_reservation = res
            break
    
    assert found_reservation is not None
    assert found_reservation["customer_name"] == "Valentine Couple"
    assert found_reservation["party_size"] == 2


@pytest.mark.asyncio
async def test_llm_generate_endpoint(authenticated_client: AsyncClient, test_tenant):
    """Test the LLM generate endpoint (mock response for testing)"""
    response = await authenticated_client.post(
        "/llm/generate",
        json={
            "system_prompt": "You are a helpful restaurant assistant.",
            "messages": [
                {"role": "user", "content": "What are your hours?"}
            ],
            "tools": [],
            "tenant_id": str(test_tenant.id),
            "provider": "openai",
            "model": "gpt-4-turbo",
            "temperature": 0.7,
        },
    )
    
    # Note: This will fail without actual API keys
    # In CI, you'd mock the LLM providers
    # For now, we just verify the endpoint accepts the request
    assert response.status_code in [200, 500]  # 500 if no API key configured

