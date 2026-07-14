from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import warnings
import os

env_state = os.getenv("ENVIRONMENT", "local")
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
env_file_path = os.path.join(base_dir, f".env.{env_state}")
if not os.path.exists(env_file_path):
    env_file_path = os.path.join(base_dir, ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "SPIP API"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    APP_SECRET_KEY: str
    ENCRYPTION_KEY: str
    
    # Postgres
    DATABASE_URL: str
    
    # Redis & Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # AI 
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_FLASH: str = "gemini-1.5-flash"
    GEMINI_MODEL_PRO: str = "gemini-1.5-pro"
    SERPAPI_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    GOOGLE_CSE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None
    
    # Email
    BREVO_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@spip.local"
    EMAIL_FROM_NAME: str = "SPIP"
    
    # Job Providers
    ARBEITNOW_ENABLED: bool = True
    REMOTEOK_ENABLED: bool = True

    # We map the legacy properties to the new ones to avoid breaking existing imports that use `settings.SECRET_KEY` etc.
    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET

    @property
    def ALGORITHM(self) -> str:
        return self.JWT_ALGORITHM

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        return self.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

settings = Settings()

if settings.JWT_SECRET in ["CHANGE_ME_TO_A_RANDOM_64_CHARACTER_SECRET", ""] or len(settings.JWT_SECRET) < 32:
    warnings.warn("SECURITY WARNING: JWT_SECRET is weak or using default placeholder. This is unsafe for production.")
