"""
=============================================================================
VeriField Nexus — Application Configuration
=============================================================================
Centralized configuration loaded from environment variables using Pydantic
Settings. All secrets and feature flags are managed here.
=============================================================================
"""

import json
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from .env file.
    All configuration is centralized here for easy management.
    """

    # --- App Metadata ---
    app_name: str = "VeriField Nexus"
    app_version: str = "1.0.0"
    debug: bool = False
    dev_mode: bool = False  # Enable offline login bypass (set DEV_MODE=true in .env)
    solana_anchor_enabled: bool = (
        False  # Feature flag to toggle actual Solana blockchain anchoring
    )
    redis_url: str = "redis://localhost:6379/0"

    # --- S3 Storage Configuration ---
    s3_bucket: str = "verifield-nexus-media"
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region_name: str = "us-east-1"

    # --- Supabase Configuration ---
    supabase_url: str = ""
    supabase_key: str = ""  # Anon key (public, used by clients)
    supabase_service_key: str = ""  # Service role key (server-side only)

    # --- Database ---
    database_url: str = ""  # PostgreSQL async connection string

    # --- JWT Authentication ---
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    # --- CORS ---
    cors_origins: str = (
        '["http://localhost:3000","http://localhost:3001","http://127.0.0.1:3001","http://localhost:8000"]'
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string to list."""
        try:
            return json.loads(self.cors_origins)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    # --- Trust Engine Thresholds ---
    trust_gps_max_distance_km: float = 5.0  # Max distance from expected location
    trust_image_hash_threshold: int = 5  # Min hamming distance for uniqueness
    trust_max_submissions_per_hour: int = 10  # Max submissions before flagging
    trust_suspicious_hours_start: int = 2  # Night window start (2 AM)
    trust_suspicious_hours_end: int = 5  # Night window end (5 AM)

    # --- Twilio Configuration ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_validate_signature: bool = True

    # --- Registry Configuration ---
    verra_api_url: str = ""
    verra_api_key: str = ""
    goldstandard_api_url: str = ""
    goldstandard_api_key: str = ""

    # --- Feature Flags ---
    enable_digital_twins: bool = False
    enable_verified_registry_sync: bool = False
    enable_live_iot: bool = False
    enable_article6: bool = False
    enable_scada: bool = False
    enable_verra_sync: bool = False
    enable_gold_standard_sync: bool = False
    enable_ai_insights: bool = False
    enable_satellite_monitoring: bool = False

    @model_validator(mode="after")
    def clean_supabase_url(self) -> "Settings":
        if self.supabase_url:
            self.supabase_url = self.supabase_url.rstrip("/")
        return self

    @property
    def supabase_admin_key(self) -> str:
        """
        Return the service role key to use for administrative actions.
        Looks in:
        1. SUPABASE_SERVICE_ROLE_KEY environment variable (standard Supabase)
        2. SUPABASE_SERVICE_KEY environment variable (alternative name)
        3. Config's supabase_service_key field
        4. Config's supabase_key field (fallback for dev environments)
        """
        import os

        return (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_SERVICE_KEY")
            or self.supabase_service_key
            or self.supabase_key
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Singleton settings instance — imported throughout the app
settings = Settings()
