from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from config.settings import settings


REDDIT_USER_AGENT = "ai-stock-analyzer/0.1 (by u/your_username)"
REDDIT_SUBREDDITS = ("wallstreetbets", "stocks", "investing")


@dataclass(frozen=True)
class RedditPost:
    subreddit: str
    title: str
    selftext: str
    ups: int
    url: str


@dataclass(frozen=True)
class NewsArticle:
    source: str
    title: str
    description: str
    url: str
    published_at: datetime


def pull_reddit_feed(
    ticker: str,
    limit_per_subreddit: int = 50,
) -> List[RedditPost]:
    """
    Recent Reddit posts mentioning `ticker` from target subreddits (public .json).
    """
    if not ticker:
        raise ValueError("ticker must be a non-empty string.")

    headers = {
        "User-Agent": REDDIT_USER_AGENT,
    }

    posts: List[RedditPost] = []

    for sub in REDDIT_SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/search.json"
        params = {
            "q": ticker,
            "restrict_sr": 1,
            "sort": "hot",
            "t": "week",
            "limit": limit_per_subreddit,
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException:
            continue

        data = resp.json()

        children = data.get("data", {}).get("children", [])
        for child in children:
            d = child.get("data", {})
            posts.append(
                RedditPost(
                    subreddit=sub,
                    title=d.get("title") or "",
                    selftext=d.get("selftext") or "",
                    ups=int(d.get("ups") or 0),
                    url=f"https://www.reddit.com{d.get('permalink')}"
                    if d.get("permalink")
                    else "",
                )
            )

    posts.sort(key=lambda p: p.ups, reverse=True)
    return posts


def grab_news(
    query: str,
    days: int = 7,
    page_size: int = 50,
) -> List[NewsArticle]:
    """
    NewsAPI results for `query`; uses configured key, returns normalized articles.
    """
    api_key = settings.api.news_api_key
    if not api_key:
        raise RuntimeError("NewsAPI key is not configured.")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": start.date().isoformat(),
        "to": end.date().isoformat(),
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": page_size,
        "apiKey": api_key,
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    payload: Dict[str, Any] = resp.json()

    articles: List[NewsArticle] = []
    for a in payload.get("articles", []):
        published_raw: Optional[str] = a.get("publishedAt")
        published_at = end
        if published_raw:
            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                published_at = end

        articles.append(
            NewsArticle(
                source=(a.get("source") or {}).get("name") or "",
                title=a.get("title") or "",
                description=a.get("description") or "",
                url=a.get("url") or "",
                published_at=published_at,
            )
        )

    return articles

