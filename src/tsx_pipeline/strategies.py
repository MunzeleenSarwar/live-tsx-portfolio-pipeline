from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .config import NAME_BY_SHORT, SECTOR_BY_SHORT, SHORT_BY_SYMBOL, STOCK_SYMBOLS

POSITION_CAP = 0.20
SECTOR_CAP = 0.40
RISK_FREE = 0.02


def _constraints(shorts: list[str]) -> list[dict]:
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    sectors = {}
    for i, short in enumerate(shorts):
        sectors.setdefault(SECTOR_BY_SHORT[short], []).append(i)
    for indices in sectors.values():
        constraints.append({
            "type": "ineq",
            "fun": lambda w, idx=tuple(indices): SECTOR_CAP - np.sum(w[list(idx)]),
        })
    return constraints


def _optimise(objective, shorts: list[str], start: np.ndarray | None = None) -> np.ndarray:
    n = len(shorts)
    x0 = np.repeat(1 / n, n) if start is None else start
    result = minimize(
        objective, x0, method="SLSQP",
        bounds=[(0.0, POSITION_CAP)] * n,
        constraints=_constraints(shorts),
        options={"maxiter": 1000, "ftol": 1e-10},
    )
    if not result.success:
        raise RuntimeError(f"optimisation failed: {result.message}")
    weights = np.clip(result.x, 0, POSITION_CAP)
    return weights / weights.sum()


def minimum_variance(cov: np.ndarray, shorts: list[str]) -> np.ndarray:
    return _optimise(lambda w: float(w @ cov @ w), shorts)


def risk_parity(cov: np.ndarray, shorts: list[str]) -> np.ndarray:
    def objective(w):
        variance = float(w @ cov @ w)
        vol = np.sqrt(max(variance, 1e-16))
        contributions = w * (cov @ w) / vol
        target = vol / len(w)
        return float(np.sum((contributions - target) ** 2))
    return _optimise(objective, shorts)


def minimum_cvar(returns: pd.DataFrame, shorts: list[str], alpha: float = 0.95) -> np.ndarray:
    scenario = returns[shorts].to_numpy(dtype=float)
    tail_count = max(1, int(np.ceil((1 - alpha) * len(scenario))))
    def objective(w):
        losses = -scenario @ w
        return float(np.sort(losses)[-tail_count:].mean())
    return _optimise(objective, shorts)


def _metrics(returns: pd.DataFrame, weights: np.ndarray, shorts: list[str]) -> dict:
    weekly = returns[shorts].to_numpy(dtype=float) @ weights
    n = len(weekly)
    ann_return = float((1 + weekly).prod() ** (52 / n) - 1)
    ann_vol = float(np.std(weekly, ddof=1) * np.sqrt(52))
    growth = np.cumprod(1 + weekly)
    drawdown = growth / np.maximum.accumulate(growth) - 1
    tail = np.sort(weekly)[: max(1, int(np.ceil(0.05 * n)))]
    return {
        "annualised_return_window": ann_return,
        "annualised_volatility_window": ann_vol,
        "sharpe_window": (ann_return - RISK_FREE) / ann_vol if ann_vol else np.nan,
        "max_drawdown_window": float(drawdown.min()),
        "weekly_cvar95_window": float(tail.mean()),
    }


def refresh_strategies(weekly_prices: pd.DataFrame, estimation_weeks: int = 104) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    shorts = [SHORT_BY_SYMBOL[s] for s in STOCK_SYMBOLS]
    prices = weekly_prices[STOCK_SYMBOLS].copy()
    prices.columns = shorts
    returns = prices.pct_change().dropna(how="any")
    if len(returns) < estimation_weeks:
        raise ValueError(f"need {estimation_weeks} weekly returns, found {len(returns)}")
    window = returns.iloc[-estimation_weeks:]
    cov = window.cov().to_numpy(dtype=float) * 52
    equal = np.repeat(1 / len(shorts), len(shorts))
    candidates = {
        "Equal Weight": equal,
        "Minimum Variance": minimum_variance(cov, shorts),
        "Risk Parity": risk_parity(cov, shorts),
        "Minimum CVaR (latest window)": minimum_cvar(window, shorts),
    }
    weight_rows, metric_rows = [], []
    for strategy, weights in candidates.items():
        metrics = _metrics(window, weights, shorts)
        metric_rows.append({
            "strategy": strategy, "estimation_start": window.index.min(),
            "estimation_end": window.index.max(), "weeks": len(window), **metrics,
        })
        for short, weight in zip(shorts, weights):
            weight_rows.append({
                "strategy": strategy, "symbol": f"{short}.TO" if short != "L" else "L.TO",
                "short": short, "company": NAME_BY_SHORT[short],
                "sector": SECTOR_BY_SHORT[short], "weight": float(weight),
            })
    # Correct Yahoo symbols come from the short mapping except for Loblaw.
    symbol_by_short = {v: k for k, v in SHORT_BY_SYMBOL.items()}
    weights_df = pd.DataFrame(weight_rows)
    weights_df["symbol"] = weights_df["short"].map(symbol_by_short)
    sector = (weights_df.groupby(["strategy", "sector"], as_index=False)["weight"].sum()
              .rename(columns={"weight": "sector_weight"}))
    return weights_df.sort_values(["strategy", "short"]), pd.DataFrame(metric_rows), sector
