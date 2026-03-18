from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import math
import pandas as pd


@dataclass(frozen=True)
class FundamentalResult:
    score: float
    ratios: Dict[str, float]


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    try:
        return float(numerator) / float(denominator)
    except (TypeError, ValueError):
        return None


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _ratio_score(
    value: float | None,
    ideal_min: float | None = None,
    ideal_max: float | None = None,
) -> float:
    """
    Map financial ratio into a 0–100 score
    """
    if value is None or math.isnan(value):
        return 50.0

    v = float(value)
    if ideal_min is not None and ideal_max is not None:
        if v < ideal_min:
            if ideal_min == 0:
                return 0.0
            return _clamp_score(100.0 * v / ideal_min)
        if v > ideal_max:
            cap = ideal_max * 3.0
            v_clamped = min(v, cap)
            return _clamp_score(100.0 * (cap - v_clamped) / (cap - ideal_max))
        return 100.0

    if ideal_min is not None:
        if v < ideal_min:
            return _clamp_score(100.0 * v / ideal_min)
        return 100.0

    if ideal_max is not None:
        if v > ideal_max:
            cap = ideal_max * 3.0
            v_clamped = min(v, cap)
            return _clamp_score(100.0 * (cap - v_clamped) / (cap - ideal_max))
        return 100.0

    return 50.0


def score_fundamentals(fundamental_data: Dict[str, Any]) -> FundamentalResult:
    """
    Calculate a 0–100 'Fundamental Score'
    Ratios considered:
    current ratio, debt to equity, forward P/E, profit margin, operating margin, free cash flow
    """
    info: Dict[str, Any] = fundamental_data.get("info", {}) or {}
    bs_obj = fundamental_data.get("balance_sheet")
    balance_sheet: pd.DataFrame = (
        bs_obj if isinstance(bs_obj, pd.DataFrame) else pd.DataFrame()
    )

    cf_obj = fundamental_data.get("cashflow")
    cashflow: pd.DataFrame = (
        cf_obj if isinstance(cf_obj, pd.DataFrame) else pd.DataFrame()
    )

    latest_bs = balance_sheet.iloc[:, 0] if not balance_sheet.empty else pd.Series(dtype="float64")
    latest_cf = cashflow.iloc[:, 0] if not cashflow.empty else pd.Series(dtype="float64")

    current_assets = float(latest_bs.get("Total Current Assets", 0.0) or 0.0)
    current_liabilities = float(latest_bs.get("Total Current Liabilities", 0.0) or 0.0)
    total_debt = float(latest_bs.get("Total Debt", 0.0) or 0.0)
    total_equity = float(latest_bs.get("Total Stockholder Equity", 0.0) or 0.0)

    current_ratio = _safe_div(current_assets, current_liabilities)
    debt_to_equity = _safe_div(total_debt, total_equity)

    forward_pe = info.get("forwardPE")
    profit_margin = info.get("profitMargins")
    operating_margin = info.get("operatingMargins")

    op_cashflow = float(latest_cf.get("Total Cash From Operating Activities", 0.0) or 0.0)
    capex = float(latest_cf.get("Capital Expenditures", 0.0) or 0.0)
    free_cash_flow = op_cashflow + capex

    ratios: Dict[str, float] = {}
    if current_ratio is not None:
        ratios["current_ratio"] = float(current_ratio)
    if debt_to_equity is not None:
        ratios["debt_to_equity"] = float(debt_to_equity)
    if forward_pe is not None:
        ratios["forward_pe"] = float(forward_pe)
    if profit_margin is not None:
        ratios["profit_margin"] = float(profit_margin)
    if operating_margin is not None:
        ratios["operating_margin"] = float(operating_margin)
    ratios["free_cash_flow"] = float(free_cash_flow)

    current_ratio_score = _ratio_score(current_ratio, ideal_min=1.5, ideal_max=3.0)

    dte_score = _ratio_score(debt_to_equity, ideal_min=None, ideal_max=1.0)

    fpe_score = _ratio_score(forward_pe, ideal_min=10.0, ideal_max=25.0)

    pm_score = _ratio_score(profit_margin, ideal_min=0.10, ideal_max=0.30)
    om_score = _ratio_score(operating_margin, ideal_min=0.10, ideal_max=0.30)

    if free_cash_flow > 0:
        fcf_score = 100.0
    elif free_cash_flow == 0:
        fcf_score = 50.0
    else:
        fcf_score = 20.0

    component_scores = [
        current_ratio_score,
        dte_score,
        fpe_score,
        pm_score,
        om_score,
        fcf_score,
    ]
    fundamental_score = sum(component_scores) / len(component_scores)

    return FundamentalResult(score=_clamp_score(fundamental_score), ratios=ratios)

