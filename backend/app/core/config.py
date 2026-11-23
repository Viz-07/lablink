import os
from dataclasses import dataclass, field
from secrets import token_urlsafe


@dataclass(frozen=True)
class Settings:
    """Define runtime defaults for storage, AI, sessions, and booking."""

    production: bool = False
    storage: str = "memory"
    gcp_project: str = ""
    firestore_database: str = "(default)"
    ai_enabled: bool = True
    ai_provider: str = "vertex"
    gemini_model: str = "gemini-3.5-flash"
    gemini_location: str = "global"
    google_api_key: str = field(default="", repr=False)
    session_secret: str = field(default_factory=lambda: token_urlsafe(48), repr=False)
    session_ttl_minutes: int = 480
    demo_mode: bool = True
    seed_demo_data: bool = True
    booking_horizon_days: int = 14


def load_settings() -> Settings:
    """Read environment settings and validate deployment configuration."""
    env = os.environ
    production = env.get("APP_ENV") == "production"
    secret = env.get("SESSION_SECRET", "")
    storage = env.get("STORAGE_BACKEND", "memory")
    provider = env.get("AI_PROVIDER", "vertex")
    project = env.get("GCP_PROJECT", "")
    api_key = env.get("GOOGLE_API_KEY", "")
    if production and len(secret.encode()) < 32:
        raise ValueError("SESSION_SECRET must contain at least 32 bytes in production")
    if storage not in {"memory", "firestore"} or (storage == "firestore" and not project):
        raise ValueError("Firestore storage requires GCP_PROJECT")
    if provider not in {"vertex", "apikey"} or (provider == "apikey" and (production or not api_key)):
        raise ValueError("API key mode requires a development API key")
    return Settings(
        production=production,
        storage=storage,
        gcp_project=project,
        firestore_database=env.get("FIRESTORE_DATABASE", "(default)"),
        ai_enabled=env.get("AI_ENABLED", "true").lower() == "true",
        ai_provider=provider,
        gemini_model=env.get("GEMINI_MODEL", Settings.gemini_model),
        gemini_location=env.get("GEMINI_LOCATION", "global"),
        google_api_key=api_key,
        session_secret=secret or token_urlsafe(48),
        session_ttl_minutes=int(env.get("SESSION_TTL_MINUTES", "480")),
        demo_mode=env.get("DEMO_MODE", "true").lower() == "true",
        seed_demo_data=env.get("SEED_DEMO_DATA", "true").lower() == "true",
        booking_horizon_days=int(env.get("BOOKING_HORIZON_DAYS", "14")),
    )
