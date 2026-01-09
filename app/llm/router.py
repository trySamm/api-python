"""LLM adapter API router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

from app.database import get_db
from app.models.tenant import Tenant
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse
from app.llm.adapter import LLMAdapter

router = APIRouter()
logger = structlog.get_logger()


@router.post("/generate", response_model=LLMGenerateResponse)
async def generate(
    request: LLMGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a response from the LLM.
    This is the unified LLM interface that routes to any provider.
    """
    logger.info(
        "LLM generate request",
        tenant_id=request.tenant_id,
        provider=request.provider,
        model=request.model,
        message_count=len(request.messages),
        tool_count=len(request.tools),
    )
    
    # Get tenant configuration
    result = await db.execute(
        select(Tenant).where(Tenant.id == UUID(request.tenant_id))
    )
    tenant = result.scalar_one_or_none()
    
    # Determine provider and model
    provider = request.provider
    model = request.model
    fallback_provider = None
    fallback_model = None
    
    if tenant:
        provider = provider or tenant.llm_provider
        model = model or tenant.llm_model
        fallback_provider = tenant.fallback_llm_provider
        fallback_model = tenant.fallback_llm_model
    else:
        provider = provider or "openai"
        model = model or "gpt-4-turbo"
    
    # Create adapter and generate
    adapter = LLMAdapter(
        provider=provider,
        model=model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
    )
    
    try:
        response = await adapter.generate(
            system_prompt=request.system_prompt,
            messages=request.messages,
            tools=request.tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        logger.info(
            "LLM generate response",
            tenant_id=request.tenant_id,
            response_type=response.type,
            provider=response.provider,
            model=response.model,
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "LLM generate error",
            tenant_id=request.tenant_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))

