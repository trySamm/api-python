"""OpenAI LLM provider"""

from typing import List
import json
from openai import AsyncOpenAI
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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation"""
    
    def __init__(self, model: str = "gpt-4-turbo"):
        super().__init__(model)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    def _convert_tools_to_provider_format(
        self,
        tools: List[ToolDefinition],
    ) -> List[dict]:
        """Convert tools to OpenAI function calling format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
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
        """Generate response using OpenAI API"""
        
        # Build messages array
        openai_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        # Build request kwargs
        kwargs = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Add tools if provided
        if tools:
            kwargs["tools"] = self._convert_tools_to_provider_format(tools)
            kwargs["tool_choice"] = "auto"
        
        logger.debug(
            "OpenAI request",
            model=self.model,
            message_count=len(openai_messages),
            tool_count=len(tools) if tools else 0,
        )
        
        # Make API call
        response = await self.client.chat.completions.create(**kwargs)
        
        # Extract response
        choice = response.choices[0]
        message = choice.message
        
        # Build response
        result = LLMGenerateResponse(
            type="text",
            provider="openai",
            model=self.model,
            usage=UsageStats(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ) if response.usage else None,
        )
        
        # Check for tool calls
        if message.tool_calls and len(message.tool_calls) > 0:
            tool_call = message.tool_calls[0]
            result.type = "tool_call"
            result.tool_call = ToolCall(
                name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
        else:
            result.content = message.content
        
        logger.debug(
            "OpenAI response",
            response_type=result.type,
            content_length=len(result.content) if result.content else 0,
        )
        
        return result

