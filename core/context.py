from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class CompanyContext:

    ticker: str
    exchange: str
    company_name: str
    display_name: str
    news_query: str


def build_company_context(
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

