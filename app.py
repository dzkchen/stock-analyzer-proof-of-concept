from __future__ import annotations

import streamlit as st

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

    # Initialize button state and last-analyzed values.
    if "analyze_clicked" not in st.session_state:
        st.session_state.analyze_clicked = False
    if "last_ticker" not in st.session_state:
        st.session_state.last_ticker = ""
    if "last_exchange" not in st.session_state:
        st.session_state.last_exchange = ""

    # If the user changes the ticker or exchange after a prior run, reset
    # the analyze flag so we do not auto-analyze on each keystroke.
    if (
        ticker != st.session_state.last_ticker
        or user_exchange != st.session_state.last_exchange
    ):
        st.session_state.analyze_clicked = False

    if not ticker:
        st.info("Enter a stock ticker above to begin.")
        return

    analyze = st.button("Analyze")
    if analyze:
        st.session_state.analyze_clicked = True

    if not st.session_state.analyze_clicked:
        return

    with st.spinner(f"Analyzing {ticker}..."):
        result: AnalysisResult = run_full_analysis(ticker=ticker, user_exchange=user_exchange)

    if not result.had_any_scores:
        st.error("Unable to compute any scores for this ticker. Please try again.")
        return

    # Record the last analyzed inputs and clear the analyze flag so that
    # subsequent edits do not automatically re-trigger analysis.
    st.session_state.last_ticker = ticker
    st.session_state.last_exchange = user_exchange
    st.session_state.analyze_clicked = False

    if result.sentiment_scores is not None:
        render_top_row(result.composite_score, result.sentiment_scores)

    if result.technical_df is not None:
        render_middle_row(result.technical_df, result.composite_score)

    if result.fundamental_result is not None:
        render_fundamental_audit(
            composite=result.composite_score,
            ratios=result.fundamental_result.ratios,
            audit_text=result.fundamental_audit_text,
            stats=result.fundamental_stats or {},
        )

    render_bottom_row(result.reddit_posts, result.news_articles)


if __name__ == "__main__":
    run_app()
