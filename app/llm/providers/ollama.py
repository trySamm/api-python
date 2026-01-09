"""Ollama local LLM provider"""

from typing import List
import json
import httpx
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


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider implementation"""
    
    def __init__(self, model: str = "llama2"):
        super().__init__(model)
        self.base_url = settings.ollama_base_url
    
    async def generate(
        self,
        system_prompt: str,
        messages: List[LLMMessage],
        tools: List[ToolDefinition],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMGenerateResponse:
        """Generate response using Ollama API"""
        
        # Build messages array
        ollama_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        for msg in messages:
            ollama_messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        # Build request payload
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        # Add tools if provided (Ollama supports function calling for some models)
        if tools:
            payload["tools"] = self._convert_tools_to_provider_format(tools)
        
        logger.debug(
            "Ollama request",
            model=self.model,
            base_url=self.base_url,
            message_count=len(ollama_messages),
            tool_count=len(tools) if tools else 0,
        )
        
        # Make API call
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        
        # Build response
        result = LLMGenerateResponse(
            type="text",
            provider="ollama",
            model=self.model,
        )
        
        message = data.get("message", {})
        
        # Check for tool calls
        tool_calls = message.get("tool_calls", [])
        if tool_calls and len(tool_calls) > 0:
            tool_call = tool_calls[0]
            result.type = "tool_call"
            result.tool_call = ToolCall(
                name=tool_call.get("function", {}).get("name", ""),
                arguments=json.loads(
                    tool_call.get("function", {}).get("arguments", "{}")
                ),
            )
        else:
            result.content = message.get("content", "")
        
        # Add usage stats if available
        if "eval_count" in data:
            result.usage = UsageStats(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            )
        
        logger.debug(
            "Ollama response",
            response_type=result.type,
            content_length=len(result.content) if result.content else 0,
        )
        
        return result
    
    def _convert_tools_to_provider_format(
        self,
        tools: List[ToolDefinition],
    ) -> List[dict]:
        """Convert tools to Ollama function calling format"""
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

