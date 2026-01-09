"""
Loman AI - FastAPI Backend Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.database import engine, Base
from app.api import auth, tenants, calls, menu, orders, reservations, llm_config
from app.webhooks import twilio
from app.llm import router as llm_router
from app.tools import router as tools_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Loman AI API", version="1.0.0")
    yield
    logger.info("Shutting down Loman AI API")


# Create FastAPI application
app = FastAPI(
    title="Loman AI",
    description="AI-powered phone answering system for restaurants",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health")
async def health():
    """Basic health check"""
    return {"status": "healthy", "service": "api", "version": "1.0.0"}


@app.get("/health/ready")
async def ready():
    """Readiness check with dependency verification"""
    from app.database import SessionLocal
    
    checks = {}
    
    # Check database
    try:
        async with SessionLocal() as db:
            await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"failed: {str(e)}"
    
    # Check Redis
    try:
        from app.jobs.celery_app import celery_app
        celery_app.control.ping(timeout=1)
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"failed: {str(e)}"
    
    all_ok = all(v == "ok" for v in checks.values())
    
    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
    }


# Include API routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
app.include_router(calls.router, prefix="/tenants/{tenant_id}/calls", tags=["Calls"])
app.include_router(menu.router, prefix="/tenants/{tenant_id}/menu_items", tags=["Menu"])
app.include_router(orders.router, prefix="/tenants/{tenant_id}/orders", tags=["Orders"])
app.include_router(reservations.router, prefix="/tenants/{tenant_id}/reservations", tags=["Reservations"])
app.include_router(llm_config.router, prefix="/tenants/{tenant_id}/llm_config", tags=["LLM Config"])

# Include webhook routers
app.include_router(twilio.router, prefix="/webhooks/twilio", tags=["Webhooks"])

# Include LLM adapter router
app.include_router(llm_router.router, prefix="/llm", tags=["LLM"])

# Include tools router
app.include_router(tools_router.router, prefix="/tools", tags=["Tools"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )

