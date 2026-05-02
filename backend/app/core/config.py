"""
=============================================================================
VeriField Nexus — Application Configuration
=============================================================================
Centralized configuration loaded from environment variables using Pydantic
Settings. All secrets and feature flags are managed here.
=============================================================================
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    """
    Application settings loaded from .env file.
    All configuration is centralized here for easy management.
    """

    # --- App Metadata ---
    app_name: str = "VeriField Nexus"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- Supabase Configuration ---
    supabase_url: str = ""
    supabase_key: str = ""          # Anon key (public, used by clients)
    supabase_service_key: str = ""  # Service role key (server-side only)

    # --- Database ---
    database_url: str = ""  # PostgreSQL async connection string

    # --- JWT Authentication ---
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    # --- CORS ---
    cors_origins: str = '["http://localhost:3000","http://localhost:3001","http://127.0.0.1:3001","http://localhost:8000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string to list."""
        try:
            return json.loads(self.cors_origins)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    # --- Trust Engine Thresholds ---
    trust_gps_max_distance_km: float = 5.0        # Max distance from expected location
    trust_image_hash_threshold: int = 5            # Min hamming distance for uniqueness
    trust_max_submissions_per_hour: int = 10       # Max submissions before flagging
    trust_suspicious_hours_start: int = 2           # Night window start (2 AM)
    trust_suspicious_hours_end: int = 5             # Night window end (5 AM)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Singleton settings instance — imported throughout the app
settings = Settings()
