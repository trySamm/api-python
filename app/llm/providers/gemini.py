"""Google Gemini LLM provider"""

from typing import List
import json
import google.generativeai as genai
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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, model: str = "gemini-1.5-pro"):
        super().__init__(model)
        genai.configure(api_key=settings.gemini_api_key)
        self.client = genai.GenerativeModel(model)
    
    def _convert_tools_to_provider_format(
        self,
        tools: List[ToolDefinition],
    ) -> List[genai.protos.Tool]:
        """Convert tools to Gemini function calling format"""
        function_declarations = []
        
        for tool in tools:
            # Convert parameters to Gemini format
            parameters = tool.parameters.copy()
            
            function_declarations.append(
                genai.protos.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=self._convert_schema(parameters),
                )
            )
        
        return [genai.protos.Tool(function_declarations=function_declarations)]
    
    def _convert_schema(self, schema: dict) -> dict:
        """Convert JSON Schema to Gemini schema format"""
        if schema.get("type") == "object":
            properties = {}
            for name, prop in schema.get("properties", {}).items():
                properties[name] = genai.protos.Schema(
                    type=self._map_type(prop.get("type", "string")),
                    description=prop.get("description", ""),
                )
            
            return genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties=properties,
                required=schema.get("required", []),
            )
        
        return genai.protos.Schema(
            type=self._map_type(schema.get("type", "string")),
        )
    
    def _map_type(self, json_type: str) -> int:
        """Map JSON Schema type to Gemini type"""
        type_map = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT,
        }
        return type_map.get(json_type, genai.protos.Type.STRING)
    
    async def generate(
        self,
        system_prompt: str,
        messages: List[LLMMessage],
        tools: List[ToolDefinition],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMGenerateResponse:
        """Generate response using Gemini API"""
        
        # Build conversation history
        history = []
        
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            history.append({
                "role": role,
                "parts": [msg.content],
            })
        
        # Start chat with system instruction
        chat = self.client.start_chat(history=history[:-1] if history else [])
        
        # Build generation config
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        logger.debug(
            "Gemini request",
            model=self.model,
            message_count=len(history),
            tool_count=len(tools) if tools else 0,
        )
        
        # Build request
        last_message = history[-1]["parts"][0] if history else "Hello"
        
        kwargs = {
            "generation_config": generation_config,
        }
        
        if tools:
            kwargs["tools"] = self._convert_tools_to_provider_format(tools)
        
        # Make API call
        response = await chat.send_message_async(
            f"{system_prompt}\n\n{last_message}",
            **kwargs,
        )
        
        # Build response
        result = LLMGenerateResponse(
            type="text",
            provider="gemini",
            model=self.model,
        )
        
        # Check for function calls
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    result.type = "tool_call"
                    result.tool_call = ToolCall(
                        name=part.function_call.name,
                        arguments=dict(part.function_call.args),
                    )
                    break
                elif hasattr(part, "text") and part.text:
                    result.content = part.text
        
        logger.debug(
            "Gemini response",
            response_type=result.type,
            content_length=len(result.content) if result.content else 0,
        )
        
        return result

