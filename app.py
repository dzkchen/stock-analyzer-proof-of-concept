from __future__ import annotations

import streamlit as st

from analysis.fundamental_analysis import FundamentalResult, score_fundamentals
from analysis.scoring import (
    CompositeAIScore,
    calculate_composite_score,
    extract_latest_technical_score,
)
from analysis.sentiment_analysis import SentimentScores, calculate_average_sentiment_scores
from analysis.technical_analysis import add_technical_score
from data.market_data import fetch_daily_history, fetch_fundamentals
from data.social_data import grab_news, pull_reddit_feed
from services.gemini_client import FundamentalAuditRequest, GeminiClient
from ui.layout import (
    render_bottom_row,
    render_fundamental_audit,
    render_header,
    render_middle_row,
    render_top_row,
)


def run_app() -> None:
    ticker = render_header()

    if not ticker:
        st.info("Enter a stock ticker above to begin.")
        return

    if "analyze_clicked" not in st.session_state:
        st.session_state.analyze_clicked = False

    analyze = st.button("Analyze")
    if analyze:
        st.session_state.analyze_clicked = True

    if not st.session_state.analyze_clicked:
        return

    with st.spinner(f"Analyzing {ticker}..."):
        price_df = None
        df_with_scores = None
        technical_score = None
        sentiment_scores: SentimentScores | None = None
        fundamental_result: FundamentalResult | None = None
        fundamental_stats: dict | None = None
        fundamental_audit_text: str = ""
        composite: CompositeAIScore | None = None
        reddit_posts = []
        news_articles = []

        try:
            price_df = fetch_daily_history(ticker)
            df_with_scores = add_technical_score(price_df)
            technical_score = extract_latest_technical_score(df_with_scores)
        except Exception as exc:
            st.error(f"Failed to fetch or compute technical data: {exc}")

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

            company_name = info.get("shortName") or info.get("longName") or ""
            exchange = info.get("exchange") or info.get("fullExchangeName") or ""

            if company_name and exchange:
                company_display_name = f"{company_name} ({exchange}: {ticker})"
            elif company_name:
                company_display_name = f"{company_name} ({ticker})"
            else:
                company_display_name = ticker

            r = fundamental_result.ratios
            summary_lines = [
                f"Ticker: {ticker}",
                f"Company: {company_name or company_display_name}",
                f"Forward P/E: {r.get('forward_pe', 'N/A')}",
                f"Debt/Equity: {r.get('debt_to_equity', 'N/A')}",
                f"Current Ratio: {r.get('current_ratio', 'N/A')}",
                f"Profit Margin: {r.get('profit_margin', 'N/A')}",
                f"Operating Margin: {r.get('operating_margin', 'N/A')}",
                f"Free Cash Flow: {r.get('free_cash_flow', 'N/A')}",
            ]
            fundamentals_text = "\n".join(str(line) for line in summary_lines)

            gemini = GeminiClient()
            audit_request = FundamentalAuditRequest(
                ticker=ticker,
                summary_text=fundamentals_text,
                display_name=company_display_name,
            )
            fundamental_audit_text = gemini.generate_fundamental_audit(audit_request)
        except Exception as exc:
            st.error(f"Failed to compute fundamental analysis: {exc}")
            fundamental_result = None
            fundamental_audit_text = ""
            fundamental_stats = None
            company_display_name = ticker

        try:
            sentiment_scores = calculate_average_sentiment_scores(
                ticker,
                company_query=company_display_name,
                company_display_name=company_display_name,
            )
        except Exception as exc:
            st.error(f"Failed to compute sentiment scores: {exc}")

        try:
            reddit_posts = pull_reddit_feed(ticker)
        except Exception:
            reddit_posts = []

        try:
            news_articles = grab_news(ticker)
        except Exception:
            news_articles = []

        if technical_score is None and sentiment_scores is None and fundamental_result is None:
            st.error("Unable to compute any scores for this ticker. Please try again.")
            return

        fundamental_score = fundamental_result.score if fundamental_result is not None else None

        composite = calculate_composite_score(
            technical_score=technical_score,
            sentiment=sentiment_scores,
            fundamental_score=fundamental_score,
        )

    if sentiment_scores is not None:
        render_top_row(composite, sentiment_scores)

    if df_with_scores is not None:
        render_middle_row(df_with_scores, composite)

    if fundamental_result is not None:
        render_fundamental_audit(
            composite=composite,
            ratios=fundamental_result.ratios,
            audit_text=fundamental_audit_text,
            stats=fundamental_stats or {},
        )

    render_bottom_row(reddit_posts, news_articles)


if __name__ == "__main__":
    run_app()
