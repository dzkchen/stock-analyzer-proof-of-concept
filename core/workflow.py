from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from analysis.fundamental_analysis import FundamentalResult, score_fundamentals
from analysis.scoring import (
    CompositeAIScore,
    calculate_composite_score,
    extract_latest_technical_score,
)
from analysis.sentiment_analysis import SentimentScores, calculate_average_sentiment_scores
from analysis.technical_analysis import add_technical_score
from core.context import CompanyContext, build_company_context
from config.settings import ScoringSettings
from data.market_data import fetch_daily_history, fetch_fundamentals
from data.social_data import NewsArticle, RedditPost, grab_news, pull_reddit_feed
from services.gemini_client import FundamentalAuditRequest, GeminiClient


@dataclass(frozen=True)
class AnalysisResult:
    price_history: Optional[pd.DataFrame]
    technical_df: Optional[pd.DataFrame]
    technical_score: Optional[float]
    fundamental_result: Optional[FundamentalResult]
    fundamental_stats: Dict[str, Any]
    fundamental_audit_text: str
    sentiment_scores: Optional[SentimentScores]
    composite_score: Optional[CompositeAIScore]
    reddit_posts: List[RedditPost]
    news_articles: List[NewsArticle]
    company_context: CompanyContext
    had_any_scores: bool


def _is_unavailable_metric(metric_name: str, value: Any) -> bool:
    if value in (None, "", "N/A"):
        return True
    if metric_name == "free_cash_flow":
        try:
            return float(value) == 0.0
        except (TypeError, ValueError):
            return False
    return False


def run_full_analysis(
    ticker: str,
    user_exchange: str | None = None,
    weights: ScoringSettings | None = None,
) -> AnalysisResult:
    price_df: Optional[pd.DataFrame] = None
    technical_df: Optional[pd.DataFrame] = None
    technical_score: Optional[float] = None
    sentiment_scores: Optional[SentimentScores] = None
    fundamental_result: Optional[FundamentalResult] = None
    fundamental_stats: Dict[str, Any] = {}
    fundamental_audit_text: str = ""
    reddit_posts: List[RedditPost] = []
    news_articles: List[NewsArticle] = []

    try:
        price_df = fetch_daily_history(ticker)
        technical_df = add_technical_score(price_df)
        technical_score = extract_latest_technical_score(technical_df)
    except Exception:
        price_df = None
        technical_df = None
        technical_score = None

    fundamentals_raw: Dict[str, Any] | None = None
    try:
        fundamentals_raw = fetch_fundamentals(ticker)
        fundamental_result = score_fundamentals(fundamentals_raw)

        info = fundamentals_raw.get("info", {}) or {}
        fundamental_stats = {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
        }

        r = fundamental_result.ratios
        normalized_ratios = {
            "forward_pe": r.get("forward_pe"),
            "debt_to_equity": r.get("debt_to_equity"),
            "current_ratio": r.get("current_ratio"),
            "profit_margin": r.get("profit_margin"),
            "operating_margin": r.get("operating_margin"),
            "free_cash_flow": r.get("free_cash_flow"),
        }
        for key, raw_value in normalized_ratios.items():
            if _is_unavailable_metric(key, raw_value):
                normalized_ratios[key] = "N/A"

        summary_lines = [
            f"Ticker: {ticker}",
            f"Company: {info.get('shortName') or info.get('longName') or ''}",
            f"Forward P/E: {normalized_ratios.get('forward_pe', 'N/A')}",
            f"Debt/Equity: {normalized_ratios.get('debt_to_equity', 'N/A')}",
            f"Current Ratio: {normalized_ratios.get('current_ratio', 'N/A')}",
            f"Profit Margin: {normalized_ratios.get('profit_margin', 'N/A')}",
            f"Operating Margin: {normalized_ratios.get('operating_margin', 'N/A')}",
            f"Free Cash Flow: {normalized_ratios.get('free_cash_flow', 'N/A')}",
        ]

        required_keys = (
            "forward_pe",
            "debt_to_equity",
            "current_ratio",
            "profit_margin",
            "operating_margin",
            "free_cash_flow",
        )
        missing_keys = [
            key for key in required_keys if _is_unavailable_metric(key, normalized_ratios.get(key))
        ]

        fundamentals_text = "\n".join(str(line) for line in summary_lines)
        if missing_keys:
            missing_lines = [
                "",
                "Missing or N/A metrics:",
                *[f"- {key}" for key in missing_keys],
                "",
                "When forming your audit, use only the metrics that are present.",
                "Treat all missing or N/A metrics above as unavailable data and do not",
                "infer negative business performance from those gaps.",
            ]
            fundamentals_text = "\n".join([fundamentals_text, *missing_lines])

        all_missing = len(missing_keys) == len(required_keys)

        if all_missing:
            fundamental_audit_text = (
                "There is insufficient fundamental data available for this company "
                "to generate a meaningful audit. Key metrics such as P/E, "
                "Debt/Equity, Current Ratio, Profit Margin, Operating Margin, or "
                "Free Cash Flow are missing or reported as N/A."
            )
        else:
            gemini = GeminiClient()
            ctx = build_company_context(
                ticker=ticker,
                fundamentals_raw=fundamentals_raw,
                user_exchange=user_exchange,
            )
            audit_request = FundamentalAuditRequest(
                ticker=ticker,
                summary_text=fundamentals_text,
                display_name=ctx.display_name,
            )
            fundamental_audit_text = gemini.generate_fundamental_audit(audit_request)
    except Exception:
        fundamental_result = None
        fundamental_audit_text = ""
        fundamental_stats = {}

    company_ctx = build_company_context(
        ticker=ticker,
        fundamentals_raw=fundamentals_raw,
        user_exchange=user_exchange,
    )

    try:
        sentiment_scores = calculate_average_sentiment_scores(company=company_ctx)
    except Exception:
        sentiment_scores = None

    try:
        reddit_posts = pull_reddit_feed(ticker, exchange=company_ctx.exchange or None)
    except Exception:
        reddit_posts = []

    try:
        news_articles = grab_news(company_ctx.news_query)
    except Exception:
        news_articles = []

    composite: Optional[CompositeAIScore]
    if technical_score is None and sentiment_scores is None and fundamental_result is None:
        composite = None
        had_any_scores = False
    else:
        fundamental_score = fundamental_result.score if fundamental_result is not None else None
        composite = calculate_composite_score(
            technical_score=technical_score,
            sentiment=sentiment_scores,
            fundamental_score=fundamental_score,
            weights=weights,
        )
        had_any_scores = True

    return AnalysisResult(
        price_history=price_df,
        technical_df=technical_df,
        technical_score=technical_score,
        fundamental_result=fundamental_result,
        fundamental_stats=fundamental_stats,
        fundamental_audit_text=fundamental_audit_text,
        sentiment_scores=sentiment_scores,
        composite_score=composite,
        reddit_posts=reddit_posts,
        news_articles=news_articles,
        company_context=company_ctx,
        had_any_scores=had_any_scores,
    )

