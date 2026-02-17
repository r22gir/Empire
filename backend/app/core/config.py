from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/marketf"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    
    # MarketF Configuration
    MARKETF_FEE_PERCENT: float = 8.0
    MARKETF_ESCROW_RELEASE_DELAY_HOURS: int = 48
    
    # Payment Processing
    PAYMENT_PROCESSING_FEE_PERCENT: float = 2.9
    PAYMENT_PROCESSING_FEE_FIXED: float = 0.30
    
    class Config:
        env_file = ".env"


settings = Settings()
