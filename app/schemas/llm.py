"""LLM adapter schemas"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """Message in conversation"""
    role: str  # system, user, assistant
    content: str


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """Tool definition for LLM"""
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolCall(BaseModel):
    """Tool call from LLM"""
    name: str
    arguments: Dict[str, Any]


class LLMGenerateRequest(BaseModel):
    """LLM generation request"""
    system_prompt: str
    messages: List[LLMMessage]
    tools: List[ToolDefinition] = []
    tenant_id: str
    provider: Optional[str] = None  # openai, anthropic, gemini, ollama
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024


class UsageStats(BaseModel):
    """Token usage statistics"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMGenerateResponse(BaseModel):
    """LLM generation response"""
    type: str  # text, tool_call
    content: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    usage: Optional[UsageStats] = None
    confidence: Optional[float] = None
    provider: str
    model: str

