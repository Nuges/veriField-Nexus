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



    app_env: str = "development"  # development, test, staging, production

    # --- JWT Authentication ---

    jwt_secret: str = ""

    jwt_algorithm: str = "HS256"

    # --- Bootstrap Super Admin Configuration ---

    bootstrap_super_admin_email: str = ""
    verifield_bootstrap_admin_email: str = ""

    @property
    def is_production(self) -> bool:
        """
        Return True if operating in a production environment.
        Checks APP_ENV, ENVIRONMENT, or default when debug=False and dev_mode=False.
        """
        import os
        env = (
            os.environ.get("APP_ENV")
            or os.environ.get("ENVIRONMENT")
            or self.app_env
        ).strip().lower()
        if env in ("prod", "production"):
            return True
        if env in ("dev", "development", "test", "testing", "local"):
            return False
        return not self.debug and not self.dev_mode

    @property
    def authorized_bootstrap_admin_email(self) -> str:
        """
        Return the email address authorized to bootstrap the platform Super Admin.
        Configurable via VERIFIELD_BOOTSTRAP_ADMIN_EMAIL or SUPER_ADMIN_EMAIL env vars.

        In production:
        - Must be explicitly configured via VERIFIELD_BOOTSTRAP_ADMIN_EMAIL or SUPER_ADMIN_EMAIL.
        - If not configured, returns empty string "" (bootstrap disabled, no default privilege).

        In development / test:
        - If configured via env vars, uses that.
        - Otherwise, falls back to development administrator identity (DEV_ADMIN_EMAIL or dev identity).
        """
        import os
        configured = (
            os.environ.get("VERIFIELD_BOOTSTRAP_ADMIN_EMAIL")
            or os.environ.get("SUPER_ADMIN_EMAIL")
            or self.verifield_bootstrap_admin_email
            or self.bootstrap_super_admin_email
        )
        if configured and configured.strip():
            return configured.strip().lower()

        if self.is_production:
            # In production, NEVER use a fallback. Bootstrap is disabled if not explicitly configured.
            return ""

        # Development / Test environment fallback
        return (os.environ.get("DEV_ADMIN_EMAIL") or "segunoluwole22@gmail.com").strip().lower()



    # --- CORS ---

    cors_origins: str = (

        '["http://localhost:3000","http://localhost:3001","http://127.0.0.1:3001","http://localhost:8000"]'

    )



    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string, comma-separated string, or wildcard."""
        if not self.cors_origins:
            return ["http://localhost:3000", "http://localhost:3001"]
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]



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

    # --- Resend / Email Configuration (Deferred pending production domain) ---
    email_notifications_enabled: bool = False
    resend_api_key: str = ""
    resend_from_email: str = ""
    resend_from_name: str = "VeriField Nexus"



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



    # --- Encryption & Evidence Protection ---

    verifield_encryption_key: str = ""

    evidence_auto_encrypt_sensitive: bool = True

    evidence_seal_on_verification: bool = True

    evidence_access_log_enabled: bool = True



    @model_validator(mode="after")

    def validate_security_settings(self) -> "Settings":

        if self.supabase_url:

            self.supabase_url = self.supabase_url.rstrip("/")

        # Safeguard: Prevent DEV_MODE when DEBUG=False in production

        if self.dev_mode and not self.debug:

            raise ValueError(

                "CRITICAL SECURITY CONFIGURATION ERROR: DEV_MODE cannot be enabled when DEBUG=False."

            )

        return self



    @property
    def effective_jwt_secret(self) -> str:
        """
        Return the secret used for signing/verifying local JWT tokens securely.
        In production mode (dev_mode=False and debug=False), an explicit non-default secret is mandatory.
        In development mode, falls back to 'verifield-dev-secret-key' for local test environments.
        """
        # Try explicit JWT_SECRET first
        if self.jwt_secret and self.jwt_secret not in ("", "verifield-dev-secret-key"):
            return self.jwt_secret
        # Try SECRET_KEY as fallback
        if hasattr(self, "secret_key") and self.secret_key and self.secret_key not in ("", "verifield-dev-secret-key"):
            return self.secret_key
        # In production mode, refuse to operate with a default secret
        if not self.dev_mode and not self.debug:
            raise RuntimeError(
                "CRITICAL: JWT_SECRET environment variable is not set. "
                "VeriField Nexus refuses to start in production without an explicit JWT secret."
            )
        # Dev mode only — safe default for local development
        return "verifield-dev-secret-key"





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
