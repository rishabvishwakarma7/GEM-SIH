"""
Central application configuration.
Reads from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://gem_user:gem_password@localhost:5432/gem_compliance"

    # Security
    SECRET_KEY: str = "insecure-dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # AI service (modular LLM backend for requirement extraction)
    GEMINI_API_KEY: str = ""
    AI_MODEL: str = "gemini-pro-latest"
    MAX_AI_INPUT_CHARS: int = 60000

    # --- Notifications (Day 6) ---
    # Email alerts for non-compliance / missing-document findings. Off by
    # default: NOTIFICATIONS_ENABLED=false means the notification_service
    # still records what WOULD have been sent (status="skipped") without
    # requiring SMTP credentials to be configured for the app to run.
    NOTIFICATIONS_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@gem-compliance.local"
    SMTP_USE_TLS: bool = True
    # SMS is a stub pending a paid gateway (Twilio / MSG91 / etc.) - see
    # notification_service.SMSNotificationProvider.
    SMS_ENABLED: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
