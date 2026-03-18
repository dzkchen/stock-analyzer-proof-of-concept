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
    gemini_api_key: Optional[str]
    news_api_key: Optional[str]
    gemini_enabled: bool
    news_enabled: bool


@dataclass(frozen=True)
class MarketDataSettings:
    default_period: str = "3mo"
    default_interval: str = "1d"


@dataclass(frozen=True)
class ScoringSettings:
    technical_weight: float = 0.40
    fundamental_weight: float = 0.30
    news_weight: float = 0.20
    reddit_weight: float = 0.10


@dataclass(frozen=True)
class SentimentMappingSettings:
    positive_score: float = 100.0
    neutral_score: float = 50.0
    negative_score: float = 0.0


@dataclass(frozen=True)
class Settings:
    api: APISettings
    market_data: MarketDataSettings
    scoring: ScoringSettings
    sentiment_mapping: SentimentMappingSettings


def _build_settings() -> Settings:
    gemini_key = os.getenv("GEMINI_API_KEY")
    news_key = os.getenv("NEWS_API_KEY")

    gemini_enabled = bool(gemini_key)
    news_enabled = bool(news_key)

    return Settings(
        api=APISettings(
            gemini_api_key=gemini_key,
            news_api_key=news_key,
            gemini_enabled=gemini_enabled,
            news_enabled=news_enabled,
        ),
        market_data=MarketDataSettings(),
        scoring=ScoringSettings(),
        sentiment_mapping=SentimentMappingSettings(),
    )


settings = _build_settings()
