from __future__ import annotations

from dataclasses import dataclass
from typing import List

from data.social_data import RedditPost, NewsArticle, grab_news, pull_reddit_feed
from services.finbert_client import FinBertClient
from services.gemini_client import GeminiClient, GeminiSummaryRequest


@dataclass(frozen=True)
class SentimentScores:
    reddit_score: float
    news_score: float
    summary: str


def _extract_reddit_texts(posts: List[RedditPost]) -> List[str]:
    texts: List[str] = []
    for p in posts:
        combined = f"{p.title}\n\n{p.selftext}".strip()
        if combined:
            texts.append(combined)
    return texts


def _extract_news_texts(articles: List[NewsArticle]) -> List[str]:
    texts: List[str] = []
    for a in articles:
        combined = f"{a.title}. {a.description or ''}".strip()
        if combined:
            texts.append(combined)
    return texts


def calculate_average_sentiment_scores(
    ticker: str,
    company_query: str | None = None,
    company_display_name: str | None = None,
    exchange: str | None = None,
    top_k_for_summary: int = 5,
) -> SentimentScores:
    """
    sentiment scoring and summary generation.
    """
    reddit_posts = pull_reddit_feed(ticker, exchange=exchange)
    news_query = company_query or ticker
    news_articles = grab_news(news_query)

    reddit_texts = _extract_reddit_texts(reddit_posts)
    news_texts = _extract_news_texts(news_articles)

    if not reddit_texts and not news_texts:
        no_data_msg = (
            "No recent Reddit posts or news articles were found for this stock on the "
            "selected exchange. As a result, a qualitative market sentiment summary "
            "cannot be generated at this time."
        )
        return SentimentScores(
            reddit_score=0.0,
            news_score=0.0,
            summary=no_data_msg,
        )

    finbert = FinBertClient()

    reddit_score = finbert.average_numeric_score(reddit_texts) if reddit_texts else 0.0
    news_score = finbert.average_numeric_score(news_texts) if news_texts else 0.0

    top_reddit_snippets = [t for t in reddit_texts[:top_k_for_summary]]
    top_news_snippets = [t for t in news_texts[:top_k_for_summary]]

    if top_reddit_snippets or top_news_snippets:
        gemini = GeminiClient()
        summary_request = GeminiSummaryRequest(
            ticker=ticker,
            reddit_snippets=top_reddit_snippets,
            news_snippets=top_news_snippets,
            display_name=company_display_name,
        )
        summary_text = gemini.summarize_sentiment(summary_request)
    else:
        summary_text = (
            "Insufficient discussion or news content was available for this stock to "
            "generate a qualitative market sentiment summary."
        )

    return SentimentScores(
        reddit_score=reddit_score,
        news_score=news_score,
        summary=summary_text,
    )
