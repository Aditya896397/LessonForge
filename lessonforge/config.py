"""Runtime configuration, read from environment variables / a local .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv is optional at import time
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    gemini_api_key: str = ""
    # Model used for drafting the lesson and the instructional review.
    model: str = "gemini-3.5-flash"
    # Model used for fact checking. Kept separate so a stronger model can be
    # used for verification without slowing down drafting.
    qc_model: str = "gemini-3.5-flash"
    youtube_api_key: str = ""  # optional: YouTube Data API v3 (scraping fallback otherwise)
    google_books_api_key: str = ""  # optional: avoids the shared anonymous Google Books quota
    # "auto": use Gemini Google Search grounding, fall back to web retrieval if the
    # key has no grounding quota. "gemini": grounding only. "web": retrieval only.
    search_backend: str = "auto"
    # Tried in order when a model's daily free-tier quota is used up (quotas are per model).
    fallback_models: tuple[str, ...] = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
    tavily_api_key: str = ""  # optional: real web search in the retrieval backend
    data_dir: Path = PROJECT_ROOT / "data" / "lessons"
    lesson_minutes: int = 45
    http_timeout: float = 12.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
            model=os.getenv("GEMINI_MODEL", cls.model),
            qc_model=os.getenv("GEMINI_QC_MODEL", os.getenv("GEMINI_MODEL", cls.qc_model)),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
            google_books_api_key=os.getenv("GOOGLE_BOOKS_API_KEY", ""),
            search_backend=os.getenv("SEARCH_BACKEND", "auto").lower(),
            fallback_models=tuple(m.strip() for m in os.getenv(
                "GEMINI_FALLBACK_MODELS", ",".join(cls.fallback_models)).split(",") if m.strip()),
            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            data_dir=Path(os.getenv("LESSONFORGE_DATA_DIR", str(cls.data_dir))),
        )


def get_settings() -> Settings:
    return Settings.from_env()
