from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class APISettings:
    """API keys"""

    gemini_api_key: Optional[str]
    news_api_key: Optional[str]


@dataclass(frozen=True)
class MarketDataSettings:
    """Market data config"""

    default_period: str = "3mo"
    default_interval: str = "1d"


@dataclass(frozen=True)
class Settings:
    api: APISettings
    market_data: MarketDataSettings


def _build_settings() -> Settings:
    gemini_key = os.getenv("GEMINII_API_KEY") or os.getenv("GEMINI_API_KEY")
    news_key = os.getenv("NEWSS_API_KEY") or os.getenv("NEWS_API_KEY")

    return Settings(
        api=APISettings(
            gemini_api_key=gemini_key,
            news_api_key=news_key,
        ),
        market_data=MarketDataSettings(),
    )


settings = _build_settings()
