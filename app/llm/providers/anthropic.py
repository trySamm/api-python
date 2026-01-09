"""Anthropic Claude LLM provider"""

from typing import List
import json
from anthropic import AsyncAnthropic
import structlog

from app.config import settings
from app.schemas.llm import (
    LLMMessage,
    ToolDefinition,
    LLMGenerateResponse,
    ToolCall,
    UsageStats,
)
from app.llm.providers.base import BaseLLMProvider

logger = structlog.get_logger()


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, model: str = "claude-3-sonnet-20240229"):
        super().__init__(model)
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    def _convert_tools_to_provider_format(
        self,
        tools: List[ToolDefinition],
    ) -> List[dict]:
        """Convert tools to Anthropic tool format"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]
    
    async def generate(
        self,
        system_prompt: str,
        messages: List[LLMMessage],
        tools: List[ToolDefinition],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMGenerateResponse:
        """Generate response using Anthropic API"""
        
        # Build messages array (Anthropic doesn't use system in messages)
        anthropic_messages = []
        
        for msg in messages:
            anthropic_messages.append({
                "role": msg.role if msg.role != "system" else "user",
                "content": msg.content,
            })
        
        # Ensure messages alternate between user and assistant
        # Anthropic requires this
        processed_messages = []
        last_role = None
        
        for msg in anthropic_messages:
            if msg["role"] == last_role:
                # Combine with previous message
                processed_messages[-1]["content"] += "\n" + msg["content"]
            else:
                processed_messages.append(msg)
                last_role = msg["role"]
        
        # Build request kwargs
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": processed_messages if processed_messages else [{"role": "user", "content": "Hello"}],
        }
        
        # Add tools if provided
        if tools:
            kwargs["tools"] = self._convert_tools_to_provider_format(tools)
        
        logger.debug(
            "Anthropic request",
            model=self.model,
            message_count=len(processed_messages),
            tool_count=len(tools) if tools else 0,
        )
        
        # Make API call
        response = await self.client.messages.create(**kwargs)
        
        # Build response
        result = LLMGenerateResponse(
            type="text",
            provider="anthropic",
            model=self.model,
            usage=UsageStats(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            ),
        )
        
        # Check response content
        for block in response.content:
            if block.type == "tool_use":
                result.type = "tool_call"
                result.tool_call = ToolCall(
                    name=block.name,
                    arguments=block.input,
                )
                break
            elif block.type == "text":
                result.content = block.text
        
        logger.debug(
            "Anthropic response",
            response_type=result.type,
            content_length=len(result.content) if result.content else 0,
        )
        
        return result

