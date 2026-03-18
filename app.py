from __future__ import annotations

import streamlit as st

from analysis.scoring import calculate_composite_score
from config.settings import ScoringSettings, settings
from core.workflow import AnalysisResult, run_full_analysis
from ui.layout import (
    render_bottom_row,
    render_fundamental_audit,
    render_header,
    render_middle_row,
    render_top_row,
)


def run_app() -> None:
    ticker, user_exchange = render_header()

    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    default_weights = settings.scoring

    st.sidebar.subheader("AI Score Weights (sum capped at 1.0)")
    technical_weight = st.sidebar.slider(
        "Technical weight",
        min_value=0.0,
        max_value=1.0,
        value=float(default_weights.technical_weight),
        step=0.05,
    )
    fundamental_weight = st.sidebar.slider(
        "Fundamental weight",
        min_value=0.0,
        max_value=1.0,
        value=float(default_weights.fundamental_weight),
        step=0.05,
    )
    news_weight = st.sidebar.slider(
        "News weight",
        min_value=0.0,
        max_value=1.0,
        value=float(default_weights.news_weight),
        step=0.05,
    )
    reddit_weight = st.sidebar.slider(
        "Reddit weight",
        min_value=0.0,
        max_value=1.0,
        value=float(default_weights.reddit_weight),
        step=0.05,
    )

    raw_weights = {
        "technical": technical_weight,
        "fundamental": fundamental_weight,
        "news": news_weight,
        "reddit": reddit_weight,
    }

    total_weight = sum(raw_weights.values())
    if total_weight > 1.0:
        st.error(
            "The sum of AI score weights exceeds 1.0. "
            "Please reduce one or more weights before running the analysis."
        )
        analyze_enabled = False
    else:
        analyze_enabled = True

    scoring_weights = ScoringSettings(
        technical_weight=raw_weights["technical"],
        fundamental_weight=raw_weights["fundamental"],
        news_weight=raw_weights["news"],
        reddit_weight=raw_weights["reddit"],
    )

    if "analyze_clicked" not in st.session_state:
        st.session_state.analyze_clicked = False
    if "last_ticker" not in st.session_state:
        st.session_state.last_ticker = ""
    if "last_exchange" not in st.session_state:
        st.session_state.last_exchange = ""

    if (
        ticker != st.session_state.last_ticker
        or user_exchange != st.session_state.last_exchange
    ):
        st.session_state.analyze_clicked = False

    if not ticker:
        st.info("Enter a stock ticker above to begin.")
        return

    analyze = st.button("Analyze", disabled=not analyze_enabled)
    if analyze:
        st.session_state.analyze_clicked = True

    if st.session_state.analyze_clicked:
        with st.spinner(f"Analyzing {ticker}..."):
            result: AnalysisResult = run_full_analysis(
                ticker=ticker,
                user_exchange=user_exchange,
            )
        st.session_state.last_result = result
        st.session_state.last_ticker = ticker
        st.session_state.last_exchange = user_exchange
        st.session_state.analyze_clicked = False
    else:
        cached: AnalysisResult | None = st.session_state.last_result
        if (
            cached is None
            or st.session_state.last_ticker != ticker
            or st.session_state.last_exchange != user_exchange
        ):
            return
        result = cached

    if not result.had_any_scores:
        st.error("Unable to compute any scores for this ticker. Please try again.")
        return

    fundamental_score = (
        result.fundamental_result.score if result.fundamental_result is not None else None
    )
    composite = calculate_composite_score(
        technical_score=result.technical_score,
        sentiment=result.sentiment_scores,
        fundamental_score=fundamental_score,
        weights=scoring_weights,
    )

    if result.sentiment_scores is not None:
        render_top_row(composite, result.sentiment_scores)

    if result.technical_df is not None:
        render_middle_row(result.technical_df, composite)

    if result.fundamental_result is not None:
        render_fundamental_audit(
            composite=composite,
            ratios=result.fundamental_result.ratios,
            audit_text=result.fundamental_audit_text,
            stats=result.fundamental_stats or {},
        )

    render_bottom_row(result.reddit_posts, result.news_articles)


if __name__ == "__main__":
    run_app()
