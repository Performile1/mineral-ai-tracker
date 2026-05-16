"""
Mineral AI Tracker - Configuration Settings (PRD v8.0)
Version: 10.5
Description: Centralized configuration with environment variable support
PRD v10.0 Phase 10.5: Added proxy rotation configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List


class Settings(BaseSettings):
    # Database Configuration (Local PostgreSQL with pgvector)
    DATABASE_TYPE: str = "local"  # "local" for Docker PostgreSQL with pgvector
    
    # Local PostgreSQL Configuration (Docker)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "mineral_user"
    POSTGRES_PASSWORD: str = "mineralpass123"  # Updated for ASCII-only encoding
    POSTGRES_DB: str = "mineral_ai_tracker"
    
    # Ollama Configuration (Local SLM Orchestration)
    OLLAMA_URL: str = "http://localhost:11434"  # Ollama API endpoint
    OLLAMA_PHI3_MODEL: str = "phi-3"  # Data Extractor SLM
    OLLAMA_MISTRAL_MODEL: str = "mistral"  # Geology Expert SLM
    OLLAMA_LLAMA3_MODEL: str = "llama3"  # Risk Manager SLM
    
    # Supabase Configuration (DEPRECATED - using local pgvector)
    # SUPABASE_URL: Optional[str] = None
    # SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # API Keys
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # PRD v8.7 Phase 9.5 - Institutional Data Pipeline (Hard-Deterministic Data)
    # Financial Modeling Prep is the canonical source for fundamentals fed
    # to Llama-3's Risk Manager prompt under <HARD_DETERMINISTIC_DATA>.
    FMP_API_KEY: Optional[str] = None
    
    # Proxy Configuration
    PROXY_ROTATION_ENABLED: bool = True
    PROXY_LIST: List[str] = []
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 30
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    REQUESTS_PER_MINUTE: int = 60
    REQUESTS_PER_HOUR: int = 1000
    
    # Scraping Schedule
    FINANCE_SCRAPER_INTERVAL_MINUTES: int = 5
    GOVERNMENT_SCRAPER_HOUR: int = 2  # 2 AM
    SENTIMENT_SCRAPER_INTERVAL_HOURS: int = 6
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Stripe (PRD 5.0)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # PRD v10.0 Phase 10.3: Async Broker Configuration
    USE_CELERY: bool = False  # Set to True to enable async task processing
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # PRD v10.0 Phase 10.5: Proxy Rotation Configuration
    USE_PROXIES: bool = False  # Set to True to enable proxy rotation
    PROXY_LIST: str = ""  # Comma-separated list of proxies (e.g., "http://user:pass@host:port,http://host:port")
    PROXY_MAX_RETRIES: int = 3  # Max retries before falling back to direct connection
    
    # PRD v13.2 Phase 13.2: Multi-Model Selector (Gemini Integration)
    GEMINI_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
