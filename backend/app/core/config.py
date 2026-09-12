"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import ClassVar, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Landslide Early Warning and Monitoring Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./landslide_dev.db"

    # Security
    JWT_SECRET: str = "change-me-to-a-long-random-secret-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # External providers
    IMD_API_KEY: str = ""
    IMD_BASE_URL: str = "https://api.imd.gov.in"
    IMD_API_TOKEN: str = ""
    IMD_TOKEN_URL: str = ""
    IMD_STATE_ID: int = 24
    IMD_STATION_ID: str = ""
    SATELLITE_SOURCE: str = "auto"
    SATELLITE_API_KEY: str = ""
    SATELLITE_BASE_URL: str = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
    TERRAIN_API_KEY: str = ""
    TERRAIN_BASE_URL: str = "https://api.open-meteo.com/v1/elevation"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    # Live weather providers: auto | openweather | weatherapi | openmeteo | imd | mock
    WEATHER_PROVIDER: str = "auto"
    OPENWEATHER_API_KEY: str = ""
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"
    WEATHERAPI_API_KEY: str = ""
    WEATHERAPI_BASE_URL: str = "https://api.weatherapi.com/v1"

    # Notifications
    SMS_API_KEY: str = ""
    SMS_PROVIDER: str = "mock"  # mock|fast2sms|other
    SMS_SENDER_ID: str = ""
    SMS_ROUTE: str = "qtp"
    FAST2SMS_API_KEY: str = ""
    EMAIL_API_KEY: str = ""
    EMAIL_FROM: str = "no-reply@example.com"
    PUSH_VAPID_PUBLIC_KEY: str = ""
    PUSH_VAPID_PRIVATE_KEY: str = ""

    # Bootstrap super admin (created on first boot when the users table is empty)
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
    BOOTSTRAP_ADMIN_NAME: str = "Administrator"

    # Storage
    STORAGE_BUCKET: str = ""
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_REGION: str = ""
    LOCAL_STORAGE_DIR: str = "./storage/media"
    LOCAL_STORAGE_PUBLIC_URL: str = "http://localhost:8000/media"

    # ML
    ML_MODEL_PATH: str = "./ml_artifacts/model.joblib"

    # Monitoring
    POLL_INTERVAL_SECONDS: int = 300
    ALERT_COOLDOWN_MINUTES: int = 60

    # News automation (auto-incident ingestion from news channels)
    NEWS_ENABLED: bool = True
    NEWS_PROVIDER: str = "auto"  # auto|google_rss|gdelt|mock
    NEWS_QUERY: str = "landslide OR landslip OR mudslide northeast india"
    NEWS_TIMESPAN_HOURS: int = 24
    NEWS_MAX_RECORDS: int = 50

    # Risk threshold defaults (configurable from admin)
    RISK_LEVELS: ClassVar[dict] = {
        "VERY_LOW": (0, 20),
        "LOW": (21, 40),
        "MODERATE": (41, 60),
        "HIGH": (61, 80),
        "CRITICAL": (81, 100),
    }

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return v
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
