"""Unified LLM adapter interface"""

from typing import List, Optional
import structlog

from app.schemas.llm import (
    LLMMessage,
    ToolDefinition,
    LLMGenerateResponse,
    ToolCall,
    UsageStats,
)
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.ollama import OllamaProvider

logger = structlog.get_logger()


class LLMAdapter:
    """
    Unified LLM adapter that routes to any provider.
    Implements fallback logic when primary provider fails.
    """
    
    def __init__(
        self,
        provider: str,
        model: str,
        fallback_provider: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model
        self.fallback_provider = fallback_provider
        self.fallback_model = fallback_model
    
    def _get_provider_instance(self, provider: str, model: str):
        """Get the appropriate provider instance"""
        providers = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "gemini": GeminiProvider,
            "ollama": OllamaProvider,
        }
        
        provider_class = providers.get(provider)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider}")
        
        return provider_class(model=model)
    
    async def generate(
        self,
        system_prompt: str,
        messages: List[LLMMessage],
        tools: List[ToolDefinition],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMGenerateResponse:
        """
        Generate a response from the LLM.
        Attempts fallback if primary provider fails.
        """
        try:
            provider_instance = self._get_provider_instance(self.provider, self.model)
            response = await provider_instance.generate(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response
            
        except Exception as e:
            logger.warning(
                "Primary LLM provider failed, attempting fallback",
                provider=self.provider,
                model=self.model,
                error=str(e),
            )
            
            # Try fallback if configured
            if self.fallback_provider and self.fallback_model:
                try:
                    fallback_instance = self._get_provider_instance(
                        self.fallback_provider,
                        self.fallback_model,
                    )
                    response = await fallback_instance.generate(
                        system_prompt=system_prompt,
                        messages=messages,
                        tools=tools,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    return response
                    
                except Exception as fallback_error:
                    logger.error(
                        "Fallback LLM provider also failed",
                        fallback_provider=self.fallback_provider,
                        fallback_model=self.fallback_model,
                        error=str(fallback_error),
                    )
                    raise fallback_error
            else:
                raise e


def get_llm_adapter(
    provider: str,
    model: str,
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
) -> LLMAdapter:
    """Factory function to create LLM adapter"""
    return LLMAdapter(
        provider=provider,
        model=model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
    )

