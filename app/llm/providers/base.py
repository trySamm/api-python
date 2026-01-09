"""Base LLM provider interface"""

from abc import ABC, abstractmethod
from typing import List

from app.schemas.llm import LLMMessage, ToolDefinition, LLMGenerateResponse


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, model: str):
        self.model = model
    
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        messages: List[LLMMessage],
        tools: List[ToolDefinition],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMGenerateResponse:
        """Generate a response from the LLM"""
        pass
    
    def _convert_tools_to_provider_format(
        self,
        tools: List[ToolDefinition],
    ) -> List[dict]:
        """Convert tools to provider-specific format (override in subclass)"""
        return [tool.model_dump() for tool in tools]

