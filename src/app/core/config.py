from typing import Any, Optional
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Environment
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Application
    APP_NAME: str = Field(default="Amazon Insights Platform")
    APP_VERSION: str = Field(default="0.1.0")
    SECRET_KEY: str = Field(...)
    API_V1_STR: str = Field(default="/api/v1")

    # Database
    DATABASE_URL: PostgresDsn = Field(...)
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=40)

    # Redis
    REDIS_URL: RedisDsn = Field(...)
    REDIS_MAX_CONNECTIONS: int = Field(default=50)

    # Celery
    CELERY_BROKER_URL: RedisDsn = Field(...)
    CELERY_RESULT_BACKEND: RedisDsn = Field(...)

    # External APIs
    FIRECRAWL_API_KEY: Optional[str] = Field(default=None)
    FIRECRAWL_API_URL: str = Field(default="https://api.firecrawl.dev")
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview")

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    ALGORITHM: str = Field(default="HS256")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000)

    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None)
    PROMETHEUS_ENABLED: bool = Field(default=True)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [i.strip() for i in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()