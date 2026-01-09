"""
Application configuration using Pydantic Settings
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = "postgresql+asyncpg://loman:loman_secret@localhost:5432/loman_ai"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT / Auth
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # Deepgram
    deepgram_api_key: str = ""
    
    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    
    # LLM Providers
    openai_api_key: str = ""
    openai_default_model: str = "gpt-4-turbo"
    
    anthropic_api_key: str = ""
    anthropic_default_model: str = "claude-3-sonnet-20240229"
    
    gemini_api_key: str = ""
    gemini_default_model: str = "gemini-1.5-pro"
    
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama2"
    
    # Default LLM Configuration
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4-turbo"
    fallback_llm_provider: str = "anthropic"
    fallback_llm_model: str = "claude-3-sonnet-20240229"
    
    # Call Gateway
    call_gateway_url: str = "http://localhost:8080"
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    cors_origins: str = "http://localhost:3000"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Recordings
    recordings_storage: str = "local"
    recordings_path: str = "/app/recordings"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

