#!/usr/bin/env python3
"""
Seed script to create demo restaurant and menu data
"""

import asyncio
import uuid
from datetime import datetime

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_demo_data():
    """Seed demo data for development"""
    from app.database import SessionLocal, engine, Base
    from app.models.tenant import Tenant, PhoneNumber, RestaurantSettings, StaffContact
    from app.models.menu import MenuItem, MenuModifier
    from app.models.user import User, UserRole
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        # Check if demo tenant already exists
        from sqlalchemy import select
        result = await db.execute(
            select(Tenant).where(Tenant.name == "Mario's Italian Kitchen")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("Demo data already exists. Skipping...")
            return
        
        print("Creating demo tenant...")
        
        # Create demo tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Mario's Italian Kitchen",
            timezone="America/New_York",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            fallback_llm_provider="anthropic",
            fallback_llm_model="claude-3-sonnet-20240229",
        )
        db.add(tenant)
        await db.flush()
        
        print(f"Created tenant: {tenant.name} (ID: {tenant.id})")
        
        # Create phone number
        phone = PhoneNumber(
            tenant_id=tenant.id,
            e164="+15551234567",  # Replace with actual Twilio number
            provider="twilio",
        )
        db.add(phone)
        
        # Create settings
        settings = RestaurantSettings(
            tenant_id=tenant.id,
            address="123 Main Street",
            city="New York",
            state="NY",
            zip_code="10001",
            hours_json={
                "monday": {"open": "11:00", "close": "22:00"},
                "tuesday": {"open": "11:00", "close": "22:00"},
                "wednesday": {"open": "11:00", "close": "22:00"},
                "thursday": {"open": "11:00", "close": "22:00"},
                "friday": {"open": "11:00", "close": "23:00"},
                "saturday": {"open": "12:00", "close": "23:00"},
                "sunday": {"open": "12:00", "close": "21:00"},
            },
            policies_json={
                "cancellation": "Please cancel reservations at least 2 hours in advance.",
                "parking": "Free parking available in the back lot.",
                "dietary": "We offer gluten-free and vegetarian options. Please ask your server.",
            },
            recording_enabled=True,
            escalation_number="+15559876543",
            max_party_size="12",
            reservation_slot_minutes="30",
        )
        db.add(settings)
        
        # Create staff contact
        staff = StaffContact(
            tenant_id=tenant.id,
            name="Mario",
            phone="+15559876543",
            email="mario@marios-kitchen.com",
            role="manager",
            notify_on_order=True,
            notify_on_reservation=True,
            notify_on_escalation=True,
        )
        db.add(staff)
        
        # Create super admin user
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@loman.ai",
            hashed_password=pwd_context.hash("admin123"),
            full_name="System Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin_user)
        
        # Create restaurant admin user
        restaurant_admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="mario@marios-kitchen.com",
            hashed_password=pwd_context.hash("mario123"),
            full_name="Mario Rossi",
            role=UserRole.RESTAURANT_ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(restaurant_admin)
        
        print("Creating menu items...")
        
        # Create menu items
        menu_items = [
            # Appetizers
            {"name": "Bruschetta", "description": "Grilled bread topped with fresh tomatoes, garlic, basil, and olive oil", "price_cents": 899, "category": "Appetizers"},
            {"name": "Calamari Fritti", "description": "Crispy fried calamari with marinara sauce", "price_cents": 1299, "category": "Appetizers"},
            {"name": "Mozzarella Sticks", "description": "Golden fried mozzarella with marinara", "price_cents": 999, "category": "Appetizers"},
            {"name": "Garlic Bread", "description": "Toasted bread with garlic butter and herbs", "price_cents": 599, "category": "Appetizers"},
            
            # Pizzas
            {"name": "Margherita Pizza", "description": "Fresh mozzarella, tomato sauce, and basil", "price_cents": 1499, "category": "Pizza"},
            {"name": "Pepperoni Pizza", "description": "Classic pepperoni with mozzarella cheese", "price_cents": 1699, "category": "Pizza"},
            {"name": "Meat Lovers Pizza", "description": "Pepperoni, sausage, bacon, and ham", "price_cents": 1899, "category": "Pizza"},
            {"name": "Vegetable Pizza", "description": "Bell peppers, onions, mushrooms, olives, and tomatoes", "price_cents": 1699, "category": "Pizza"},
            {"name": "Hawaiian Pizza", "description": "Ham and pineapple with mozzarella", "price_cents": 1699, "category": "Pizza"},
            {"name": "BBQ Chicken Pizza", "description": "Grilled chicken, BBQ sauce, red onions, and cilantro", "price_cents": 1799, "category": "Pizza"},
            
            # Pasta
            {"name": "Spaghetti Bolognese", "description": "Spaghetti with rich meat sauce", "price_cents": 1599, "category": "Pasta"},
            {"name": "Fettuccine Alfredo", "description": "Fettuccine in creamy parmesan sauce", "price_cents": 1499, "category": "Pasta"},
            {"name": "Chicken Parmesan", "description": "Breaded chicken breast with marinara and melted mozzarella over spaghetti", "price_cents": 1899, "category": "Pasta"},
            {"name": "Lasagna", "description": "Layers of pasta, meat sauce, ricotta, and mozzarella", "price_cents": 1699, "category": "Pasta"},
            {"name": "Penne Vodka", "description": "Penne in creamy tomato vodka sauce", "price_cents": 1599, "category": "Pasta"},
            {"name": "Shrimp Scampi", "description": "Sautéed shrimp in garlic butter white wine sauce over linguine", "price_cents": 2199, "category": "Pasta"},
            
            # Salads
            {"name": "Caesar Salad", "description": "Romaine, parmesan, croutons, caesar dressing", "price_cents": 1099, "category": "Salads"},
            {"name": "House Salad", "description": "Mixed greens, tomatoes, cucumbers, red onion", "price_cents": 899, "category": "Salads"},
            {"name": "Caprese Salad", "description": "Fresh mozzarella, tomatoes, basil, balsamic glaze", "price_cents": 1199, "category": "Salads"},
            
            # Desserts
            {"name": "Tiramisu", "description": "Classic Italian coffee-flavored dessert", "price_cents": 899, "category": "Desserts"},
            {"name": "Cannoli", "description": "Crispy shells filled with sweet ricotta cream", "price_cents": 699, "category": "Desserts"},
            {"name": "Gelato", "description": "Choice of vanilla, chocolate, or strawberry", "price_cents": 599, "category": "Desserts"},
            
            # Drinks
            {"name": "Soft Drink", "description": "Coca-Cola, Diet Coke, Sprite, or Fanta", "price_cents": 299, "category": "Drinks"},
            {"name": "Italian Soda", "description": "Sparkling water with your choice of flavor", "price_cents": 399, "category": "Drinks"},
            {"name": "Coffee", "description": "Regular or decaf", "price_cents": 299, "category": "Drinks"},
            {"name": "Espresso", "description": "Single or double shot", "price_cents": 349, "category": "Drinks"},
        ]
        
        for item_data in menu_items:
            item = MenuItem(
                tenant_id=tenant.id,
                name=item_data["name"],
                description=item_data["description"],
                price_cents=item_data["price_cents"],
                category=item_data["category"],
                is_active=True,
                is_available=True,
            )
            db.add(item)
            await db.flush()
            
            # Add modifiers for pizzas
            if item_data["category"] == "Pizza":
                size_modifier = MenuModifier(
                    tenant_id=tenant.id,
                    menu_item_id=item.id,
                    name="Size",
                    options_json=[
                        {"name": "Small (10\")", "price_cents": 0},
                        {"name": "Medium (14\")", "price_cents": 300},
                        {"name": "Large (18\")", "price_cents": 600},
                    ],
                    is_required=True,
                    max_selections=1,
                )
                db.add(size_modifier)
                
                crust_modifier = MenuModifier(
                    tenant_id=tenant.id,
                    menu_item_id=item.id,
                    name="Crust",
                    options_json=[
                        {"name": "Regular", "price_cents": 0},
                        {"name": "Thin", "price_cents": 0},
                        {"name": "Deep Dish", "price_cents": 200},
                        {"name": "Gluten-Free", "price_cents": 300},
                    ],
                    is_required=False,
                    max_selections=1,
                )
                db.add(crust_modifier)
        
        await db.commit()
        
        print(f"""
Demo data created successfully!

Tenant: Mario's Italian Kitchen
  ID: {tenant.id}
  Phone: +15551234567

Users:
  Super Admin:
    Email: admin@loman.ai
    Password: admin123
  
  Restaurant Admin:
    Email: mario@marios-kitchen.com
    Password: mario123

Menu: {len(menu_items)} items created

To use this tenant, update the phone number in the database
to match your actual Twilio number.
""")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())

