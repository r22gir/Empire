"""
Configuration settings for MarketForge backend.
Loads environment variables and provides centralized config.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/marketforge"
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # eBay API
    ebay_app_id: Optional[str] = None
    ebay_cert_id: Optional[str] = None
    ebay_dev_id: Optional[str] = None
    
    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # Cloudflare Email
    cloudflare_api_key: Optional[str] = None
    cloudflare_zone_id: Optional[str] = None
    
    # AI Services
    grok_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    
    # Economic Intelligence
    economic_enabled: bool = True
    economic_default_balance: float = 1000.00
    economic_token_input_price_per_1m: float = 2.50  # GPT-4 pricing per 1M tokens
    economic_token_output_price_per_1m: float = 10.00  # GPT-4 pricing per 1M tokens
    economic_compute_cost_per_minute: float = 0.10
    economic_listing_commission_rate: float = 0.05  # 5% commission on listings
    
    # Quality Evaluation
    quality_eval_enabled: bool = True
    quality_eval_model: str = "gpt-4-turbo-preview"
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
