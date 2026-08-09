import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Database (SQLite for local dev; set postgresql:// for production)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./musician.db")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")

    # ElevenLabs
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "")

    # Fal AI
    FAL_KEY: str = os.getenv("FAL_KEY", "")

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "musician-secret-key-2024-CHANGE-IN-PROD")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 gün

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # File Storage (local fallback)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50000000"))

    # S3 / Cloudflare R2 (optional — leave blank to use local storage)
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")   # e.g. https://<id>.r2.cloudflarestorage.com
    S3_PUBLIC_BASE_URL: str = os.getenv("S3_PUBLIC_BASE_URL", "")  # e.g. https://pub-xxx.r2.dev
    S3_REGION: str = os.getenv("S3_REGION", "auto")

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Email (Resend)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "zeynep.ece933@gmail.com")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "onboarding@resend.dev")

    class Config:
        env_file = ".env"


settings = Settings()
