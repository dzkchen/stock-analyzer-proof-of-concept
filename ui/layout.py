from __future__ import annotations

from typing import Dict, List

import streamlit as st

from analysis.scoring import CompositeAIScore
from analysis.sentiment_analysis import SentimentScores
from data.social_data import NewsArticle, RedditPost
from ui.charts import build_ai_score_gauge, build_price_chart


def render_header() -> str:
    st.set_page_config(
        page_title="Stock Analyzer",
        layout="wide",
    )

    st.title("Stock Analyzer")
    st.caption("Quantitative technicals + qualitative sentiment, powered by LLMs.")

    with st.container():
        cols = st.columns([3, 1])
        with cols[0]:
            ticker = st.text_input("Stock Ticker", value="AAPL").upper().strip()
        with cols[1]:
            st.write("")
            st.write("")
            st.write(" ")

    return ticker


def render_top_row(
    composite: CompositeAIScore,
    sentiment: SentimentScores,
) -> None:
    col_gauge, col_summary = st.columns([1, 1])

    with col_gauge:
        gauge_fig = build_ai_score_gauge(composite.overall_score)
        st.plotly_chart(gauge_fig, use_container_width=True)

    with col_summary:
        st.subheader("Market Sentiment Summary")
        st.markdown(sentiment.summary or "_No summary available._")


def render_middle_row(
    df_with_scores,
    composite: CompositeAIScore,
) -> None:
    st.subheader("Price & Sentiment Overview")
    fig = build_price_chart(df_with_scores, composite_score=composite)
    st.plotly_chart(fig, use_container_width=True)


def render_fundamental_audit(
    composite: CompositeAIScore,
    ratios: Dict[str, float],
    audit_text: str,
    stats: Dict[str, float] | None = None,
) -> None:
    st.subheader("Fundamental Audit")

    col_metrics, col_audit = st.columns([1.2, 1.8])

    with col_metrics:
        st.markdown("#### Snapshot")
        stats = stats or {}
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            mc = stats.get("market_cap")
            mc_label = (
                f"{mc/1_000_000_000_000:.2f}T"
                if isinstance(mc, (int, float)) and mc >= 1_000_000_000_000
                else f"{mc/1_000_000_000:.1f}B"
                if isinstance(mc, (int, float)) and mc >= 1_000_000_000
                else f"{mc/1_000_000:.1f}M"
                if isinstance(mc, (int, float)) and mc >= 1_000_000
                else f"{mc:,.0f}"
                if isinstance(mc, (int, float))
                else "N/A"
            )
            st.metric("Market Cap", mc_label)

        with s2:
            pe = stats.get("pe_ratio")
            st.metric("P/E Ratio", f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A")

        with s3:
            high = stats.get("fifty_two_week_high")
            st.metric(
                "52W High",
                f"{high:,.2f}" if isinstance(high, (int, float)) else "N/A",
            )

        with s4:
            low = stats.get("fifty_two_week_low")
            st.metric(
                "52W Low",
                f"{low:,.2f}" if isinstance(low, (int, float)) else "N/A",
            )

        v1, _, _ = st.columns(3)
        with v1:
            vol = stats.get("volume")
            st.metric(
                "Volume",
                f"{vol:,.0f}" if isinstance(vol, (int, float)) else "N/A",
            )

        st.markdown("#### Key Ratios")
        m1, m2, m3 = st.columns(3)

        with m1:
            st.metric(
                "Forward P/E",
                f"{ratios.get('forward_pe', float('nan')):.2f}"
                if "forward_pe" in ratios
                else "N/A",
            )
        with m2:
            st.metric(
                "Debt / Equity",
                f"{ratios.get('debt_to_equity', float('nan')):.2f}"
                if "debt_to_equity" in ratios
                else "N/A",
            )
        with m3:
            st.metric(
                "Current Ratio",
                f"{ratios.get('current_ratio', float('nan')):.2f}"
                if "current_ratio" in ratios
                else "N/A",
            )

        m4, m5, m6 = st.columns(3)
        with m4:
            st.metric(
                "Profit Margin",
                f"{ratios.get('profit_margin', float('nan'))*100:.1f}%"
                if "profit_margin" in ratios
                else "N/A",
            )
        with m5:
            st.metric(
                "Operating Margin",
                f"{ratios.get('operating_margin', float('nan'))*100:.1f}%"
                if "operating_margin" in ratios
                else "N/A",
            )
        with m6:
            st.metric(
                "Free Cash Flow",
                f"{ratios.get('free_cash_flow', float('nan'))/1_000_000:.1f}M"
                if "free_cash_flow" in ratios
                else "N/A",
            )

        st.markdown(
            f"**Fundamental Score:** {composite.fundamental_score:.1f} / 100",
        )

    with col_audit:
        st.markdown("#### Gemini Fundamental Audit")
        st.markdown(audit_text or "_No fundamental audit available._")


def render_bottom_row(
    reddit_posts: List[RedditPost],
    news_articles: List[NewsArticle],
) -> None:
    st.subheader("Raw Data Feeds")
    col_reddit, col_news = st.columns(2)

    with col_reddit:
        st.markdown("### Reddit Posts")
        if not reddit_posts:
            st.write("No Reddit posts found.")
        else:
            for post in reddit_posts[:20]:
                st.markdown(
                    f"- **[{post.subreddit}] {post.title}**  \n"
                    f"  👍 {post.ups}  •  [Open thread]({post.url})"
                )

    with col_news:
        st.markdown("### News Articles")
        if not news_articles:
            st.write("No news articles found.")
        else:
            for article in news_articles[:20]:
                st.markdown(
                    f"- **{article.title}**  \n"
                    f"  {article.description or ''}  \n"
                    f"  [Read more]({article.url})"
                )
