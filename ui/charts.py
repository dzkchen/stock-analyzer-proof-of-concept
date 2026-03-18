from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis.scoring import CompositeAIScore


def build_price_chart(
    df_with_scores: pd.DataFrame,
    composite_score: Optional[CompositeAIScore] = None,
) -> go.Figure:
    """
    Plotly chart showing the stock closing price over last 30 days
    """
    if df_with_scores.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Price chart unavailable",
            template="plotly_dark",
        )
        return fig

    df = df_with_scores.copy()
    df = df.sort_index()
    last_30 = df.tail(30)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        specs=[[{"type": "xy"}], [{"type": "bar"}]],
    )
    fig.add_trace(
        go.Scatter(
            x=last_30.index,
            y=last_30["Close"],
            mode="lines",
            name="Close Price",
            line=dict(color="#1f77b4", width=2),
        ),
        row=1,
        col=1,
    )

    fig.update_yaxes(title_text="Price", row=1, col=1)
    if composite_score is not None:
        labels = ["Technical", "Fundamental", "News", "Reddit", "Overall"]
        values = [
            composite_score.technical_score,
            composite_score.fundamental_score,
            composite_score.news_score,
            composite_score.reddit_score,
            composite_score.overall_score,
        ]
        colors = ["#2ca02c", "#1f77b4", "#ff7f0e", "#d62728", "#9467bd"]

        fig.add_trace(
            go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                name="Sentiment Scores",
            ),
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="Score (0-100)", row=2, col=1, range=[0, 100])

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        showlegend=False,
        title="Price (Last 30 Days) & Sentiment Snapshot",
    )

    return fig


def build_ai_score_gauge(overall_score: float) -> go.Figure:
    value = max(0.0, min(100.0, float(overall_score)))

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": " / 100"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#1f77b4"},
                "steps": [
                    {"range": [0, 33], "color": "#d62728"},
                    {"range": [33, 66], "color": "#ffbf00"},
                    {"range": [66, 100], "color": "#2ca02c"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 3},
                    "thickness": 0.75,
                    "value": value,
                },
            },
            title={"text": "Overall AI Score"},
        )
    )

    fig.update_layout(
        margin=dict(l=40, r=40, t=60, b=40),
        template="plotly_dark",
    )

    return fig
