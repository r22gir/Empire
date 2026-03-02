"""
Configuration settings for ContractorForge API
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/contractorforge"
    
    # API Keys
    OPENAI_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    SENDGRID_API_KEY: str = ""
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Feature Flags
    ENABLE_PHOTO_MEASUREMENT: bool = True
    ENABLE_POLYCAM_3D: bool = False
    ENABLE_MULTI_TENANCY: bool = True
    ENABLE_SAAS_BILLING: bool = True
    ENABLE_CLIENT_PORTAL: bool = True
    ENABLE_PRODUCTION_QUEUE: bool = True
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "ContractorForge API"
    VERSION: str = "1.0.0"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://contractorforge.com",
        "https://app.contractorforge.com",
    ]


settings = Settings()
