from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class Settings(BaseSettings):
    """
    Centralized application configuration loaded from environment variables or .env file.
    Provides strict typing and validation.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = Field(default="development", description="App environment (development, staging, production, test)")
    HOST: str = Field(default="0.0.0.0", description="Bind host")
    PORT: int = Field(default=8000, description="Bind port")
    PROJECT_NAME: str = Field(default="Opti Matrix ERP", description="Project display name")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 route prefix")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Structured logging level")
    LOG_JSON_FORMAT: bool = Field(default=True, description="Output logs as JSON")

    # MongoDB Configuration
    MONGODB_URI: str = Field(default="mongodb://127.0.0.1:27017", description="MongoDB connection URI")
    MONGODB_DB_NAME: str = Field(default="RG_erp", description="MongoDB database name")
    MONGODB_MIN_POOL_SIZE: int = Field(default=10, description="Minimum connection pool size")
    MONGODB_MAX_POOL_SIZE: int = Field(default=50, description="Maximum connection pool size")
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = Field(default=5000, description="Server selection timeout in ms")
    MONGODB_CONNECT_TIMEOUT_MS: int = Field(default=5000, description="Socket connect timeout in ms")

    # Security, Sessions & CSRF
    SESSION_COOKIE_NAME: str = Field(default="RG_session", description="Session cookie name")
    SESSION_MAX_AGE_SECONDS: int = Field(default=28800, description="Max session lifespan (8 hours)")
    SESSION_IDLE_TIMEOUT_SECONDS: int = Field(default=3600, description="Session idle timeout (1 hour)")
    CSRF_COOKIE_NAME: str = Field(default="RG_csrf", description="CSRF token cookie name")
    CSRF_HEADER_NAME: str = Field(default="X-CSRF-Token", description="CSRF header name")
    RATE_LIMIT_LOGIN: str = Field(default="10/minute", description="Rate limit rule for login endpoint")

    # Security & CORS
    ALLOWED_CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Origins permitted to make cross-origin requests"
    )

    @field_validator("ALLOWED_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS origins value: {v}")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.lower() == "test"


settings = Settings()
