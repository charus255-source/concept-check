"""Server-only configuration, loaded lazily so imports do not contact providers."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = field(repr=False)
    supabase_url: str
    supabase_service_key: str = field(repr=False)
    session_secret: str = field(repr=False)

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
        names = ("GROQ_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SESSION_SECRET")
        missing = [name for name in names if not os.getenv(name, "").strip()]
        if missing:
            raise ValueError("Missing server configuration: " + ", ".join(missing))
        settings = cls(*(os.environ[name].strip() for name in names))
        if len(settings.session_secret) < 32 or settings.session_secret == settings.supabase_service_key:
            raise ValueError("SESSION_SECRET must be its own random value of at least 32 characters.")
        return settings
