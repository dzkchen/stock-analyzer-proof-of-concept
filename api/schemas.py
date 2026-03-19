from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ScoresPayload(BaseModel):
    overall: float = 50.0
    technical: float = 50.0
    fundamental: float = 50.0
    news: float = 50.0
    reddit: float = 50.0


class PricePoint(BaseModel):
    date: str
    close: float


class RedditSource(BaseModel):
    subreddit: str
    title: str
    ups: int
    url: str


class NewsSource(BaseModel):
    source: str
    title: str
    description: str
    url: str
    published_at: str


class SourcesPayload(BaseModel):
    reddit: List[RedditSource] = Field(default_factory=list)
    news: List[NewsSource] = Field(default_factory=list)


class FundamentalPayload(BaseModel):
    ratios: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    ticker: str
    exchange: str
    had_any_scores: bool
    scores: ScoresPayload
    market_sentiment_summary: str
    fundamental_audit_text: str
    fundamental: FundamentalPayload
    price_points: List[PricePoint] = Field(default_factory=list)
    sources: SourcesPayload


class ErrorResponse(BaseModel):
    detail: str


def to_iso_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day).isoformat()
    return ""

