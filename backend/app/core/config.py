from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    firebase_project_id: str = ""
    firebase_service_account_json: str = ""
    indicator_hmac_secret: str = ""
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    safe_browsing_api_key: str = ""
    virustotal_api_key: str = ""
    virustotal_max_urls_per_analysis: int = 2
    virustotal_cache_ttl_seconds: int = 21_600
    default_phone_region: str = "AR"
    allowed_origins: str = (
        "http://localhost:60891,http://127.0.0.1:60891,"
        "http://localhost:5000,http://127.0.0.1:5000"
    )
    max_analysis_chars: int = 10_000
    max_report_chars: int = 4_000

    @field_validator("default_phone_region")
    @classmethod
    def normalize_phone_region(cls, value: str) -> str:
        return value.strip().upper()

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def firebase_ready(self) -> bool:
        return bool(self.firebase_project_id and self.indicator_hmac_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
