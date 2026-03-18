from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf

from config.settings import settings


def fetch_daily_history(
    ticker: str,
    period: Optional[str] = None,
    interval: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch the last N period of daily price/volume data for a single ticker.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("ticker must be a non-empty string.")

    use_period = period or settings.market_data.default_period
    use_interval = interval or settings.market_data.default_interval

    ticker_obj = yf.Ticker(ticker)
    df = ticker_obj.history(period=use_period, interval=use_interval, auto_adjust=False)

    if df.empty:
        raise ValueError(f"No historical data returned for ticker '{ticker}'.")

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    expected_cols = {"Open", "High", "Low", "Close", "Volume"}
    missing = expected_cols.difference(df.columns)
    if missing:
        raise ValueError(
            f"Historical data for '{ticker}' is missing expected columns: {missing}"
        )

    return df


def fetch_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Fetch fundamental data for `ticker` with yfinance.
    If datasets are unavailable - returned as empty structures
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("ticker must be a non-empty string.")

    ticker_obj = yf.Ticker(ticker)

    raw_info = getattr(ticker_obj, "info", None)
    info: Dict[str, Any] = dict(raw_info) if isinstance(raw_info, dict) else {}

    raw_bs = getattr(ticker_obj, "balance_sheet", None)
    balance_sheet = raw_bs if isinstance(raw_bs, pd.DataFrame) else pd.DataFrame()

    raw_cf = getattr(ticker_obj, "cashflow", None)
    cashflow = raw_cf if isinstance(raw_cf, pd.DataFrame) else pd.DataFrame()

    return {
        "info": info,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
    }

