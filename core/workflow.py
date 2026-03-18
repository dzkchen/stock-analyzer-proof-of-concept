from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from analysis.fundamental_analysis import FundamentalResult, score_fundamentals
from analysis.scoring import CompositeAIScore, calculate_composite_score, extract_latest_technical_score
from analysis.sentiment_analysis import SentimentScores, calculate_average_sentiment_scores
from analysis.technical_analysis import add_technical_score
from data.market_data import fetch_daily_history, fetch_fundamentals
from data.social_data import NewsArticle, RedditPost, grab_news, pull_reddit_feed
from services.gemini_client import FundamentalAuditRequest, GeminiClient


@dataclass(frozen=True)
class CompanyContext:
    ticker: str
    exchange: str
    company_name: str
    display_name: str
    news_query: str


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


def _build_company_context(
    ticker: str,
    fundamentals_raw: Dict[str, Any] | None,
    user_exchange: str | None,
) -> CompanyContext:
    info = (fundamentals_raw or {}).get("info", {}) or {}

    company_name = info.get("shortName") or info.get("longName") or ""

    yf_exchange = info.get("exchange") or info.get("fullExchangeName") or ""
    exchange = user_exchange if user_exchange and user_exchange != "OTHER" else yf_exchange

    if company_name and exchange:
        display_name = f"{company_name} ({exchange}: {ticker})"
    elif company_name:
        display_name = f"{company_name} ({ticker})"
    else:
        display_name = ticker

    if company_name:
        ticker_terms = [ticker]
        if exchange:
            ticker_terms.append(f"{exchange}: {ticker}")
        ticker_clause = " OR ".join(ticker_terms)
        news_query = f'"{company_name}" AND ({ticker_clause})'
    elif exchange:
        news_query = f"{exchange}: {ticker}"
    else:
        news_query = ticker

    return CompanyContext(
        ticker=ticker,
        exchange=exchange,
        company_name=company_name,
        display_name=display_name,
        news_query=news_query,
    )


def run_full_analysis(ticker: str, user_exchange: str | None = None) -> AnalysisResult:
    """
    Orchestrate the full analysis pipeline for a given ticker and exchange.
    This is UI-agnostic and intended to be called from Streamlit or other frontends.
    """
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
        summary_lines = [
            f"Ticker: {ticker}",
            f"Company: {info.get('shortName') or info.get('longName') or ''}",
            f"Forward P/E: {r.get('forward_pe', 'N/A')}",
            f"Debt/Equity: {r.get('debt_to_equity', 'N/A')}",
            f"Current Ratio: {r.get('current_ratio', 'N/A')}",
            f"Profit Margin: {r.get('profit_margin', 'N/A')}",
            f"Operating Margin: {r.get('operating_margin', 'N/A')}",
            f"Free Cash Flow: {r.get('free_cash_flow', 'N/A')}",
        ]
        fundamentals_text = "\n".join(str(line) for line in summary_lines)

        all_missing = all(
            r.get(key) in (None, "N/A")
            for key in (
                "forward_pe",
                "debt_to_equity",
                "current_ratio",
                "profit_margin",
                "operating_margin",
                "free_cash_flow",
            )
        )

        if all_missing:
            fundamental_audit_text = (
                "There is insufficient fundamental data available for this company "
                "to generate a meaningful audit. Key metrics such as P/E, "
                "Debt/Equity, Current Ratio, Profit Margin, Operating Margin, or "
                "Free Cash Flow are missing or reported as N/A."
            )
        else:
            gemini = GeminiClient()
            ctx = _build_company_context(ticker=ticker, fundamentals_raw=fundamentals_raw, user_exchange=user_exchange)
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

    company_ctx = _build_company_context(
        ticker=ticker,
        fundamentals_raw=fundamentals_raw,
        user_exchange=user_exchange,
    )

    try:
        sentiment_scores = calculate_average_sentiment_scores(
            ticker,
            company_query=company_ctx.news_query,
            company_display_name=company_ctx.display_name,
            exchange=company_ctx.exchange or None,
        )
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

