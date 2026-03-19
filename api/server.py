from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AnalyzeResponse,
    FundamentalPayload,
    NewsSource,
    PricePoint,
    RedditSource,
    ScoresPayload,
    SourcesPayload,
    to_iso_datetime,
)
from core.workflow import AnalysisResult, run_full_analysis


app = FastAPI(
    title="Stock Analyzer API",
    version="0.1.0",
    description="API wrapper for the Stock Analyzer workflow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _serialize_price_points(result: AnalysisResult, limit: int = 30) -> List[PricePoint]:
    if result.price_history is None or result.price_history.empty:
        return []
    if "Close" not in result.price_history.columns:
        return []

    rows = result.price_history.sort_index().tail(limit)
    points: List[PricePoint] = []
    for idx, row in rows.iterrows():
        if hasattr(idx, "strftime"):
            date_label = idx.strftime("%Y-%m-%d")
        elif hasattr(idx, "isoformat"):
            date_label = idx.isoformat()
        else:
            date_label = str(idx)

        points.append(
            PricePoint(
                date=date_label,
                close=_safe_float(row.get("Close"), default=0.0),
            )
        )
    return points


def _serialize_sources(result: AnalysisResult) -> SourcesPayload:
    reddit = [
        RedditSource(
            subreddit=post.subreddit,
            title=post.title,
            ups=int(post.ups),
            url=post.url,
        )
        for post in result.reddit_posts[:20]
    ]

    news = [
        NewsSource(
            source=article.source,
            title=article.title,
            description=article.description,
            url=article.url,
            published_at=to_iso_datetime(article.published_at),
        )
        for article in result.news_articles[:20]
    ]

    return SourcesPayload(reddit=reddit, news=news)


def _serialize_response(ticker: str, exchange: str, result: AnalysisResult) -> AnalyzeResponse:
    composite = result.composite_score
    sentiment_summary = (
        result.sentiment_scores.summary
        if result.sentiment_scores is not None and result.sentiment_scores.summary
        else ""
    )
    ratios: Dict[str, Any] = (
        result.fundamental_result.ratios if result.fundamental_result is not None else {}
    )

    scores = ScoresPayload(
        overall=_safe_float(getattr(composite, "overall_score", 50.0), default=50.0),
        technical=_safe_float(getattr(composite, "technical_score", 50.0), default=50.0),
        fundamental=_safe_float(getattr(composite, "fundamental_score", 50.0), default=50.0),
        news=_safe_float(getattr(composite, "news_score", 50.0), default=50.0),
        reddit=_safe_float(getattr(composite, "reddit_score", 50.0), default=50.0),
    )

    return AnalyzeResponse(
        ticker=ticker.upper().strip(),
        exchange=exchange.upper().strip(),
        had_any_scores=result.had_any_scores,
        scores=scores,
        market_sentiment_summary=sentiment_summary,
        fundamental_audit_text=result.fundamental_audit_text or "",
        fundamental=FundamentalPayload(
            ratios=ratios,
            stats=result.fundamental_stats or {},
        ),
        price_points=_serialize_price_points(result=result, limit=30),
        sources=_serialize_sources(result=result),
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/analyze", response_model=AnalyzeResponse)
def analyze(
    ticker: str = Query(..., min_length=1, max_length=12),
    exchange: str = Query("NASDAQ", min_length=2, max_length=12),
) -> AnalyzeResponse:
    symbol = ticker.upper().strip()
    market = exchange.upper().strip()

    if not symbol:
        raise HTTPException(status_code=400, detail="Ticker must be a non-empty string.")

    try:
        result = run_full_analysis(ticker=symbol, user_exchange=market)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    if not result.had_any_scores:
        raise HTTPException(
            status_code=422,
            detail="Unable to compute any scores for this ticker.",
        )

    return _serialize_response(ticker=symbol, exchange=market, result=result)

