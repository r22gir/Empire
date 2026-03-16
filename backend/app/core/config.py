from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/marketf"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    MARKETF_FEE_PERCENT: float = 8.0
    MARKETF_ESCROW_RELEASE_DELAY_HOURS: int = 48
    PAYMENT_PROCESSING_FEE_PERCENT: float = 2.9
    PAYMENT_PROCESSING_FEE_FIXED: float = 0.30
    
    # API Keys
    anthropic_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # AI Configuration
    ai_primary_provider: str = "anthropic"
    ai_primary_model: str = "claude-sonnet-4-20250514"
    ai_fallback_provider: str = "ollama"
    ai_fallback_model: str = "llama3"
    ollama_base_url: str = "http://localhost:11434"
    
    # Telegram
    telegram_bot_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
