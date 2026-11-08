"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://quran:quran@localhost:5432/quran"

    # Auth
    SECRET_KEY: str = "dev-secret-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Speech recognition (Whisper)
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"          # cpu | cuda
    WHISPER_COMPUTE_TYPE: str = "int8"   # int8 | float16 | float32

    # Tajweed correction model
    TAJWEED_MODEL_ID: str = "quran-tajweed-correction"
    TAJWEED_MODEL_PATH: str = "./models/tajweed"
    TAJWEED_CONFIDENCE_THRESHOLD: float = 0.70

    # App
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
