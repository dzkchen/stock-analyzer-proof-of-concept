from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import math
import pandas as pd

from analysis.sentiment_analysis import SentimentScores


TECHNICAL_WEIGHT = 0.40
FUNDAMENTAL_WEIGHT = 0.30
NEWS_WEIGHT = 0.20
REDDIT_WEIGHT = 0.10


@dataclass(frozen=True)
class CompositeAIScore:
    """
    Container for the component scores and final overall AI Score.
    All scores are in range [0, 100].
    """

    technical_score: float
    fundamental_score: float
    news_score: float
    reddit_score: float
    overall_score: float


def _sanitize_score(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    return v


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def extract_latest_technical_score(df_with_score: pd.DataFrame) -> Optional[float]:
    """
    Extract most recent 'Technical_Score' from a dataframe
    produced by `analysis.technical_analysis.add_technical_score`.
    """
    if df_with_score.empty or "Technical_Score" not in df_with_score.columns:
        return None
    latest = df_with_score["Technical_Score"].iloc[-1]
    return _sanitize_score(latest)


def compute_overall_ai_score(
    technical_score: Optional[float],
    sentiment: Optional[SentimentScores],
    fundamental_score: Optional[float] = None,
) -> CompositeAIScore:
    """
    Calculate the final Overall AI Score (0–100) using the weights:
      - 40% Technical Indicators 
      - 30% Fundamental 
      - 20% News Sentiment 
      - 10% Reddit Sentiment 

    Missing/invalid component scores:
      - Missing - excluded from the weighted sum
        and the remaining weights renormalized
      - If all components are missing - neutral 50.0
    """
    tech = _sanitize_score(technical_score)
    fundamental = _sanitize_score(fundamental_score)
    news = _sanitize_score(sentiment.news_score) if sentiment is not None else None
    reddit = _sanitize_score(sentiment.reddit_score) if sentiment is not None else None

    components = []
    if tech is not None:
        components.append(("technical", tech, TECHNICAL_WEIGHT))
    if fundamental is not None:
        components.append(("fundamental", fundamental, FUNDAMENTAL_WEIGHT))
    if news is not None:
        components.append(("news", news, NEWS_WEIGHT))
    if reddit is not None:
        components.append(("reddit", reddit, REDDIT_WEIGHT))

    if not components:
        overall = 50.0
        tech_out = fund_out = news_out = reddit_out = 50.0
    else:
        total_weight = sum(w for _, _, w in components)
        overall = sum(val * w for _, val, w in components) / total_weight

        tech_out = tech if tech is not None else 50.0
        fund_out = fundamental if fundamental is not None else 50.0
        news_out = news if news is not None else 50.0
        reddit_out = reddit if reddit is not None else 50.0

    return CompositeAIScore(
        technical_score=_clamp_score(tech_out),
        fundamental_score=_clamp_score(fund_out),
        news_score=_clamp_score(news_out),
        reddit_score=_clamp_score(reddit_out),
        overall_score=_clamp_score(overall),
    )


def calculate_composite_score(
    technical_score: Optional[float],
    sentiment: Optional[SentimentScores],
    fundamental_score: Optional[float] = None,
) -> CompositeAIScore:
    """
    Alias for compute_overall_ai_score to align with project terminology.
    """
    return compute_overall_ai_score(
        technical_score=technical_score,
        sentiment=sentiment,
        fundamental_score=fundamental_score,
    )

