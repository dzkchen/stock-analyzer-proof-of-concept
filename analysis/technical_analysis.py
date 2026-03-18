from __future__ import annotations

import pandas as pd
import pandas_ta_classic as ta


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Some indicator stuff
    """
    required_cols = {"Close", "High", "Low", "Volume"}
    if not required_cols.issubset(df.columns):
        missing = required_cols.difference(df.columns)
        raise ValueError(f"Missing required columns for technicals: {missing}")

    df = df.copy()
    df["RSI_14"] = ta.rsi(df["Close"], length=14)

    macd = ta.macd(
        df["Close"],
        fast=12,
        slow=26,
        signal=9,
    )
    if macd is not None:
        df["MACD_12_26_9"] = macd["MACD_12_26_9"]
        df["MACD_signal_12_26_9"] = macd["MACDs_12_26_9"]
        df["MACD_hist_12_26_9"] = macd["MACDh_12_26_9"]

    df["SMA_20"] = ta.sma(df["Close"], length=20)
    df["SMA_50"] = ta.sma(df["Close"], length=50)

    bbands = ta.bbands(
        df["Close"],
        length=20,
        std=2.0,
    )
    if bbands is not None:
        df["BB_lower"] = bbands["BBL_20_2.0"]
        df["BB_middle"] = bbands["BBM_20_2.0"]
        df["BB_upper"] = bbands["BBU_20_2.0"]

    df["VWAP"] = ta.vwap(
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        volume=df["Volume"],
    )

    return df


def compute_technical_score(row: pd.Series) -> float:
    """
    Technical Score in [0, 100] from indicator values
    """
    close = float(row["Close"])

    rsi = float(row["RSI_14"])
    if rsi <= 30:
        rsi_score = 100.0
    elif rsi >= 70:
        rsi_score = 0.0
    elif rsi <= 50:
        rsi_score = 100.0 - (rsi - 30) * (50.0 / 20.0)
    else:
        rsi_score = 50.0 - (rsi - 50) * (50.0 / 20.0)

    macd_hist = float(row["MACD_hist_12_26_9"])
    macd_scaled = max(min(macd_hist / (0.02 * close), 3.0), -3.0)
    macd_score = 50.0 + (macd_scaled / 3.0) * 50.0
    macd_score = max(0.0, min(100.0, macd_score))

    sma20 = float(row["SMA_20"])
    sma50 = float(row["SMA_50"])

    def _trend_score(price: float, sma: float) -> float:
        pct = (price - sma) / sma if sma != 0 else 0.0
        pct = max(min(pct, 0.10), -0.10)
        return 50.0 + (pct / 0.10) * 50.0

    sma20_score = _trend_score(close, sma20)
    sma50_score = _trend_score(close, sma50)
    sma_score = (sma20_score + sma50_score) / 2.0

    bb_lower = float(row["BB_lower"])
    bb_upper = float(row["BB_upper"])
    if bb_upper == bb_lower:
        bb_score = 50.0
    else:
        pos = (close - bb_lower) / (bb_upper - bb_lower)
        pos = max(0.0, min(1.0, pos))
        bb_score = pos * 100.0

    vwap = float(row["VWAP"])
    if vwap == 0:
        vwap_score = 50.0
    else:
        vwap_pct = (close - vwap) / vwap
        vwap_pct = max(min(vwap_pct, 0.05), -0.05)
        vwap_score = 50.0 + (vwap_pct / 0.05) * 50.0

    scores = [
        rsi_score,
        macd_score,
        sma_score,
        bb_score,
        vwap_score,
    ]
    technical_score = float(sum(scores) / len(scores))
    return max(0.0, min(100.0, technical_score))


def add_technical_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Indicators exist, append 'Technical_Score'.
    """
    if "RSI_14" not in df.columns:
        df = add_technical_indicators(df)

    df = df.copy()
    df["Technical_Score"] = df.apply(compute_technical_score, axis=1)
    return df
