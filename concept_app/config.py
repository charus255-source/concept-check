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

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
        names = ("GROQ_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY")
        missing = [name for name in names if not os.getenv(name, "").strip()]
        if missing:
            raise ValueError("Missing server configuration: " + ", ".join(missing))
        return cls(*(os.environ[name].strip() for name in names))
